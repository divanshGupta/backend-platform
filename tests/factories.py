from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from itertools import count

from src.apps.hospital.medicine.category_model import Category

_category_counter = count(1)


class CategoryFactory(SQLAlchemyFactory[Category]):
    __model__ = Category

    @classmethod
    def name(cls) -> str:
        return f"Test Category {next(_category_counter)}"