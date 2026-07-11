import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.apps.hospital.purchase.purchase_dependencies import get_purchase_service
from src.apps.hospital.purchase.purchase_schemas import PurchaseCreate, PurchaseRead
from src.apps.hospital.purchase.purchase_service import (
    PurchaseService,
    InvalidMedicineError,
    InvalidSupplierError,
)
from src.modules.user.dependencies import require_permission

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post(
    "", response_model=PurchaseRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("purchase.create"))],
)
async def create_purchase(
    data: PurchaseCreate,
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> PurchaseRead:
    try:
        purchase = await service.create_purchase(
            medicine_id=data.medicine_id,
            supplier_id=data.supplier_id,
            batch_number=data.batch_number,
            quantity=data.quantity,
            unit_price=data.unit_price,
            expiry_date=data.expiry_date,
            purchase_date=data.purchase_date,
        )
    except InvalidMedicineError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidSupplierError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return PurchaseRead.model_validate(purchase)


@router.get(
    "", response_model=list[PurchaseRead],
    dependencies=[Depends(require_permission("purchase.read"))],
)
async def list_purchases(
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> list[PurchaseRead]:
    purchases = await service.list_all()
    return [PurchaseRead.model_validate(p) for p in purchases]


# Must stay ABOVE /{purchase_id} — same routing-order rule as before.
@router.get(
    "/by-medicine/{medicine_id}", response_model=list[PurchaseRead],
    dependencies=[Depends(require_permission("purchase.read"))],
)
async def list_purchases_by_medicine(
    medicine_id: uuid.UUID,
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> list[PurchaseRead]:
    purchases = await service.list_by_medicine(medicine_id)
    return [PurchaseRead.model_validate(p) for p in purchases]


@router.get(
    "/{purchase_id}", response_model=PurchaseRead,
    dependencies=[Depends(require_permission("purchase.read"))],
)
async def get_purchase(
    purchase_id: uuid.UUID,
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> PurchaseRead:
    purchase = await service.get_by_id(purchase_id)
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
    return PurchaseRead.model_validate(purchase)