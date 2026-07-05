import asyncio

from src.core.database.session import async_session_factory
from src.modules.user.service import UserService


async def main():
    async with async_session_factory() as session:
        service = UserService(session)
        user = await service.create_user(
            email="raj@example.com",
            username="raj",
            plain_password="TestPassword123!",
        )
        await session.commit()
        print(f"Created user: id={user.id}, email={user.email}, hashed_password={user.hashed_password[:30]}...")


if __name__ == "__main__":
    asyncio.run(main())