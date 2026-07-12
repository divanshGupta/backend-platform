import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import PlatformBase 


class AuditLog(PlatformBase):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_platform_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_platform_audit_logs_created_at", "created_at"),
        {"schema": "platform"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # SET NULL, not RESTRICT — audit history must outlive the user who caused it.
    # This mirrors Purchase.stock_id's reasoning: independent lifecycles.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform.users.id", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(String(100))       # eg. "stock.adjust"
    entity_type: Mapped[str] = mapped_column(String(100))  # eg. "Stock"
    
    # String, not int — a generic audit package can't assume every future
    # entity (across Restaurant/Pharmacy/whatever clones this repo) uses
    # integer PKs. Stringify at the call site.
    entity_id: Mapped[str] = mapped_column(String(100)) 

    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())