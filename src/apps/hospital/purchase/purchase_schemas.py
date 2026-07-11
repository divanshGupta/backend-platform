import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

from src.apps.hospital.medicine.medicine_schemas import MedicineRead
from src.apps.hospital.supplier.supplier_schemas import SupplierRead
from src.apps.hospital.medicine.stock_schemas import StockRead


class PurchaseCreate(BaseModel):
    medicine_id: uuid.UUID
    supplier_id: uuid.UUID
    batch_number: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0)
    unit_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    expiry_date: date
    purchase_date: date


class PurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    medicine: MedicineRead
    supplier: SupplierRead
    stock: StockRead | None
    batch_number: str
    quantity: int
    unit_price: Decimal
    expiry_date: date
    purchase_date: date