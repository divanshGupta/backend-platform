from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.model import User
from src.modules.user.repository import UserRepository
from src.modules.role.repository import RoleRepository
from src.packages.auth.hashing import hash_password

class RoleNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateUsernameError(Exception):
    pass


class UserService:
    """
    Business logic for User. Orchestrates the repository and the
    hashing package. Never writes SQL directly.
    """

    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)
        self.role_repository = RoleRepository(session)

    async def create_user(self, email: str, username: str, plain_password: str) -> User:
        if await self.repository.get_by_email(email) is not None:
            raise DuplicateEmailError(f"Email already registered: {email}")

        if await self.repository.get_by_username(username) is not None:
            raise DuplicateUsernameError(f"Username already taken: {username}")

        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(plain_password),
        )
        return await self.repository.create(user)
    
    async def assign_role(self, user_id, role_name: str) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")

        role = await self.role_repository.get_by_name(role_name)
        if role is None:
            raise RoleNotFoundError(f"Role not found: {role_name}")

        if role not in user.roles:
            user.roles.append(role)

        return user