import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.token_model import RefreshToken


class RefreshTokenRepository:
    """
    Data access for RefreshToken. Knows how to read/write
    `platform.refresh_tokens`. Contains no business rules.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked=True)
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
            .values(revoked=True)
        )

    async def commit(self) -> None:
        """Force this repository's pending writes to persist immediately,
        independent of the request's overall commit/rollback outcome.

        Used only for security-critical writes (like mass token revocation)
        that must survive even when the request itself is about to fail —
        the normal per-request commit-on-success pattern would otherwise
        silently discard them on rollback.
        """
        await self.session.commit()