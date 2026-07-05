from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.permission.model import Permission


class PermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name(self, name: str) -> Permission | None:
        result = await self.session.execute(
            select(Permission).where(Permission.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, permission: Permission) -> Permission:
        self.session.add(permission)
        await self.session.flush()
        return permission