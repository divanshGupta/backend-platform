# what conftest.py actually is?

- normally in python i we have to use fuction in another file, we need to import it. 
- pytest breaks that rul for one specific filename: conftest.py
- pytest automatically loads conftest.py in its own, without anyone writing an import statement.
- and anything we define inside it(mainly "fixtures") becomes automatically available to every test file in that folder, and every folder below it - no import needed.
- so basically conftest.py is - a shared toolbox that pytest hands to every test automatically.

# why we need it?

- every single test in our project is goint to need:
- a connection to the test db
- a clean,empty table
- a test client (https.AsyncCient)
- sometimes, a faked logged-in user

# before any test even run:

1. something needs to create the test database engine, once. - connecting to db isnt free- it takes a lot of time. db connection should happend once per whole test run, not once.

2. something needs to run the alembic migration against the test database, once. - the db starts completely fresh and empty. before any test run insert a category table (and other tables) needs to exist.

3. something needs to give each test a clean db session, and clean it up after. - this is where truncate table comes in - but per test, not per whole test run. Test A should see leftover test data from test B.

4. something needs to hands each test a working httpx.AsyncClient, already wired up to talk to you FastAPI app using that same clean database session - not a real network call, just an in-process fake request.

5. (later) Something needs to give tests a fake logged-in user, or a real one via login.

<IMP> 1 and 2 happen once, 3 and 4 happen fresh, every single test.

# pytest "scope"

1. scope="session" - created once, for the entire test run. this is what we'll use for db connection and migrations.
2. scope="function" - created fresh, before every single test function, and cleaned up right after. this is what we'll use for "truncate" (clean session) and the test client.
(There are a couple of in-between scopes too (like per-file), but for our case, we really only need these two.)

# shape of our conftest.py

- something like <db_engine> - session - Connect once, run Alembic migrations once
- something like <db_session> - function - Give each test a clean session, truncate tables after
- something like <client> - function - Give each test a working httpx.AsyncClient, wired to the same db session

# how does the test db know to use bakcend_platform_test instead of our real dev db?

1. separate .env.test file - a second file, just like .env, but with database_url pointing at backend_platform_test instead.
2. build the test URL by editing the real one in code - Take normal database_url, and inside conftest.py, just swap the database name at the end from backend_platform to backend_platform_test, using string logic.

3. An environment variable set only when running tests - Something like setting DATABASE_URL in the terminal right before running pytest, or in a small script.

- i am choosing option 1

# test db creation inside docker:

- creating the second database directly, using a command, without touching docker-compose.yml or restarting anything.

- Here's why that's possible - POSTGRES_DB: backend_platform only controls what happens the first time the container is created. After that, Postgres is just a normal running database server — and any normal running Postgres server lets you create additional databases at any time with a simple SQL command, no restart needed.

<steps>

1. make sure docker is running
2. enter psql : docker exec -it backend_platform_db psql -U platform -d backend_platform
3. create db using SQL: CREATE DATABASE backend_platform_test;
4. check with : \1

# how do we convice get_settings() to load .env.test sometimes?

- our get_settings():

@lru_cache
def get_settings() -> Settings:
    return Settings()

- This always builds Settings() the same way, and Settings always loads from .env — that's hardcoded in model_config. 
Nothing today tells it "hey, sometimes load .env.test instead."

- we need to make app load .env.test when we are running tests, without changing how it behaves normally.

1. set a real environment variable before the tests start, that overrides .env

- pydantic-settings has a rule: if a real environment variable already exists (like DATABASE_URL set directly in the terminal or process), 
it wins over whatever's written inside the .env file. So in conftest.py, right at the very top — before app code is even imported — 
we can load .env.test's values in as real environment variables.
Settings class doesn't need to change at all; it just sees DATABASE_URL "already set" and uses that

2. change Settings itself to know about a "testing mode"

- Add something like a TESTING flag, and inside the Settings class, 
conditionally point at .env.test instead of .env when that flag is on.

- i am choosing 1 - it keeps Settings completely untouched - app code has zero awareness that tests even exist. 
all the test specific logic stays inside conftest.py

# how conftest.py gets those values loaded as real environment variables before our app code even runs?

- There's a small library, python-dotenv, that pytest projects commonly use for exactly this — 
it reads a .env-style file and pushes each line into the actual process environment (the same place os.environ lives). 
Once that's done, when our Settings class asks pydantic-settings to build itself, 
it'll find DATABASE_URL already sitting in the real environment — 
and real environment variables take priority over whatever's written in .env.

- common first-time mistake - this has to happen before anything imports our app's settings or database code. 
If src.core.database.session gets imported first — and remember, that file runs get_settings() immediately at the top, 
outside any function — it'll cache the wrong database URL before we ever get a chance to override it.

# so order of operations inside conftest.py has to be strict:

1. load .env.test into the real environment (using python-dotenv)
2. only after that - import anything from src.core...(settings, sessions, your app, anything)

