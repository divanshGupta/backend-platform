# Backend Platform — project documentation

_Last updated: July 11, 2026_

## What this project is

A production-grade, reusable FastAPI backend platform, built to be cloned and
redeployed per client (one deployment per client, not multi-tenant) across
different business verticals — hospital, pharmacy, restaurant, school, gym, CRM,
warehouse — without rewriting authentication, RBAC, logging, storage, or core
infrastructure each time.

The current build target and primary deliverable is a **Hospital Inventory
Management MVP**, used both as a real, working system and as a deliberate
architecture-learning exercise: moving from ad-hoc FastAPI scripts to a properly
layered, production-quality codebase with real dependency injection, a repository/
service/controller separation, and RBAC enforcement baked in from the start.

## Architecture

Strict layered "moducore" pattern:

```
core → packages → modules → apps
```

- **Core** — infrastructure only (config, DB session management, DI, middleware,
  exception handling). Never contains business logic.
- **Packages** — reusable forever, business-agnostic (auth, RBAC, logging — these
  never know what a "hospital" or "medicine" is).
- **Modules** — reusable domain concepts (users, roles, permissions).
- **Apps** — actual client systems (Hospital, and eventually others), each combining
  reusable modules into a real product.

Within any single feature, the request/response path always flows:

```
Controller (HTTP only) → Service (business rules) → Repository (raw DB access) → Database
```

with Pydantic schemas validating input at the controller boundary and shaping
output on the way back, and SQLAlchemy models defining the DB table structure
with zero business logic of their own.

## Tech stack

FastAPI · SQLAlchemy 2.0 (async) · Alembic (async, multi-schema) · PostgreSQL
(Dockerized) · Pydantic v2 · `uv` for dependency management · `argon2-cffi` for
password hashing · PyJWT (HS256) · HTTPie for manual API testing.

## What's built so far

### Platform layer (identity & access control — `platform` schema)

- **Authentication**: JWT access + refresh tokens, refresh token rotation with
  reuse detection (replaying a revoked token revokes all of that user's sessions),
  single-device logout, argon2 password hashing.
- **RBAC**: full permission chain (`users → user_roles → roles → role_permissions
  → permissions`), single dotted-string permission names (e.g. `medicine.read`),
  a reusable `require_permission()` FastAPI dependency enforcing authorization at
  the route level, and an idempotent seed script (`scripts/seed_rbac.py`) that
  fully reconciles roles' permissions on every run.
- **Users**: registration, login, profile retrieval, role assignment.

### Hospital Inventory MVP (`hospital` schema)

| Module | What it does | Status |
|---|---|---|
| **Category** | Medicine categorization (e.g. "Antibiotics"). Full CRUD. | ✅ Complete |
| **Supplier** | Supplier/vendor records with contact info. Full CRUD. | ✅ Complete |
| **Medicine** | Core medicine catalog, referencing Category + Supplier. Full CRUD, includes name search. | ✅ Complete |
| **Stock** | Batch-level inventory: quantity + expiry date per batch, referencing a Medicine. Delta-based quantity adjustments (never direct overwrite) for audit accountability. Zero-quantity batches are preserved, not deleted. | ✅ Complete |
| **Purchase** | Records a purchase order (Medicine + Supplier + quantity + price), and automatically creates the resulting Stock batch in the same transaction. Append-only — no editing or deleting purchase history. | ✅ Complete |
| **Dashboard** | Aggregated inventory metrics (total medicines, low stock, expiring soon, out of stock, today's purchases). | 🔲 Not started — next up |

Every completed module above has been:
- Migrated and schema-verified directly against the live PostgreSQL database (not
  just assumed correct from the migration file or a passing API response)
- Fully RBAC-gated, with both positive (authorized user succeeds) and negative
  (unauthorized user gets a clean 403) cases manually tested
- Exercised end-to-end via HTTPie, including error paths (invalid foreign keys,
  constraint violations, permission failures) — not just the happy path

## Real engineering problems solved along the way

This project has been as much about learning async SQLAlchemy's genuine sharp
edges as about the inventory domain itself. Problems found and fixed, in the
order they were encountered:

1. **Silent write loss in error-handling code** — a global `except Exception:
   rollback()` in the DB session dependency was undoing a security-critical
   write (mass refresh-token revocation on detected token reuse) whenever the
   triggering exception propagated through it. Fixed with a narrowly-scoped
   explicit commit on that one security-critical path, without weakening the
   global rollback safety net everywhere else.
2. **`MissingGreenlet` on eager-loaded relationships** — async SQLAlchemy's
   `flush()` only sends the `INSERT`/`UPDATE`; it does not populate relationship
   attributes configured for eager loading. Reading them afterward without an
   explicit re-fetch crashes, because async SQLAlchemy has no implicit
   lazy-load fallback the way sync SQLAlchemy does.
3. **`PendingRollbackError` masking the real exception** — after a failed
   `flush()` (e.g. a foreign-key `RESTRICT` violation on delete), touching any
   attribute of the involved ORM object — even just to build a clean error
   message — triggers an automatic reload attempt against a transaction that's
   already dead, producing a second, unrelated exception that hides the first.
4. **Stale relationship data via the SQLAlchemy identity map** — re-fetching an
   object by primary key after mutating one of its foreign key columns returns
   the *same* cached Python object with the relationship still showing its old
   value, because SQLAlchemy trusts already-loaded relationship state rather
   than assuming it's now stale. Fixed via a targeted `session.refresh(obj,
   attribute_names=[...])`.
5. **A model silently losing its schema assignment** — combining a `CheckConstraint`
   with schema declaration in `__table_args__` requires care: a plain tuple of
   constraints without an explicit schema dict as the final element drops the
   inherited schema from the base class entirely, caught by reviewing the
   generated Alembic migration before applying it, not after.

## What's next

Per the project's own milestone plan (`moducore.md`):

- **Dashboard** (remaining Week 3 item) — aggregated read-only metrics across
  the modules already built. Architecturally different from everything above:
  no new table, no new migration, just well-designed aggregation queries.
- **Week 4 — polish & portfolio**: automated tests (pytest), richer seed data,
  Swagger/OpenAPI documentation improvements, deployment setup, a demo frontend
  integration, and portfolio-ready documentation/screenshots.

## Longer-term roadmap

- Expand the reusable platform to additional verticals (Pharmacy, Restaurant,
  School, Gym, CRM, Warehouse) — reusing the `core`/`packages`/`modules` layers
  as-is, building new `apps/*` for each business domain.
- Formalize a multi-client deployment/cloning workflow, since this platform is
  designed as one-deployment-per-client rather than multi-tenant.
- Build out `packages/audit` properly — several places in the Hospital app
  (notably Stock adjustments) currently only log changes via Python's standard
  logging as an interim measure, deliberately deferring full audit-trail
  persistence until this package exists.