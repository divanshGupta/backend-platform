import logging
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.hospital.medicine.stock_model import Stock
from src.apps.hospital.medicine.stock_repository import StockRepository
from src.apps.hospital.medicine.medicine_repository import MedicineRepository

from src.packages.audit.service import AuditService
from src.packages.audit.utils import serialize_model


logger = logging.getLogger(__name__)


class StockNotFoundError(Exception):
    pass


class InvalidMedicineError(Exception):
    pass


class InsufficientStockError(Exception):
    """Raised when a negative adjustment would take quantity below zero."""
    pass


class StockService:
    """
    Business logic for Stock. Orchestrates StockRepository plus a
    read-only check against MedicineRepository to validate the FK
    before insert. Never writes SQL directly.
    """

    def __init__(self, session: AsyncSession, audit_service: AuditService):
        self.repository = StockRepository(session)
        self.medicine_repository = MedicineRepository(session)
        self.audit_service = audit_service

    async def create_stock(
        self, medicine_id: uuid.UUID, batch_number: str, quantity: int, expiry_date: date
    ) -> Stock:
        if await self.medicine_repository.get_by_id(medicine_id) is None:
            raise InvalidMedicineError(f"Medicine not found: {medicine_id}")

        if quantity < 0:
            raise InsufficientStockError("Initial quantity cannot be negative")

        stock = Stock(
            medicine_id=medicine_id,
            batch_number=batch_number,
            quantity=quantity,
            expiry_date=expiry_date,
        )
        stock = await self.repository.create(stock)

        logger.info(
            "Stock created: stock_id=%s medicine_id=%s batch=%s quantity=%s expiry=%s",
            stock.id, medicine_id, batch_number, quantity, expiry_date,
        )
        return stock

    async def adjust_stock(self, stock_id: uuid.UUID, delta: int, reason: str) -> Stock:
        """
        Adjusts quantity by `delta` (positive or negative) rather than
        overwriting it directly — preserves the intent behind every
        change instead of just the final number.

        NOTE: `reason` is logged only, not yet persisted to the DB.
        Once packages/audit exists, this is where it hooks in — this
        method's signature won't need to change, just its body.
        """
        stock = await self.repository.get_by_id(stock_id)
        if stock is None:
            raise StockNotFoundError(f"Stock not found: {stock_id}")
        
        old_value = serialize_model(stock) # full snapshot, befoer mutatino

        new_quantity = stock.quantity + delta
        if new_quantity < 0:
            raise InsufficientStockError(
                f"Cannot adjust stock {stock_id} by {delta}: "
                f"would result in negative quantity ({stock.quantity} + {delta} = {new_quantity})"
            )

        stock.quantity = new_quantity
        stock = await self.repository.update(stock)

        new_value = serialize_model(stock)
        new_value["reason"] = reason # not a stock column - tacked onto new_value as action context

        # logger.info(
        #     "Stock adjusted: stock_id=%s delta=%s new_quantity=%s reason=%s",
        #     stock_id, delta, new_quantity, reason,
        # )

        await self.audit_service.record(
            action="stock.adjust",
            entity_type="Stock",
            entity_id=stock.id,
            old_value=old_value,
            new_value=new_value,
        )
        return stock

    async def update_batch_details(
        self,
        stock_id: uuid.UUID,
        batch_number: str | None = None,
        expiry_date: date | None = None,
    ) -> Stock:
        """Corrects typos/data-entry mistakes on batch_number or expiry_date.
        Does NOT touch quantity — that only moves through adjust_stock()."""
        stock = await self.repository.get_by_id(stock_id)
        if stock is None:
            raise StockNotFoundError(f"Stock not found: {stock_id}")

        if batch_number is not None:
            stock.batch_number = batch_number
        if expiry_date is not None:
            stock.expiry_date = expiry_date

        return await self.repository.update(stock)

    async def delete_stock(self, stock_id: uuid.UUID) -> None:
        stock = await self.repository.get_by_id(stock_id)
        if stock is None:
            raise StockNotFoundError(f"Stock not found: {stock_id}")
        await self.repository.delete(stock)

    async def get_by_id(self, stock_id: uuid.UUID) -> Stock | None:
        return await self.repository.get_by_id(stock_id)

    async def list_all(self) -> list[Stock]:
        return await self.repository.list_all()

    async def list_by_medicine(self, medicine_id: uuid.UUID) -> list[Stock]:
        return await self.repository.list_by_medicine(medicine_id)