from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.apps.hospital.purchase.purchase_service import PurchaseService


def get_purchase_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PurchaseService:
    return PurchaseService(session)