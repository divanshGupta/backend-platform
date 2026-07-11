import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.hospital.purchase.purchase_model import Purchase
from src.apps.hospital.purchase.purchase_repository import PurchaseRepository
from src.apps.hospital.medicine.medicine_repository import MedicineRepository
from src.apps.hospital.supplier.supplier_repository import SupplierRepository
from src.apps.hospital.medicine.stock_service import StockService


class PurchaseNotFoundError(Exception):
    pass


class InvalidMedicineError(Exception):
    pass


class InvalidSupplierError(Exception):
    pass


class PurchaseService:
    """
    Business logic for Purchase. Orchestrates PurchaseRepository directly,
    plus StockService (not StockRepository) for the Stock this purchase
    produces — Stock's own business rules (quantity validation, etc.) must
    run, not be duplicated here. See project discussion: services call
    other services for anything outside their own domain, never reach
    past a service into a repository they don't own.
    """

    def __init__(self, session: AsyncSession):
        self.repository = PurchaseRepository(session)
        self.medicine_repository = MedicineRepository(session)
        self.supplier_repository = SupplierRepository(session)
        self.stock_service = StockService(session)

    async def create_purchase(
        self,
        medicine_id: uuid.UUID,
        supplier_id: uuid.UUID,
        batch_number: str,
        quantity: int,
        unit_price: Decimal,
        expiry_date: date,
        purchase_date: date,
    ) -> Purchase:
        if await self.medicine_repository.get_by_id(medicine_id) is None:
            raise InvalidMedicineError(f"Medicine not found: {medicine_id}")

        if await self.supplier_repository.get_by_id(supplier_id) is None:
            raise InvalidSupplierError(f"Supplier not found: {supplier_id}")

        # Stock's own validation (quantity >= 0 etc.) runs inside
        # StockService.create_stock — not re-implemented here.
        # stock_id is left null on the Purchase row initially; it's filled
        # in immediately after Stock exists, in the same transaction/session,
        # so both writes commit or roll back together.
        purchase = Purchase(
            medicine_id=medicine_id,
            supplier_id=supplier_id,
            batch_number=batch_number,
            quantity=quantity,
            unit_price=unit_price,
            expiry_date=expiry_date,
            purchase_date=purchase_date,
        )
        purchase = await self.repository.create(purchase)

        stock = await self.stock_service.create_stock(
            medicine_id=medicine_id,
            batch_number=batch_number,
            quantity=quantity,
            expiry_date=expiry_date,
        )

        purchase = await self.repository.set_stock_link(purchase, stock.id)
        return purchase

    async def get_by_id(self, purchase_id: uuid.UUID) -> Purchase | None:
        return await self.repository.get_by_id(purchase_id)

    async def list_all(self) -> list[Purchase]:
        return await self.repository.list_all()

    async def list_by_medicine(self, medicine_id: uuid.UUID) -> list[Purchase]:
        return await self.repository.list_by_medicine(medicine_id)