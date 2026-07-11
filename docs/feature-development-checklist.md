# Feature development checklist — moducore pattern

A reusable, step-by-step process for adding a new entity/module to `backend-platform`,
distilled from building Category, Supplier, Medicine, Stock, and Purchase.

---

## Phase 0 — Design decisions (before writing any code)

Don't skip this phase. Every real bug in this project's history came from a decision
made silently rather than discussed. Work through these explicitly:

- [ ] **Where does this belong?** Core / Package / Module / App — per moducore.md's
      layering. If it's business-specific (like Hospital's entities), it's an App.
- [ ] **What does it depend on?** List every other entity this one references via FK.
      Build dependencies *before* dependents — never retrofit a FK onto existing data.
- [ ] **Folder placement.** Does it get its own top-level folder (like Supplier, Stock,
      Purchase) or live grouped with a closely related entity (like Category living
      inside `medicine/`)? Match precedent, don't default to nesting just because an FK exists.
- [ ] **`ondelete` behavior for every FK**, decided one at a time, not copy-pasted:
  - `RESTRICT` — default choice when deleting the parent would silently destroy or
    orphan meaningful business/audit data (inventory, financial records).
  - `SET NULL` — when the FK is a traceability/reference link whose target has an
    independent lifecycle (e.g. Purchase→Stock: Stock can be legitimately deleted
    without invalidating the historical fact that a purchase happened).
  - `CASCADE` — almost never, in this project, for anything representing real
    business state. Ask "would silently deleting this data ever be correct?"
- [ ] **CRUD scope.** Full CRUD, read-only, or append-only (create + read, no
      update/delete — for financial/audit records where "corrections" should be new
      entries, not edits to history)?
- [ ] **Cross-service orchestration?** Does creating/updating this entity need to
      trigger real business logic in another module (e.g. Purchase creating Stock)?
      If so: the calling service depends on the *other service*, never reaches past
      it into that service's repository. See Phase 6.
- [ ] **Any DB-level invariants?** (e.g. quantity/price can never be negative) — these
      become `CheckConstraint`s, not just application-level `if` checks. A constraint
      the DB enforces can't be bypassed by a future script or bug.

---

## Phase 1 — Model

- [ ] Inherit from the correct schema base (`HospitalBase`, `PlatformBase`, etc.)
- [ ] **If combining `__table_args__` constraints with a schema**, the schema dict
      must be the LAST element of the tuple: `__table_args__ = (CheckConstraint(...), {"schema": "hospital"})`.
      A bare tuple with no dict silently drops the inherited schema — caught this
      exact bug on the Stock model; verify in the generated migration, not by eye.
- [ ] Constraint `name=` should be the bare descriptive name (e.g. `"quantity_non_negative"`),
      NOT pre-prefixed — the naming convention template adds `ck_%(table_name)s_`
      automatically. Passing an already-prefixed name doubles the prefix.
