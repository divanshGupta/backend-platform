from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

import jwt

from src.core.config.settings import get_settings

settings = get_settings()

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised when a token is malformed, has a bad signature, or wrong type."""


class ExpiredTokenError(Exception):
    """Raised when a token's expiry has passed."""


def _create_token(subject: UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),   # subject = user id
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    return _create_token(
        user_id,
        TokenType.ACCESS,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(
        user_id,
        TokenType.REFRESH,
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: TokenType) -> UUID:
    """Decode and validate a token, returning the user_id it belongs to.

    Raises ExpiredTokenError or InvalidTokenError — callers map these to HTTP 401.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError("Token has expired")
    except jwt.InvalidTokenError:
        raise InvalidTokenError("Token is invalid")

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Expected {expected_type.value} token")

    return UUID(payload["sub"])