# Extending Audit Logging to a New Service — Manual

_Use this to add audit logging to Medicine, Purchase, Category, Supplier, or any
future service, without re-deriving the pattern from scratch. The mechanism
itself (`packages/audit`) is done — this is purely about wiring an existing
service into it, mirroring what `StockService.adjust_stock()` already does._

## Before you start

Decide, per mutation, what `action` string to use. Convention established with
Stock: `"{entity}.{verb}"`, lowercase, dot-separated — e.g. `"medicine.create"`,
`"medicine.update"`, `"medicine.delete"`, `"purchase.create"`. Keep it consistent
with your existing permission-naming convention (`medicine.read`, `stock.adjust`),
since these audit action strings and your RBAC permission strings live in the
same "dotted resource.verb" style.

## Steps

### 1. Import what you need into the target service file

```python
from src.packages.audit.service import AuditService
from src.packages.audit.utils import serialize_model
```

### 2. Add `audit_service` to the service's `__init__`

```python
class MedicineService:
    def __init__(self, session: AsyncSession, audit_service: AuditService):
        self.repository = MedicineRepository(session)
        self.audit_service = audit_service
```

### 3. Update the corresponding dependency factory

Same pattern as `get_stock_service` — both dependencies must resolve from the
**same `get_db`** so FastAPI hands them the same `AsyncSession` per request. This
is what makes the audit write and the business mutation atomic (one commits or
rolls back with the other).

```python
from src.packages.audit.dependencies import get_audit_service
from src.packages.audit.service import AuditService

def get_medicine_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> MedicineService:
    return MedicineService(session, audit_service)
```

### 4. Instrument each mutating method

**Pattern for update:**

```python
async def update_medicine(self, medicine_id: uuid.UUID, ...) -> Medicine:
    medicine = await self.repository.get_by_id(medicine_id)
    if medicine is None:
        raise MedicineNotFoundError(medicine_id)

    old_value = serialize_model(medicine)   # snapshot BEFORE mutation

    # ... apply your changes to medicine's fields ...
    medicine = await self.repository.update(medicine)

    new_value = serialize_model(medicine)   # snapshot AFTER mutation

    await self.audit_service.record(
        action="medicine.update",
        entity_type="Medicine",
        entity_id=medicine.id,
        old_value=old_value,
        new_value=new_value,
    )
    return medicine
```

**Pattern for create** — `old_value` is `None`, since nothing existed before:

```python
async def create_medicine(self, ...) -> Medicine:
    medicine = Medicine(...)
    medicine = await self.repository.create(medicine)

    await self.audit_service.record(
        action="medicine.create",
        entity_type="Medicine",
        entity_id=medicine.id,
        old_value=None,
        new_value=serialize_model(medicine),
    )
    return medicine
```

**Pattern for delete** — capture the snapshot **before** deleting (you can't
serialize a row that's already gone); `new_value` is `None`:

```python
async def delete_medicine(self, medicine_id: uuid.UUID) -> None:
    medicine = await self.repository.get_by_id(medicine_id)
    if medicine is None:
        raise MedicineNotFoundError(medicine_id)

    old_value = serialize_model(medicine)   # capture BEFORE delete
    await self.repository.delete(medicine)

    await self.audit_service.record(
        action="medicine.delete",
        entity_type="Medicine",
        entity_id=medicine_id,
        old_value=old_value,
        new_value=None,
    )
```

### 5. Any extra, non-column context (like Stock's `reason`)?

Tack it onto `new_value` as an extra key rather than adding a real column, if
it's context about the *action* rather than a fact about the entity — same
reasoning as Stock's `reason`:

```python
new_value = serialize_model(medicine)
new_value["note"] = some_context_string
```

### 6. Test it the same way the Stock pilot was verified

Don't trust the API response alone. After hitting the endpoint:

```sql
SELECT actor_user_id, action, entity_type, entity_id, old_value, new_value, ip_address, created_at
FROM platform.audit_logs
ORDER BY created_at DESC LIMIT 1;
```

Confirm: `actor_user_id` is the real logged-in user (not null), `ip_address` is
populated, `old_value`/`new_value` show the actual field(s) that changed, and
for creates/deletes the null side is genuinely null.

## Common pitfalls (all already hit once during the Stock pilot — don't repeat them)

- **New column type, not in `serialize_model()` yet** — if the entity has an
  `Enum`, or any type beyond `str`/`int`/`bool`/`float`/`datetime`/`date`/
  `Decimal`/`uuid.UUID`, add a branch to `serialize_model()` in
  `packages/audit/utils.py` before you hit a `TypeError` at request time.
- **Dependency factory using a different session than expected** — if
  `get_X_service` and `get_audit_service` don't both ultimately depend on the
  same `get_db`, you silently lose the atomic-transaction guarantee. Double-check
  the dependency chain, don't just assume it.
- **Capturing `old_value` after the mutation instead of before** — always
  serialize the "before" state first, before touching any field or calling
  `repository.update()`/`delete()`.
- **Forgetting the delete case needs its snapshot before the row is gone** —
  there's no "after" to read once it's deleted.

## Rollout order suggestion

Not required, but sensible: Category and Supplier first (simplest, full CRUD,
low risk), then Medicine (slightly more fields), then Purchase last — Purchase
is append-only (create + read only) so it only ever needs the "create" pattern,
never update/delete.