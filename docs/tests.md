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