- we have to make sure that we installed the python-dotenv - uv add python-dotenv --dev (because it's only needed in devlopment)

# creating conftest.py

<step-1> loading .env.test before anything else:

from dotenv import load_dotenv
load_dotenv(".env.test", override=True)

- two things worth pointing out:

1. load_dotenv(".env.test", override=True) - telling Python to read the test config file and 
put those values into the environment that our code uses. 
python-dotenv does this by loading key-value pairs from a .env file into os.environ for the current process.

2. The important part is override=True. Without it, if a variable like DATABASE_URL is already set somewhere else, 
Python will keep that old value and ignore the one from .env.test. 
That can cause confusing pytest failures because our tests may accidentally talk to the wrong database.

<step-2>  creating the test database engine (session-scoped, runs once)

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.core.config.settings import get_settings
@pytest_asyncio.fixture(scope="session")
async def db_engine():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    yield engine
    await engine.dispose()

<notice>

- few things worth pointing out here:

1. pytest_asyncio.fixture instead of plain @pytest.fixture — 
because this function is async def. Plain pytest fixtures don't know how to run async code; 
this decorator is what tells pytest "this one needs an event loop to run."
2. scope="session" — this is the "once per whole run" scope
3. The yield in the middle — this is the same pattern as our own get_db() function. 
Code before yield runs as setup; code after yield runs as teardown, once all tests are done. 
Here, engine.dispose() cleanly closes all the database connections when the whole test run finishes.
4. get_settings() is called inside the fixture function, not at import time — 
this is deliberate, so it only runs after .env.test has already been loaded in Step 1.

<step-3> creating tables in the empty db - alembic migrations

- two options for creating tables using alembic migrations

1. have conftest.py literally run that same command as a subprocess, like a script would
2. call Alembic's own Python API directly inside the fixture, so it runs "in process" without spawning a separate command

- Option 2 stays inside the same Python process that already has .env.test loaded — 
so there's no risk of it "forgetting" which database it's supposed to point at.

- Here's roughly how that looks, added into db_engine:

import asyncio
from alembic import command
from alembic.config import Config
@pytest_asyncio.fixture(scope="session")
async def db_engine():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    alembic_cfg = Config("alembic.ini")
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    yield engine
    await engine.dispose()

<step-4> db_session fixture, the function-scoped fixture - gives each individual test a clean, ready-to-use session, then truncates the tables afterward.

- Here's the shape:

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
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

<notice> 

- here we are instead of hardcoding table names, we are askingd postgres itself what tables currently exist in platform and hospital schemas, 
right at truncate time, and trucate whatever it finds. This way, the list is never out of date — it's not a list at all, it's a live query.

- information_schema.tables is a special, built-in view every Postgres database has — 
it's not one of our tables, it's Postgres's own internal catalog of "here's every table that currently exists." 
We filter it down to our two schemas, and exclude alembic_version on purpose 
(truncating that would wipe out Alembic's memory of which migrations have already run — that's bookkeeping, not test data)

<questions>

- why does this fixture take db_engine as parameter?

-  This is that "fixtures depending on other fixtures" idea from earlier — 
pytest sees db_session asking for db_engine by name, runs db_engine first (only once, since it's session-scoped), 
and hands the result in. db_session needs the engine to build sessions from.

- Why truncate after the test, not before?

- Either order technically works for the very first test. But doing it after means the database is always left clean and ready, no matter how a previous test failed or crashed halfway through — the cleanup doesn't depend on the next test remembering to do it first.

- Why RESTART IDENTITY CASCADE specifically?

1. RESTART IDENTITY resets auto-incrementing ID counters back to 1 (matters for audit_logs, since that's our one BigInteger auto-increment table)
2. CASCADE — this is important. Since our tables have foreign keys pointing at each other (Stock → Medicine → Category, for example), Postgres would normally refuse to truncate a table that something else still references. CASCADE tells it to truncate all the dependent tables together, safely, in one shot — instead of us having to figure out the exact right order by hand

<step-4> client fixture - the httpx.AsyncClient that actually sends fake requests into FastAPI app

- Here's the key problem this fixture has to solve: our FastAPI app, right now, 
gets its database session from get_db() — which builds a session from the real async_session_factory in session.py, 
pointing at our real dev database. If we don't do anything about it, even with .env.test loaded, 
our app itself would still reach for the real database when handling a request — 
because session.py's objects were already built before we ever loaded .env.test.

- we don't want to build a brand new session inside the override. 
We want to hand the app the exact same session that db_session already created for this test.

<notice>

- Why does that matter?
- if the test creates one session, and the app (handling the fake request) creates a different session, 
they're technically two separate database connections. Depending on transaction visibility rules, 
the test might not even "see" data the app just inserted, or vice versa, until something commits. 
Sharing the exact same session guarantees test code and app code are looking at the database through the same lens.

- So the override function needs to depend on db_session too, and just yield it straight through:

async def override_get_db(db_session):
    yield db_session

- Now here's where it gets wired into the actual app. 
FastAPI has a built-in mechanism exactly for this — 
app.dependency_overrides, a dictionary where we say "whenever a request asks for this dependency, give it this other one instead."

from httpx import AsyncClient, ASGITransport

from src.core.database.session import get_db
from main import app  # or wherever the FastAPI() instance actually lives

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

<notice>

1. ASGITransport(app=app) — this is the "transport layer". 
Normally httpx.AsyncClient sends requests over a real network socket. 
ASGITransport tells it instead: "don't go over the network at all — 
call the FastAPI app's code directly, in-process." 
That's what makes this fast and not require a running server.

2. app.dependency_overrides.clear() at the end — this resets the override after each test, 
so one test's override never accidentally leaks into a different test that might not even want it.

