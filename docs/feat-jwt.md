# JWT Feature

## token generation/verification is pure logic with no DB knowledge → packages/auth/jwt.py (same tier as hashing.py). But a login endpoint needs a service method that checks credentials and issues tokens → that's modules/user/service.py calling into packages/auth.

## JWT Library:

- PyJWT - simple, minimal api, actively maintained, no known outstanding cves - slightly lower lever (we write our own expiry/claims helpers)

- python-jose - more features (jwk, jwe) - historically has had cves, we dont need jwe/jwk for a single deployment model

- i am choosing pyjwt here, we dont need jose's extra machinery.

## Signing algo

- HS256 (symmetric, one secret) - Single deployment validates its own tokens — our exact case

- RS256 (asymmetric, public/private key) - Multiple services need to verify tokens without being able to issue them (e.g. microservices, API gateway)

- i am choosing hs256. rs256 solves a problem i dont have rn.

## Refresh token storage

- Stateless refresh (just a long-lived JWT) - no db hit - cant revoke. logut doesnt actually log out. cant detect token theft/misuse.

- DB-backed refresh token (store hash of token, user_id, expiry, revoked flag) - Revocable, supports rotation, supports "logout everywhere" - one extra table +  one db write  per login/refresh

- i am choosing db backed, productiion grade.

## Task Breakdown 

1. Config — add JWT settings to pydantic-settings (secret key, algorithm, access/refresh expiry)
2. packages/auth/jwt.py — pure functions: create_access_token, create_refresh_token, decode_token
3. modules/user/token_model.py — RefreshToken SQLAlchemy model (id, user_id FK, token_hash, expires_at, revoked)
4. Alembic migration for the new table
5. modules/user/service.py — authenticate_user() method (verify password via packages/auth/hashing.py, issue tokens)
6. Schema - LoginRequest, TokenResponse (access_token, refresh_token, token_type)
7. Route - POST /auth/login (where should this controller live - new modules/auth/ or  inside modules/user/? worth deciding)
8. Dependency - get_current_user() for protection future routes (decides jwt, loads user)
9. Exception mapping - invalid credentials -> 401, expired/invalid token -> 401


## RedreshToken Model 

concept: why stooe refresh token at all if theyre alredy jwts?

if decode_token() already verifies signature and expiry, why hit the DB too? Because a signature check alone can only tell we "this token was legitimately issued and hasn't expired." It can never tell we "this token has since been revoked." Revocation requires a record we can mutate. Without a DB row, "logout" is a lie — the token stays valid until it naturally expires, even after the user logs out.

- Design decision: store the raw token, or a hash of it?

- Store raw refresh token - Simple to query - If our DB is ever breached, attacker gets live, usable refresh tokens for every user

- Store SHA-256 hash of the token - DB breach alone doesn't give usable tokens (like password hashing) - Need to hash before every lookup — trivial cost

- i choose hashing it.

### A few things worth flagging explicitly: modules/user/token_model.py

- ForeignKey("platform.users.id") — adjust platform to whatever our actual schema name is for the users table (we mentioned a dedicated platform schema earlier). Get this wrong and Alembic - will fail loudly at migration time, not silently.
- ondelete="CASCADE" — if a user is deleted, their refresh tokens should die with them. Otherwise we accumulate orphaned rows forever.
- token_hash is unique=True — this is a real (if astronomically unlikely) safety net: a hash collision would let one user's stored token match another's lookup. Practically it also just makes the index useful for fast revocation checks.
- No updated_at — deliberately. This table doesn't get updated in place; when a token rotates, we revoke the old row and insert a new one (append-only audit trail of sorts). If we find ourself wanting to UPDATE this table later, that's usually a sign token rotation logic has drifted from the design.

## Task 5 - authenticate_user() - user/service.py

- concept - what does "auth" actuall mean here, and what should it return?

- This method has one job: given raw credentials, either return a validated User or refuse — cleanly, without leaking why it refused. It should not issue tokens itself. Token issuance is a separate concern (packages/auth), and keeping them separate means we can reuse authenticate_user() anywhere we need to verify credentials, even somewhere that never touches JWTs (e.g. a future "confirm our password to change email" flow).

- A very common mistake: returning different errors for "no such email" vs "wrong password." That lets an attacker discover which emails exist in our system just by trying logins. Both cases must return the same generic error, and — just as important — take roughly the same amount of time, otherwise a timing attack (measuring response latency) leaks the same information a different way. The trick: always run the password hash verification, even when the user doesn't exist, against a dummy hash — argon2 verification is deliberately slow, so skipping it when the user is missing makes "no such user" responses measurably faster than "wrong password" responses.

- Why is_active is checked here, inside authentication, and not later: a deactivated user should fail login with the exact same generic error as a wrong password — not a special "your account is disabled" message. Otherwise you've reintroduced enumeration: now an attacker can distinguish "wrong password on an active account" from "this account exists but is disabled."

