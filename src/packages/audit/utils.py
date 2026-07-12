import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def serialize_model(instance: Any) -> dict[str, Any]:
    """Full-row snapshot of a SQLAlchemy model instance as JSON-safe primitives."""
    result = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        elif isinstance(value, uuid.UUID):
            value = str(value)
        result[column.name] = value
    return result


"""
This exists because Decimal and datetime aren't JSON-serializable by default, 
and we've already been explicit everywhere else about never silently coercing Decimal to float. 
Reusable for any future entity — Medicine, Purchase, whatever gets audited next.
"""