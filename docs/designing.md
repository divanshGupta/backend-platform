## Concept: why split Repository and Service at all?

### Repository 
- knows how to talk to the database for User rows. get_by_id, get_by_email, create, nothing else. No business rules.

### Service
- knows the business rule of creating a user: "hash the password before storing it," "reject duplicate emails with a clear error," "maybe emit an audit log entry later." It calls the repository, it doesn't write SQL.


## Why not just put DB queries directly in the service? For a single table, right now, honestly — it wouldn't look very different. The value shows up as the system grows:
- Testability. You can unit-test UserService.create_user() by giving it a fake/mock repository, with no real database — fast tests, no Docker container needed to run them.
- Swappable persistence. If a query needs to become more complex (e.g., a join across user_roles later), that complexity is isolated in the repository; the service's create_user() method doesn't change.
- One clear place SQL is allowed to exist. Per our own coding standard, "never place SQL inside controllers" — extending that, business logic (services) also shouldn't hand-write queries. This makes future code review trivial: SQL/ORM query construction outside repository.py is an instant red flag.

## should one service call another service?

-  yes, and you actually already have a precedent for this in our own codebase.

- here:
def __init__(
    self,
    user_service: Annotated[UserService, Depends(get_user_service)],
    token_repository: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> AuthService:

- AuthService doesn't touch UserRepository directly — it depends on UserService, a full service, not a repository. That's the exact same shape PurchaseService needs: it should depend on StockService, not StockRepository.

## Why service-to-service, not service-to-repository — the actual reasoning, not just "match the pattern"

- Here's the concrete failure mode if PurchaseService reached into StockRepository directly instead: it would need to reimplement the business rule that lives in StockService.create_stock() — specifically, the check that quantity can't be negative, and the check that the medicine actually exists before creating stock against it. Those rules live in StockService on purpose. If PurchaseService bypassed StockService and wrote to StockRepository directly, we have the same validation logic potentially drifting out of sync in two places — a bug where fixing a rule in StockService doesn't fix it for purchases, because purchases never went through StockService at all.

- So the layering principle in one sentence: a service orchestrates repositories it owns, plus other services for anything outside its own domain.