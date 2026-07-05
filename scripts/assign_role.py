import asyncio

from src.core.database import model_registry  # noqa: F401
from src.core.database.session import async_session_factory
from src.modules.user.repository import UserRepository
from src.modules.user.service import UserService


async def main():
    async with async_session_factory() as session:
        service = UserService(session)
        user_repo = UserRepository(session)

        user = await user_repo.get_by_email("raj@example.com")
        if user is None:
            print("User not found — check the email matches an existing user.")
            return

        updated_user = await service.assign_role(user.id, "Pharmacist")
        await session.commit()

        print(f"User {updated_user.email} now has roles: {[r.name for r in updated_user.roles]}")


if __name__ == "__main__":
    asyncio.run(main())