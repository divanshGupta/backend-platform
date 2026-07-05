from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.modules.user.service import UserService

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