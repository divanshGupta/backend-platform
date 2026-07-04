from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Explicit naming convention for constraints/indexes.
# Without this, Postgres auto-generates names, and Alembic's
# autogenerate can silently produce broken/mismatched migrations
# when comparing constraint names across environments.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

class PlatformBase(Base):
    """
    Base for all models in the `platform` schema — identity and
    access-control data (users, roles, permissions, refresh tokens,
    audit logs) shared across whichever business app this deployment
    is currently running.
    """
    __abstract__ = True
    __table_args__ = {"schema": "platform"}
