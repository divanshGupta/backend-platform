# Feature: Expose UserService.create_user() over HTTP as POST /users

- Layer check: This is a Module-level concern (src/modules/user/) — not Core (no infra), not a Package (it's User-specific, not domain-agnostic), not an Application (not hospital-specific).
- Dependencies: UserService (done), get_db() (done). New pieces: Pydantic schemas, a dependency function wiring get_db() → UserService, a router, and exception-to-HTTP mapping.
- Small tasks, in order: schemas → dependency wiring → router → exception mapping → wire router into the app → test via /docs → verify in psql.

## Step 1: Pydantic Schemas - why two schemas? - user/shemas.py

- A UserCreate schema describes what the client sends (email, username, plaintext password). 
- A UserRead schema describes what the server sends back (id, email, username, timestamps — never the password)

## Step 2: Dependency Wiring - get_user_service() - user/dependencies.py

- Concept: why not just instantiate UserService inside the route function?
1. bypasses the req-scoped transaction pattern i already built (get_db() from step 4 - it commits on success, rolls back on error and closed the session)
2. untestable in isolation, fastapi dependency injection lets override dependencies in tests.
3. repeats wiring logic every route. a dependency functon centralize that once.

## Step 3: The Controller - user/controller.py

@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    try:
        user = await service.create_user(
            email=data.email,
            username=data.username,
            plain_password=data.password,
        )
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DuplicateUsernameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return UserRead.model_validate(user)

- why response_model=UserRead matters, even though i am already returning UserRead.model_validate(user) explicitily?
    Declaring response_model gives fastapi a second, independent enforcement layer - if code changes accidentally returned the raw User ORM object instead of the schema, fastapi would still filter the response through UserRead before sending it,  meaning hashed_password cannot leak even if someone makes that mistakes later.
- the same principle as the req/res schema split - never rely on a single point of correctness for something secruity sensitive.

- One security thing to flag now, not later: HTTPException(detail=str(e)) — exposing "Email already registered: raj@example.com" back to the client. This is a real, if minor, information-disclosure trade-off worth naming: it confirms to an attacker that a specific email exists in your system, which is a known enumeration vector (useful for phishing/targeting). For a hospital inventory demo, low real risk — but if this were a public-facing signup form for a real client handling PII, I'd recommend a generic message ("Registration failed" or "Email or username already in use") instead of confirming which field collided.

## Step 4: Wire the router into the app - src/core/app.py