- [ ] `relationship(..., lazy="selectin")` for any FK you want eager-loaded automatically
      on every SELECT. Know that this cascades — nesting a model that itself has
      `selectin` relationships multiplies the eager-load depth (fine at MVP scale,
      worth knowing before assuming it's free forever).
- [ ] Use `TYPE_CHECKING` imports for relationship type hints to avoid circular imports.
- [ ] Decide `int` vs `Numeric`/`Decimal` deliberately — **never `float` for money.**

## Phase 2 — Repository

- [ ] Constructor takes `session: AsyncSession`, stores as `self.session`.
- [ ] Standard methods: `get_by_id`, `list_all`, `create`, `update`, `delete` — only
      build what's actually needed (e.g. no `update`/`delete` for append-only entities).
- [ ] **`create()`/`update()` on any model with eager-loaded relationships must
      re-fetch after `flush()`**, not just return the in-memory object:
      ```python
      async def create(self, obj):
          self.session.add(obj)
          await self.session.flush()   # INSERT only — doesn't populate relationships
          return await self.get_by_id(obj.id)
      ```
      Skipping this causes `MissingGreenlet` the moment the response schema tries
      to read the relationship attribute.
- [ ] **If you mutate a relationship's FK column and need that relationship reloaded
      in the SAME already-loaded Python object** (e.g. linking `purchase.stock_id`
      after the purchase object already exists in the session), a second `get_by_id()`
      is NOT enough — SQLAlchemy's identity map returns the same cached object with
      the relationship still holding its stale value. Use:
      ```python
      await self.session.refresh(obj, attribute_names=["the_relationship"])
      ```
- [ ] No business rules here. No validation. Just queries.

## Phase 3 — Service

- [ ] Constructor builds its own repository, plus read-only repositories of anything
      it needs to FK-validate against, plus **full services** (not repositories) of
      anything whose business rules it needs to trigger as a side effect.
- [ ] Module-level plain `Exception` subclasses for each domain error — no HTTP
      concerns here at all.
- [ ] Validate foreign keys exist BEFORE insert (defense in depth — gives a clean
      404/400 with a specific message, rather than relying solely on the DB's FK
      violation, which doesn't say *which* FK failed).
- [ ] **Delta-based mutation, not overwrite, for anything with an audit/accountability
      requirement** (e.g. stock quantity adjustments) — preserves *why* something
      changed, not just the final value.
- [ ] **Capture any ORM attribute you'll need for an error message BEFORE an
      operation that might fail** (e.g. `name = obj.name` before `try: delete()`).
      Touching an ORM attribute AFTER a failed flush triggers a fresh reload attempt
      on a transaction that's already dead, raising `PendingRollbackError` and
      masking the real exception your `except` block was written to catch.
- [ ] Catch `sqlalchemy.exc.IntegrityError` around deletes if any FK elsewhere
      points at this table with `RESTRICT` — translate to a domain-specific
      "in use" error, not a raw 500.

## Phase 4 — Schemas (Pydantic)

- [ ] Separate `Create` / `Update` / `Read` schemas — never reuse one shape for all three.
- [ ] `Read` schemas: `model_config = ConfigDict(from_attributes=True)`.
- [ ] Decide nested vs flat response shape deliberately — nesting related objects is
      "free" when the model already eager-loads them, but increases response size
      and query depth. Fine at MVP scale; revisit with a lighter list-view schema
      only if it's ever actually slow.
- [ ] Money fields: `Decimal`, with `Field(ge=0, max_digits=..., decimal_places=...)`.

## Phase 5 — Dependencies (DI providers)

- [ ] One `get_x_service(session: Annotated[AsyncSession, Depends(get_db)]) -> XService`
      function per service. Keep it a one-liner — no logic here.

## Phase 6 — Controller

- [ ] Route decorators use `dependencies=[Depends(require_permission("x.action"))]`
      when the route body doesn't need the `User` object itself.
- [ ] **Static path segments MUST be declared before dynamic `{id}` segments**
      (e.g. `/search`, `/by-medicine/{id}` before `/{id}`) — FastAPI matches routes
      in declaration order; a dynamic segment declared first will swallow the
      static path and try (and fail) to parse it as the dynamic type.
- [ ] try/except per route, each domain exception mapped to a specific status code
      (404 not found, 400 bad input/invalid FK, 409 conflict/in-use, 403 via the
      permission dependency itself — not hand-rolled in the route body).
- [ ] Append-only entities: simply don't define PATCH/DELETE routes. FastAPI
      returns 405 automatically for undefined methods on an existing path — verify
      this actually happens, don't just assume it.

## Phase 7 — Wiring

- [ ] Import the new model in `model_registry.py` (with `# noqa: F401`) — invisible
      to Alembic otherwise, no matter how correct the model file is.
- [ ] Register the new router in the main app file (`app.include_router(...)`).
- [ ] Add new permissions to `seed_rbac.py`'s `PERMISSIONS` list, and map them into
      the appropriate roles in `ROLES`.
- [ ] **Re-run the seed script after editing it.** Editing the file does nothing
      to the DB by itself — this exact mistake cost real debugging time twice in
      this project. Treat editing `seed_rbac.py` like writing (not yet applying)
      a migration.

## Phase 8 — Migration

- [ ] `alembic revision --autogenerate -m "..."`
- [ ] Review against three checks before touching `alembic upgrade`:
  1. **Scoped correctly?** Delete any unrelated `platform.*` FK drop/recreate noise
     that autogenerate sometimes hallucinates from reflection differences on
     already-correct tables — this reappears on nearly every migration in this
     project; recognize it and remove it every time.
  2. **Explicit, single-prefixed constraint names?** Check PK/FK/CK names via `op.f(...)`.
  3. **`schema=` present on every `create_table` call for this app's tables?** If
     missing, the model's `__table_args__` almost certainly has the Phase-1 bug
     (schema dict overwritten rather than combined).
- [ ] `CREATE SCHEMA` only needed the very first time a new schema is introduced —
      subsequent migrations for tables in an existing schema don't need it.
- [ ] `downgrade()` ordering: child tables (those with FKs pointing INTO other new
      tables in this same migration) drop first, then their parents, then the
      schema itself last (only if this migration created the schema).
- [ ] Apply: `alembic upgrade head`.
- [ ] **Verify against the live DB directly — never trust the migration file or an
      API response alone:**
      ```sql
      docker exec -it backend_platform_db psql -U platform -d backend_platform
      \d hospital.<table_name>
      ```
      Confirm every column, PK, FK (with correct `ondelete`), and check constraint.

## Phase 9 — Manual API testing (HTTPie)

- [ ] Fresh login every testing session — stale tokens and forgotten re-seeds are
      the single most common false "bug" in this project's history. When
      something 403s unexpectedly, re-login before debugging anything else.
- [ ] Happy path: create → confirm nested relationships are fully populated, not
      bare IDs or `null`.
- [ ] Bad FK reference → confirm clean 400, not a raw DB error.
- [ ] If `RESTRICT` is used anywhere: attempt to delete a referenced parent →
      confirm clean 409, not 500. (If 500: check the service isn't touching an
      ORM attribute after the failed flush — Phase 3's `PendingRollbackError` trap.)
- [ ] If cross-service orchestration is involved: verify the linked ID persisted
      via direct `psql` query, separately from what the API response shows —
      confirms write vs. read-path bugs are distinguished, not conflated.
- [ ] Permission checks: one route as Admin (succeeds), same route as a role
      missing that permission (clean 403 naming the missing permission).
- [ ] Append-only entities: confirm PATCH/DELETE actually 405, don't just assume
      omission from the controller is enough.

---

## Recurring bug patterns to recognize on sight

| Symptom | Cause | Fix |
|---|---|---|
| `MissingGreenlet` on a create/read response | `flush()` doesn't populate eager-loaded relationships | Re-fetch via `get_by_id()` after flush |
| Correct DB write, but API response shows stale/null relationship | Session identity map returns the same cached Python object; relationship attribute wasn't told to reload | `session.refresh(obj, attribute_names=[...])` |
| 500 instead of expected 409 on a `RESTRICT` delete | Touched an ORM attribute (e.g. `.name`) inside the `except IntegrityError` block, after the flush already failed | Capture the value BEFORE the risky operation, not after |
| Migration silently missing `schema=` on `create_table` | `__table_args__` overwritten instead of combined with parent's schema dict | Last tuple element must be the schema dict |
| Permission denied despite DB showing correct role/permission link | Stale JWT issued before a role's permissions changed, OR `seed_rbac.py` was edited but never re-run | Fresh login; confirm seed script was actually re-run |
| 422 on a route that should exist | Static path segment declared AFTER a dynamic `{id}` segment | Reorder — static routes first |