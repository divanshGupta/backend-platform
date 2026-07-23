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

from tests.factories import CategoryFactory, SupplierFactory

from src.apps.hospital.medicine.medicine_model import Medicine


# fixture that returns ALL_PERMISSION_NAMES (Admin)
@pytest_asyncio.fixture
def current_user_permissions():
    return ALL_PERMISSION_NAMES  # default: acts like Admin

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

# @pytest_asyncio.fixture(scope="function")
# async def client(db_session, current_user_permissions):
#     test_app = create_app()

#     async def override_get_db():
#         yield db_session

#     async def override_get_current_user():
#         return FakeUser(current_user_permissions)

#     test_app.dependency_overrides[get_db] = override_get_db
#     test_app.dependency_overrides[get_current_user] = override_get_current_user

#     transport = ASGITransport(app=test_app)
#     async with AsyncClient(transport=transport, base_url="http://test") as ac:
#         yield ac

#     test_app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def client(db_engine, db_session, current_user_permissions):
    test_app = create_app()
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            # i am not using finally block here. session_factory already used
            # inside an async with block, which handles closing the session on its own
            # adding an explicit finally block while we are using async with, would be redundent.

    async def override_get_current_user():
        return FakeUser(current_user_permissions)

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def category_and_supplier(db_session):
    category = CategoryFactory.build()
    supplier = SupplierFactory.build()

    db_session.add(category)
    db_session.add(supplier)
    await db_session.commit()

    return category, supplier


@pytest_asyncio.fixture
async def medicine(db_session, category_and_supplier):
    category, supplier = category_and_supplier

    medicine = Medicine(
        name="Paracetamol 500mg",
        category_id=category.id,
        supplier_id=supplier.id,
    )
    db_session.add(medicine)
    await db_session.commit()

    return medicine