from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=not settings.is_production,  # log SQL in dev, silent in prod
    pool_pre_ping=True,  # check connection is alive before using it from the pool
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency. Yields a session scoped to a single request.

    - Commits automatically if the request handler completes without error.
    - Rolls back automatically if an exception propagates.
    - Always closes the session, returning the connection to the pool.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()