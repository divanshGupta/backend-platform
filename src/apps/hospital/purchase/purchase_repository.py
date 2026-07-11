import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.hospital.purchase.purchase_model import Purchase


class PurchaseRepository:
    """
    Data access for Purchase. Knows how to read/write `hospital.purchases`.
    No update()/delete() — purchases are append-only by design (financial
    audit record, corrections happen as new entries, not edits to history).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, purchase_id: uuid.UUID) -> Purchase | None:
        result = await self.session.execute(
            select(Purchase).where(Purchase.id == purchase_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Purchase]:
        result = await self.session.execute(
            select(Purchase).order_by(Purchase.purchase_date.desc())
        )
        return list(result.scalars().all())

    async def list_by_medicine(self, medicine_id: uuid.UUID) -> list[Purchase]:
        result = await self.session.execute(
            select(Purchase)
            .where(Purchase.medicine_id == medicine_id)
            .order_by(Purchase.purchase_date.desc())
        )
        return list(result.scalars().all())

    async def create(self, purchase: Purchase) -> Purchase:
        self.session.add(purchase)
        await self.session.flush()
        return await self.get_by_id(purchase.id)

    async def set_stock_link(self, purchase: Purchase, stock_id: uuid.UUID) -> Purchase:
        """The only mutation this repository allows post-creation — linking
        the Purchase to the Stock row it produced. Not a general update()."""
        purchase.stock_id = stock_id
        await self.session.flush()
        # Plain get_by_id() here would return the SAME Python object from the
        # session's identity map with its `stock` relationship still cached as
        # the pre-update value (None) — SQLAlchemy doesn't know to distrust an
        # already-loaded relationship just because the underlying FK changed.
        # session.refresh() with an explicit attribute_names list forces exactly
        # that attribute to be reloaded from the DB.
        await self.session.refresh(purchase, attribute_names=["stock"])
        return purchase