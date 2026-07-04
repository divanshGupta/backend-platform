# Building the hashing package first

- User.hashed_password needs somewhere to get its value from, we build the package before the modules that consumes it.

## Why it exists as its own package rather than a method on User:

- Reusability beyond User. If you ever hash anything else (API keys, invite tokens), you reuse the same package — it doesn't know or care what's being hashed.
- Swappability. If argon2 configuration ever needs tuning, or you migrate hashing algorithms years from now, there's exactly one place to change it — not scattered across every model/service that touches passwords.
- Testability in isolation. You can unit test hashing correctness (hash_password("x") then verify_password("x", result) is True) without touching a database, a User model, or FastAPI at all.