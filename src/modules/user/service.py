import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.model import User
from src.modules.user.repository import UserRepository
from src.modules.role.repository import RoleRepository
from src.packages.auth.hashing import hash_password, verify_password

class RoleNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateUsernameError(Exception):
    pass


class InvalidCredentialsError(Exception):
    """Raised for any authentication failure. Deliberately generic —
    never distinguish 'no such user' from 'wrong password' to the caller."""
    pass


# A pre-computed dummy hash, used only to burn equivalent CPU time when
# the user doesn't exist — so response timing doesn't leak whether the
# email is registered. Generate once with hash_password("dummy") and paste
# the result here as a constant; don't recompute it per request.
_DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$43b6e5FcVPGIjMyhRSvsRg$6ZgAKayGkYAdTi8jcQTdqLgUFXypTwB1xB9aAwxccVA"


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
    
    async def authenticate_user(self, email: str, plain_password: str) -> User:
        user = await self.repository.get_by_email(email)

        if user is None:
            verify_password(plain_password, _DUMMY_HASH)  # burn equivalent time
            raise InvalidCredentialsError("Invalid email or password")

        if not verify_password(plain_password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            raise InvalidCredentialsError("Invalid email or password")

        return user
    
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.repository.get_by_id(user_id)
    

# What the leading underscore means
# self._repository (with the underscore) is Python's convention for "internal, not part of the public API of this class." It's not a typo, and it's not enforced by the language — Python has no true private keyword like Java or C#. It's a signal to other developers (including future-you): "don't reach into this from outside the class — it's an implementation detail."
