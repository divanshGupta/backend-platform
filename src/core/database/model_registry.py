"""
Imports every SQLAlchemy model in the system, ensuring they're all
registered with SQLAlchemy's mapper registry before any relationship
(e.g. Mapped[list["User"]]) needs to resolve a class by name.

Any file that queries the database — Alembic's env.py, seed scripts,
the FastAPI app itself — should import this module first.

When you add a new model anywhere in modules/ or apps/, add its
import here. Forgetting this step causes a mapper configuration
error the first time a relationship touches the missing class —
usually with a large, confusing traceback pointing at the wrong file.
"""

from src.modules.user.model import User  # noqa: F401
from src.modules.role.model import Role  # noqa: F401
from src.modules.permission.model import Permission  # noqa: F401