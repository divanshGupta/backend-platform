# Medicine, Category and Supplier

# Step 1: HospitalBase — a new declarative base for the hospital schema

# Step 2: Category model — apps/hospital/medicine/category_model.py

# Step 3: Supplier model — apps/hospital/supplier/supplier_model.py

# Step 4: Medicine model — apps/hospital/medicine/model.py

# Step 5: generate and review the migration

# Step 6: Repository layer

## these files are created:

src/core/database/base.py                          (add HospitalBase)
src/apps/hospital/medicine/category_model.py
src/apps/hospital/medicine/category_repository.py
src/apps/hospital/medicine/category_service.py
src/apps/hospital/medicine/category_schemas.py
src/apps/hospital/medicine/category_dependencies.py
src/apps/hospital/medicine/category_controller.py
src/apps/hospital/supplier/supplier_model.py
src/apps/hospital/supplier/supplier_repository.py
src/apps/hospital/supplier/supplier_service.py
src/apps/hospital/supplier/supplier_schemas.py
src/apps/hospital/supplier/supplier_dependencies.py
src/apps/hospital/supplier/supplier_controller.py
src/apps/hospital/medicine/model.py
src/apps/hospital/medicine/repository.py
src/apps/hospital/medicine/service.py
src/apps/hospital/medicine/medicine_schemas.py
src/apps/hospital/medicine/medicine_dependencies.py
src/apps/hospital/medicine/medicine_controller.py

## Full stack verified end to end:
- Schema/FK integrity confirmed at the DB level
- RBAC gating confirmed both positive (Admin succeeds) and negative (missing permission → 403)
- Nested eager-loaded serialization confirmed on create
- FK pre-validation confirmed (bad category_id → clean 400, not a raw DB error)
- ON DELETE RESTRICT confirmed to surface as a clean 409, with the underlying PendingRollbackError-masking bug found and fixed rather than papered over

## Bugs
- touching an ORM object's attributes after a failed flush — is genuinely the kind of thing worth writing down somewhere for your own reference, the same way you've been tracking the get_db rollback trap and the MissingGreenlet one. All three are variations on one theme: async SQLAlchemy fails loudly and specifically the moment you do anything with a session or object that's in a state it doesn't expect (unflushed relationship, failed transaction, wrong greenlet context). That's a real pattern worth internalizing for the modules still ahead.

# Stocks - done - 10-07


# Purchase module is genuinely complete, end-to-end - 11-07

- Purchase → Stock → Medicine → Category/Supplier

- Schema, check constraints, and all three FK behaviors confirmed correct (RESTRICT × 2, SET NULL × 1) against the live DB
- Cross-service orchestration (PurchaseService → StockService) working correctly, including the transactional safety we discussed — one write path, one shared session
- The identity-map staleness bug found and fixed, not papered over — a genuinely new failure mode for this project, distinct from the three you'd already hit
- FK pre-validation (bad medicine_id → clean 400, and confirmed no orphaned Purchase row got left behind)
- Append-only enforced at the API surface (405 on PATCH/DELETE, not just omitted from docs)
- RBAC gating confirmed positive and negative