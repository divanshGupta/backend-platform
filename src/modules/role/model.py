import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from src.core.database.base import PlatformBase

if TYPE_CHECKING:
    from src.modules.user.model import User
    from src.modules.permission.model import Permission

# Pure join table: no extra columns, so a plain Table object is enough —
# it never needs to be queried directly, only used via relationship(secondary=...).
role_permissions = Table(
    "role_permissions",
    PlatformBase.metadata,
    Column("role_id", ForeignKey("platform.roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("platform.permissions.id"), primary_key=True),
    schema="platform",
)

user_roles = Table(
    "user_roles",
    PlatformBase.metadata,
    Column("user_id", ForeignKey("platform.users.id"), primary_key=True),
    Column("role_id", ForeignKey("platform.roles.id"), primary_key=True),
    schema="platform",
)


class Role(PlatformBase):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles"
    )

    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")