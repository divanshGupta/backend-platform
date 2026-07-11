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
from src.modules.user.token_model import RefreshToken  # noqa: F401

# --- Hospital app models ---
from src.apps.hospital.medicine.category_model import Category  # noqa: F401
from src.apps.hospital.supplier.supplier_model import Supplier  # noqa: F401
from src.apps.hospital.medicine.medicine_model import Medicine  # noqa: F401
from src.apps.hospital.medicine.stock_model import Stock  # noqa: F401
from src.apps.hospital.purchase.purchase_model import Purchase  # noqa: F401


"""
The # noqa: F401 suppresses "unused import" linter warnings — 
the import's side effect, registering the class with metadata, 
is the whole point, so linters flagging it as "unused" are technically right but missing the purpose
"""

"""
Alembic's autogenerate works by diffing your models' metadata against the live DB schema. 
But SQLAlchemy only knows a model exists if the Python class has been imported somewhere — 
imports are what populate Base.metadata.tables. 
If a model file is never imported, it's invisible to Alembic even though the file exists on disk. 
model_registry.py is a single, deliberate "import everything" file 
so you never have to remember where a model got imported from — you just check one place.
"""