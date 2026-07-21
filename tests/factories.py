from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from itertools import count

from src.apps.hospital.medicine.category_model import Category
from src.apps.hospital.supplier.supplier_model import Supplier

_category_counter = count(1)


class CategoryFactory(SQLAlchemyFactory[Category]):
    __model__ = Category

    @classmethod
    def name(cls) -> str:
        return f"Test Category {next(_category_counter)}"
    

class SupplierFactory(SQLAlchemyFactory[Supplier]):
    __model__ = Supplier
    