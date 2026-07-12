from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.apps.hospital.medicine.stock_service import StockService
from src.packages.audit.dependencies import get_audit_service
from src.packages.audit.service import AuditService


def get_stock_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> StockService:
    return StockService(session, audit_service)