import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Date, String, Numeric, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database.base import HospitalBase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.apps.hospital.medicine.medicine_model import Medicine
    from src.apps.hospital.supplier.supplier_model import Supplier
    from src.apps.hospital.medicine.stock_model import Stock


class Purchase(HospitalBase):
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        {"schema": "hospital"},
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    medicine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hospital.medicines.id", ondelete="RESTRICT"), nullable=False
    )
    medicine: Mapped["Medicine"] = relationship(lazy="selectin")

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hospital.suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    supplier: Mapped["Supplier"] = relationship(lazy="selectin")

    # Nullable + SET NULL: unlike medicine_id/supplier_id above, Stock's
    # lifecycle is independent of Purchase's — a Stock row can legitimately
    # be deleted later (recalled/destroyed batch) without destroying the
    # historical fact that a purchase happened. RESTRICT here would wrongly
    # make purchase history block stock deletion.
    stock_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hospital.stocks.id", ondelete="SET NULL"), nullable=True
    )
    stock: Mapped["Stock | None"] = relationship(lazy="selectin")

    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)

    # Numeric(10, 2) for unit_price, mapped to Python's Decimal — never float for money. Floating point can't represent currency exactly (classic 0.1 + 0.2 != 0.3 problem)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)