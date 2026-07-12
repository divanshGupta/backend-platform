from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from src.modules.user.model import User
from src.packages.auth.jwt import decode_token, TokenType, InvalidTokenError, ExpiredTokenError

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.modules.user.service import UserService

from src.modules.user.token_repository import RefreshTokenRepository
from src.modules.user.auth_service import AuthService

# audit
from src.packages.audit.context import set_actor

bearer_scheme = HTTPBearer()

def get_user_service(
        session: Annotated[AsyncSession, Depends(get_db)],
) -> UserService:
    """
        Provides a UserService with its session dependency already wired.
        FastAPI resolves get_db() once per request (session lifecycle
        handled there), then injects it here — the route function never
        touches session management directly.
    """
    return UserService(session)

def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def get_auth_service(
    user_service: Annotated[UserService, Depends(get_user_service)],
    token_repository: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> AuthService:
    return AuthService(user_service, token_repository)

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    try:
        user_id = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except (InvalidTokenError, ExpiredTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_service.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    #for auditing
    set_actor(user.id)
    return user

def require_permission(permission: str):
    """
    Returns a FastAPI dependency that checks whether the current user
    has the given permission (e.g. "medicine.create").

    Usage in a route:
        @router.post("/medicines", dependencies=[Depends(require_permission("medicine.create"))])
    """
    async def _check_permission(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        user_permissions = {
            perm.name
            for role in current_user.roles
            for perm in role.permissions
        }

        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )

        return current_user

    return _check_permission