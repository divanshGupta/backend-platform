## Concept: why split Repository and Service at all?

### Repository 
- knows how to talk to the database for User rows. get_by_id, get_by_email, create, nothing else. No business rules.

### Service
- knows the business rule of creating a user: "hash the password before storing it," "reject duplicate emails with a clear error," "maybe emit an audit log entry later." It calls the repository, it doesn't write SQL.


## Why not just put DB queries directly in the service? For a single table, right now, honestly — it wouldn't look very different. The value shows up as the system grows:
- Testability. You can unit-test UserService.create_user() by giving it a fake/mock repository, with no real database — fast tests, no Docker container needed to run them.
- Swappable persistence. If a query needs to become more complex (e.g., a join across user_roles later), that complexity is isolated in the repository; the service's create_user() method doesn't change.
- One clear place SQL is allowed to exist. Per your own coding standard, "never place SQL inside controllers" — extending that, business logic (services) also shouldn't hand-write queries. This makes future code review trivial: SQL/ORM query construction outside repository.py is an instant red flag.