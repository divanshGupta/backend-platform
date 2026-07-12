from typing import Any

from src.packages.audit.context import get_actor_user_id, get_ip_address
from src.packages.audit.repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def record(
        self,
        action: str,
        entity_type: str,
        entity_id: int | str,
        old_value: dict[str, Any] | None,
        new_value: dict[str, Any] | None,
    ) -> None:
        await self.repository.create(
            actor_user_id=get_actor_user_id(),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old_value=old_value,
            new_value=new_value,
            ip_address=get_ip_address(),
        )