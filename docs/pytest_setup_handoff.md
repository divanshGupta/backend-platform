# Backend Platform — Context Handoff (pytest foundation complete)

## Project
Building `backend-platform`: reusable, cloneable FastAPI backend (one deployment
per client, not multi-tenant). Primary build target: Hospital Inventory MVP.
Governed by `moducore.md` (layered architecture: core → packages → modules →
apps). I'm a learner building FastAPI skills — plain English, minimal jargon,
deep understanding over memorization. For testing work specifically: learning
mode — explain each step, ask questions, don't just implement.

## Stack & environment
FastAPI, SQLAlchemy 2.0 (async), Alembic (async, multi-schema), PostgreSQL,
`uv`, Docker Compose, PyJWT, argon2-cffi, pytest, pytest-asyncio, httpx,
polyfactory. Windows, PowerShell, VS Code.

DB access (dev): `docker exec -it backend_platform_db psql -U platform -d backend_platform`
DB access (test): `docker exec -it backend_platform_db psql -U platform -d backend_platform_test`
(same container, same user — see "Test database" section below)

## Everything decided this session (with reasoning, not just conclusions)

### Test database strategy
- **Second database in the same running Docker container** — `backend_platform_test`,
  created manually via `CREATE DATABASE backend_platform_test;` inside psql.
  No new infrastructure, no testcontainers — reuses the existing dev Postgres,
  same schema names (`platform`, `hospital`) so app code never needs to know
  it's under test.
- **Isolation between tests: truncate, not rollback-via-savepoint.** Chosen
  specifically because this project's core debugging habit is "verify against
  a live psql connection" — a savepoint-rollback strategy would make
  in-progress test data invisible to any external psql session, which
  directly undercuts that habit. Truncation keeps every committed row real
  and independently verifiable.
- **Test client: `httpx.AsyncClient` + `ASGITransport`**, not FastAPI's
  `TestClient` — chosen because the whole app is async top-to-bottom, and
  `TestClient` forces a sync-style call underneath, which is a known source of
  subtle bugs when mixed with async SQLAlchemy.
- **Test data: `polyfactory`** (`SQLAlchemyFactory`), not hand-written
  fixtures — chosen because of the dependency chain (Category → Medicine →
  Stock → Purchase); hand-rolled fixtures would mean repetitive setup code
  duplicated across many test files.
- **Auth in tests: both, deliberately split.**
  - A small, dedicated set of tests for the auth/RBAC system itself uses the
    **real** login flow (real JWT, real password) — because testing fake auth
    there would be meaningless.
  - Every other test (Category, Medicine, Stock, Purchase, Dashboard) uses a
    **faked** `get_current_user` dependency override — because those tests
    care about business logic, not about re-proving auth works every time.
- **Coverage order: simplest thing first.** Category CRUD was deliberately
  chosen as the very first test — not because it's high-value, but because it
  lets the whole pipeline (env loading, migrations, fixtures, client) get
  proven on the easiest possible target before pointing it at RBAC/Auth, which
  is the actually complex, high-stakes code.

## Environment setup for tests

### `.env.test`
A second env file at the project root, alongside `.env`. Same content as
`.env`, with only `DATABASE_URL`'s database name changed to
`backend_platform_test`. Same user/password/host/port as dev — it's the same
Postgres container, just a different database inside it.
**Must be added to `.gitignore`, same as `.env`** (real credentials inside).

### Why a `.env.test` file instead of code-level "testing mode" branching
Considered adding a `TESTING` flag inside `Settings` itself to conditionally
load a different env file. Rejected — that would mix test-only concerns into
production config code, violating the same "packages/core must not know about
higher layers" instinct already applied elsewhere in this project. Instead,
`.env.test` is loaded as real OS environment variables at the very top of
`conftest.py`, before anything else is imported — `Settings` itself stays
completely unaware tests exist.

### The critical ordering trap this creates
`src/core/database/session.py` has `settings = get_settings()` running at
**import time** — not inside a function. Combined with `@lru_cache` on
`get_settings()`, whichever `Settings` gets built *first* in the whole process
is cached and reused forever after, regardless of what env vars get set later.
This means: **`load_dotenv(".env.test", override=True)` must be the literal
first thing that happens in `conftest.py`**, before any `from src...` import
anywhere in the file. `override=True` specifically matters too — without it,
`python-dotenv` won't overwrite a variable that's already sitting in the OS
environment for some other reason.

## `tests/conftest.py` — final, working version