- Why I haven't touched RefreshToken yet in this method: authenticate_user() only proves identity. Issuing a refresh token is a side effect of a successful login specifically — not of "authentication" as a general-purpose operation. That distinction matters if you ever authenticate a user for something that shouldn't spawn a new session (e.g. verifying current password before changing it).

### Where does "issue tokens on successful login" then live?

1. New login() method in UserService, calling authenticate_user() + packages/auth/jwt.py + writing the RefreshToken row - Keeps orchestration in the service layer

2. Directly in the controller, calling authenticate_user() then packages/auth functions inline

- i choose new login() method in UserService. the controller should end up looking like your existing create_user route - thin, just catching exceptions and mapping to http status codes.
All the "verify password → create refresh token row → return token pair" orchestration belongs in the service.

##  Design: AuthService - user/auth_service.py

authservice dosnt reimplement credential checking - it depends on userservice and calls the authenticate_user() we already wrote.
this id dependency injection trade-off workth naming explicitly: injecting userservice into authservice (rather than authservice reaching into userrepository directly) means credentails checking remains at one place. if we ever need to add accunt lockout after N failed attempts, we add it once, in authenticate_user() and every caller benefits.


## Login is fully working, Two more pieces remain before JWt auth is done.

1. get_current_user() dependency - decodes the access token, loads theuser, and protects routes. without this, having tokens doesnt actually secure anything yet.

2. refresh + logout endpoints - using the get_by_hash() / revoke() methods already sitting in RefreshTokenRepository, unused until now.

### get_current_user() - it's self-contained, testable in one endpoint and its the piece that turn "we can issue tokens" into "tokens actually protect something".

- this is a fastapi dependency, not a service method - it doenst belong in AuthService because it's not business logic, it's request plumbing: extract the token from the Authorization header, verify it, load the user, hand it to whichever routes asked for it. Every protected route will just declare currect_user: Annotated[User, Depends(get_current_user)] and get this for free.

- Design choice: use Fastapi's HTTPBearer security scheme (not OAuth2PasswordBearer) - OAuth2PasswordBearer assumes a /token form-based flow (OAuth2 spec baggage  you dont need), while HTTPBearer just means "expect Authoriztino: Bearer <token>," which is exactly your actual contract.

### Two things worth noting, briefly:

1. Same generic error message for "bad signature," "expired," "user deleted since token was issued," and "deactivated" — same enumeration principle from authenticate_user(). Don't tell an attacker which of these is true.

2. expected_type=TokenType.ACCESS is doing real work here — this is exactly what stops someone from using a stolen refresh token as an access token.

## refresh token rotation and logout.
- both use the get_by_hash() and revoke() methods already sitting in RefreshTokenRepository, unused until now.

- <CONCEPT> why rotation, why not just reuse?
- everytime a refres token is used, the server issues a new refresh token, and immediately revoke the last one, in this way if a attacker get the old refresh token and he tries to login with that old refresh token, then server will know that someone is using older refresh token, in response server will revoke all the refresh token for that user, forcing a fresh login everywhere, treating it as a likely compromise.

- WHAT WE GONNA DO?

1. AuthService.refresh() - verify refresh token (signature + db lookup + not revoked + not expired), revoke it, issue new access+refresh pair.
2. Reuse detection - if the presented token's hash isn't found, or is found but already revoked, treat as suspicious.
3. AuthService.logout() - rvoke a specific refresh token (or all of a user's tokens, if you want a "logout everywhere" option)
4. Two new routes: POST /auth/refresh, POST  /auth/logout
5. Schemas: RefreshRequest, maybe reuse TokenResponse

### Repository addition - one more method needed - for reuse detection, we need to revoke every token for a user at once, not just one

### src/modules/user/token_repository.py  (add to existing class)
async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
    await self.session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
        .values(revoked=True)
    )

#### AuthService.refresh() — the core logic

<Concept>: what makes this different from just "check the token and issue a new one"?

- The refresh token's JWT sign only proves it was legitimately used by user at some point - it says nothing about whether its still supposed to be vaild. Only the db row knows that.
- so refresh() has to check three things, adn each catched a diff failure mode:

1. JWT sign + type valid - forged tokens, access tokens submitted as refresh tokens
2. DB row exists for this hash - tokens that were never issued by users
3. DB row not already revoked - resuse - this exact token was already used once before

- One deliberate choice worth flagging: logout() doesn't raise on a missing/already-revoked token. Calling logout twice, or logging out with a token that already expired, just quietly succeeds both times. This is standard REST practice for destructive/idempotent operations — a client retrying a logout call (e.g. after a flaky network response) shouldn't get an error for something that's already in the state they wanted.