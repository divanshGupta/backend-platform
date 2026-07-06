from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.modules.user.service import UserService

from src.modules.user.token_repository import RefreshTokenRepository
from src.modules.user.auth_service import AuthService

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