```python
from dotenv import load_dotenv
load_dotenv(".env.test", override=True)

import asyncio

from httpx import AsyncClient, ASGITransport

import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.core.config.settings import get_settings
from src.core.database.session import get_db
from src.core.app import create_app
from src.modules.user.dependencies import get_current_user

from tests.fake_auth import FakeUser, ALL_PERMISSION_NAMES


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    alembic_cfg = Config("alembic.ini")
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with db_engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('platform', 'hospital')
            AND table_name != 'alembic_version'
        """))
        tables = [f"{schema}.{name}" for schema, name in result.fetchall()]

        if tables:
            await conn.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
def current_user_permissions():
    return ALL_PERMISSION_NAMES  # default: acts like Admin


@pytest_asyncio.fixture(scope="function")
async def client(db_engine, db_session, current_user_permissions):
    test_app = create_app()
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_get_current_user():
        return FakeUser(current_user_permissions)

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    test_app.dependency_overrides.clear()
```

### Design decisions baked into this file (worth remembering *why*)

1. **`create_app()` is called fresh inside the `client` fixture — never import
   the already-built `app` from `src.main`.** `create_app` is a factory
   function specifically so tests can get their own private `FastAPI`
   instance ("their own whiteboard") instead of sharing and mutating the one
   real app object every request in production would also use.
2. **`db_engine` (Alembic migrations) runs via `asyncio.to_thread(...)`,
   not called directly.** `alembic/env.py` calls `asyncio.run(...)` internally
   — starting a *new* event loop. Since `db_engine` itself already runs inside
   pytest-asyncio's event loop, calling Alembic directly would try to nest one
   event loop inside another (`RuntimeError: event loop already running`).
   Running it on a separate thread sidesteps this — a fresh thread has no
   existing loop, so Alembic's `asyncio.run()` is free to create its own,
   completely independently.
