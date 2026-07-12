from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db 
from src.packages.audit.repository import AuditRepository
from src.packages.audit.service import AuditService

def get_audit_service(session: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(AuditRepository(session))