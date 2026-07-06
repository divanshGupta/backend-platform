# src/modules/user/auth_service.py

import uuid
from datetime import datetime, timedelta, timezone

from src.core.config.settings import get_settings
from src.modules.user.service import UserService, InvalidCredentialsError
from src.modules.user.token_model import RefreshToken
from src.modules.user.token_repository import RefreshTokenRepository
from src.packages.auth.jwt import create_access_token, create_refresh_token, decode_token, TokenType
from src.packages.auth.jwt import InvalidTokenError, ExpiredTokenError
from src.packages.auth.token_hash import hash_token

settings = get_settings()


class TokenPair:
    """Simple DTO — not a DB model, just what the controller hands back."""
    def __init__(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = "bearer"


class AuthService:
    def __init__(self, user_service: UserService, token_repository: RefreshTokenRepository):
        self._user_service = user_service
        self._token_repository = token_repository

    async def login(self, email: str, plain_password: str) -> TokenPair:
        # Raises InvalidCredentialsError on any failure — controller maps to 401.
        user = await self._user_service.authenticate_user(email, plain_password)

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        await self._token_repository.create(
            RefreshToken(
                id=uuid.uuid4(),
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.jwt_refresh_token_expire_days),
                revoked=False,
                created_at=datetime.now(timezone.utc),
            )
        )

        return TokenPair(access_token=access_token, refresh_token=refresh_token)