3. **`client` builds its own fresh session for `get_db`, rather than reusing
   `db_session` directly.** First attempt shared one session between "test
   setup code" and "the app's request handling" — this caused
   `InterfaceError: cannot perform operation: another operation is in
   progress`, because a single database connection can only run one operation
   at a time, and the test body's code and the app's in-flight request weren't
   cleanly sequential. Giving the app's request its own separate connection
   (built from the same long-lived `db_engine`) avoids the collision entirely.
   Because of this, **any test that needs to pre-create data the app should
   later see must `.commit()` it** (not just `.flush()`) — `.flush()` only
   makes data visible within the *same* connection; `.commit()` finishes the
   transaction so any other connection (like the one the app's request uses)
   can see it too.
4. **Truncation uses a live `information_schema.tables` query, not a
   hardcoded table list.** A hardcoded list would silently go stale every time
   a new table is added (same failure class as forgetting to register a model
   in `model_registry.py`) — querying Postgres directly for what tables
   currently exist means this can never drift out of sync.
5. **`current_user_permissions` is a plain, overridable fixture, not a
   hardcoded list inside `client`.** Defaults to `ALL_PERMISSION_NAMES`
   (acts like Admin) for every test. A specific test *file* can redefine a
   fixture with the exact same name to simulate a restricted role (e.g.
   Pharmacist or Viewer) — pytest resolves the closer, file-local definition
   first, without needing to touch `conftest.py` at all.

## `tests/fake_auth.py`

```python
import uuid
from scripts.seed_rbac import PERMISSIONS

ALL_PERMISSION_NAMES = [name for name, _ in PERMISSIONS]


class FakePermission:
    def __init__(self, name: str):
        self.name = name


class FakeRole:
    def __init__(self, permission_names: list[str]):
        self.permissions = [FakePermission(name) for name in permission_names]


class FakeUser:
    def __init__(self, permission_names: list[str] = ALL_PERMISSION_NAMES):
        self.id = uuid.uuid4()
        self.is_active = True
        self.roles = [FakeRole(permission_names)]
```

Deliberately pulls `PERMISSIONS` from `scripts/seed_rbac.py` (the real source
of truth) rather than a second hardcoded list — same "never let two places
disagree" reasoning as the table-truncation query above.

**Why overriding `get_current_user` (not `require_permission`) is what
actually covers every protected route:** `require_permission("x")` is a
dependency *factory* — it runs once per route at startup and returns a fresh,
distinct function object each time, specific to that one permission string.
Overriding it would only work per-exact-string. But every one of those
generated functions internally depends on the *same* shared `get_current_user`
dependency to figure out who's logged in. Overriding that single shared
dependency transparently covers every `require_permission(...)`-protected
route in the app, regardless of which permission string it checks.

## `tests/factories.py`

```python
from itertools import count

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.apps.hospital.medicine.category_model import Category

_category_counter = count(1)


class CategoryFactory(SQLAlchemyFactory[Category]):
    __model__ = Category

    @classmethod
    def name(cls) -> str:
        return f"Test Category {next(_category_counter)}"
```

`_category_counter` is defined at module level (outside the class/method) so
it's created exactly once and persists for the life of the process — if it
were created inside the `name()` method itself, it would reset to a fresh
counter on every single call, defeating the point. Needed because `Category.name`
has `unique=True` — without a monotonically increasing value, random string
generation could occasionally collide and cause a flaky (sometimes-passes,
sometimes-fails) test.

## `.build()` vs `.create_async()` vs manual `db_session.add()` — the real distinction

- **`.build()`** — constructs a fake object in Python memory only. Never
  touches the database. Correct when a test just needs realistic *values* to
  send as a request body (e.g. testing "does POST /categories work").
- **`.create_async()`** — polyfactory's own save mechanism. **Not used in this
  project** — it requires configuring an `__async_persistence__` handler on
  the factory, which is one more piece of configuration/"magic" this project
  deliberately avoids per its stated philosophy (prefer simplicity, avoid
  unnecessary abstraction).
- **What's actually used instead, when a test needs a row to already exist**
  (e.g. testing a duplicate-name conflict): `.build()` to get a realistic fake
  object, then save it explicitly and visibly:
  ```python
  existing_category = CategoryFactory.build()
  db_session.add(existing_category)
  await db_session.commit()
  ```
  This keeps the "how something gets saved" fully explicit and visible in the
  test file itself, rather than hidden inside factory configuration.

## pytest configuration — `pyproject.toml`

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
testpaths = ["tests"]
```

- `asyncio_mode = "auto"` — every `async def test_...` is automatically
  treated as an async test; no need to hand-decorate each one with
  `@pytest.mark.asyncio`.
- `asyncio_default_fixture_loop_scope = "session"` **and**
  `asyncio_default_test_loop_scope = "session"` — both required together.
  This was the real, subtle bug behind this session's hardest debugging
  stretch (see below).

### Bug: event loop mismatch (the hardest bug of this session)
By default, pytest-asyncio gives **each test function its own fresh event
loop**. But `db_engine` is `scope="session"` — created once, and its
underlying database connections are tied to whichever loop existed at the
moment it was created. The second test to run would get a brand-new event
loop, but still try to reuse `db_engine`'s connections, which secretly
"belonged" to the *first* test's loop. Result: confusing low-level errors —
`InterfaceError: cannot perform operation: another operation is in progress`,
`AttributeError: 'NoneType' object has no attribute 'send'`,
`RuntimeError: Event loop is closed` — none of which point clearly at the
real cause from the traceback alone.
**Fix:** force fixtures *and* test functions to share one single event loop
for the entire session, matching the lifetime of the session-scoped
`db_engine`. Setting only the fixture-scope option first fixed half the
symptom and shifted the mismatch elsewhere (fixture vs. test function) before
setting both closed the gap completely.
**Generalized lesson:** if a long-lived (session-scoped) async resource is
involved and pytest-asyncio errors look like nonsensical low-level
connection/event-loop noise rather than a clear application bug, suspect an
event-loop-scope mismatch first.

## Tests written and passing (the reference pattern going forward)

`tests/test_category.py`:
- `test_create_category` — happy path. Uses `CategoryFactory.build()` for
  fake request values (never touches DB directly), posts to `/categories`,
  asserts `201` and correct `name` in the response body.
- `test_create_duplicate_category` — conflict path. Uses `.build()` +
  `db_session.add()` + `await db_session.commit()` to create a *real*,
  already-saved Category first, then posts a second request with the same
  `name`, asserts `409`. Deliberately does **not** assert the exact `"detail"`
  error message text — checking status code alone avoids the test breaking
  every time the error message's wording changes, when the actual behavior
  being tested (duplicates are rejected) hasn't.

Both pass cleanly end-to-end, against a real Postgres test database, through
real HTTP-shaped requests, with real Alembic-migrated schema.

## Next steps (not yet started)

- A few more Category tests for full coverage: validation errors (422 on
  missing/invalid fields), and a restricted-role test overriding
  `current_user_permissions` to simulate Pharmacist/Viewer and confirm 403 on
  a permission they don't have.
- RBAC/Auth test suite — the first tests to use the **real** login flow
  instead of the faked `get_current_user` override. Covers login, refresh
  token rotation, and reuse detection — the highest-stakes, most complex logic
  already built.
- Once Category + RBAC both have solid coverage, extend the same
  `db_session`/`client`/factory pattern to Medicine, Supplier, Stock, and
  Purchase.
- Manual verification habit for tests (same discipline as the rest of the
  project): since the test DB gets truncated after every run, "verify in
  psql" for test-related work means either checking mid-debug with a paused
  test, or making one real request against the normal dev server + dev
  database as a sanity check that the underlying mechanism (endpoint → real
  Postgres write) genuinely works — separate from what pytest itself already
  confirms.