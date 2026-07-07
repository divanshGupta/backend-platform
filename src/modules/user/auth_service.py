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

class ReusedRefreshTokenError(Exception):
    """Raised when a revoked (already-used) refresh token is presented again.
    Signals likely token theft — caller should force full re-authentication."""

class InvalidRefreshTokenError(Exception):
    """Raised for any other refresh-token failure. Kept generic — don't leak
    *why* a token was rejected."""

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
    
    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        try:
            user_id = decode_token(raw_refresh_token, expected_type=TokenType.REFRESH)
        except (InvalidTokenError, ExpiredTokenError):
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        token_hash = hash_token(raw_refresh_token)
        stored_token = await self._token_repository.get_by_hash(token_hash)

        if stored_token is None:
            # Signature was valid but we have no record of it. Shouldn't happen
            # in normal operation — treat as invalid, not as a special case.
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        if stored_token.revoked:
            await self._token_repository.revoke_all_for_user(user_id)
            await self._token_repository.commit()  # persist before raising — see method docstring
            raise ReusedRefreshTokenError("Refresh token reuse detected")

        if stored_token.expires_at < datetime.now(timezone.utc):
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        user = await self._user_service.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        # Rotation: revoke the old token, issue a completely new pair.
        await self._token_repository.revoke(stored_token.id)

        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)

        await self._token_repository.create(
            RefreshToken(
                id=uuid.uuid4(),
                user_id=user.id,
                token_hash=hash_token(new_refresh_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.jwt_refresh_token_expire_days),
                revoked=False,
                created_at=datetime.now(timezone.utc),
            )
        )

        return TokenPair(access_token=new_access_token, refresh_token=new_refresh_token)

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_token(raw_refresh_token)
        stored_token = await self._token_repository.get_by_hash(token_hash)

        # Idempotent by design: whether the token was valid, already revoked,
        # or never existed, logout always looks the same from the outside.
        # Logout isn't a security boundary the same way login is — there's
        # no meaningful secret to protect by distinguishing these cases here.
        if stored_token is not None and not stored_token.revoked:
            await self._token_repository.revoke(stored_token.id)
