# Audit Logging

<Decisions>

## how does logging get triggered?

- Manual — each service explicitly calls something like audit_service.record(action="stock.adjust", entity_type="Stock", entity_id=stock.id, old_value=..., new_value=..., reason=...) at the point of mutation.

- Automatic — SQLAlchemy ORM event listeners (after_insert/after_update/after_delete) hook every mutation without anyone remembering to call anything.

- i am choosing manual over automatic - simple and easy to implement, logging will be human readable rather than low-level diff

## How does "current user" + "IP address" reach the service layer?

- Both live on the HTTP request, but the mutation happens in a service, several layers down — and worse, cross-service calls (Purchase creating a Stock row) mean the same actor needs to travel through a call that isn't the outermost one.

1. Thread explicitly 
-  Controller reads user and IP from the request and passes them as parameters into every mutating service call (and through any nested service calls).
- Explicit and obvious where data comes from.
- Clutters every method signature and requires discipline to pass those params everywhere.

2. Request-Scoped ContextVar 
- Middleware stores user and IP into a context variable once per request; services read them explicitly.
- no need to add extra parameters everywhere; common approach for request scoped data.
- it's implici, but practical because actor-IP apply almost everywhere.

- i am choosing ContextVar here because we will not have carry user/ip into deeper layers.
- middleware could store currect user and IP once, then deeper service functions could read them automatically. in this way we dont need to add user and ip to every service method.

### ContextVars - packages/audit/context.py

- ContextVars is a Python feature for storing data that should belong to the current request/task instead of being passed around everywhere. It’s mainly useful in async code and web apps, where many requests run at the same time and we don’t want one request’s data to leak into another.

- Before contextvars, people often used global variables or thread-local storage for this kind of data. That works poorly in async programs, because one thread may run many tasks, and values can get mixed up if they aren’t tied to the right execution context.

- Contextvars + async, one thing worth understanding, not just trusting: FastAPI runs each request's dependencies and route handler in the same asyncio task, and contextvars are task-scoped — so a value set in middleware is visible everywhere downstream in that same request, including nested service calls. This breaks down the moment you introduce BackgroundTasks or anything that spawns a genuinely separate task, since contextvars don't automatically propagate there. You're not using background tasks yet, but if you ever do, this is the thing that'll bite you with a silently-None actor.

## What shape should old_value/new_value be in the audit?

1. Full snapshot 
- Store the entire row before and after as JSON.
- Simple to implement and always contains all data.
- Stores unchanged fields redundantly, larger payloads.

2. field-level diff
- Store only the columns that actually changed (old/new for each).
- Smaller, clearer about what changed.
- Requires careful diff logic and correct timing to capture true “before” values.

- i am choosing snapshot, its simpler and safer; diff is clearer but trickier.


# ------------------------------Audit Logging — Feature Documentation --------------------------------------------------------

_Package: `packages/audit` · Status: mechanism complete, piloted on Stock adjustments_

## What this is

A reusable, business-agnostic audit trail package that records who changed what,
when, from where, and what the before/after state was — for any mutation in any
future app built on this platform (Hospital today; Restaurant/Pharmacy/etc. later).
Lives in `packages/`, not `apps/hospital/`, because it must never know what a
"Stock" or "Medicine" is — it only knows about generic `entity_type` / `entity_id`
strings and JSON-serializable before/after snapshots.

## Why it exists

`moducore.md` lists Audit Trails as a core platform feature: every mutation should
record User, Time, IP, Action, Entity, Old Value, New Value. Stock adjustments
already had a `reason` field that was only going to Python's `logging` module —
this package is what finally persists that (and everything like it) to the database.

## Architecture decisions (and why, not just what)

Three real design choices were made here, each with a rejected alternative:

| Decision | Chosen | Rejected alternative | Why |
|---|---|---|---|
| **Trigger mechanism** | Manual — explicit `audit_service.record(...)` calls in services | SQLAlchemy ORM event listeners (`after_insert`/`after_update`) | Automatic hooks can't easily see "current user," and they log at the row level, not the business-action level. An explicit call lets `new_value` carry a semantic `reason` string that raw ORM diffing never could. |
| **Actor/IP propagation** | `contextvars.ContextVar`, set once in middleware + `get_current_user`, read implicitly by `AuditService` | Explicit `actor_id`/`ip_address` params threaded through every service method | Actor/IP apply to *every* mutation everywhere — threading two params through every method (including nested cross-service calls, like Purchase→Stock) would add friction to every future feature. Contextvars are task-scoped in asyncio, so this is safe under normal request/response handling — but doesn't survive into a genuinely separate task (e.g. `BackgroundTasks`), which isn't in use yet but is worth remembering if it ever is. |
| **Old/new value shape** | Full row snapshot (JSONB) | Field-level diff (only changed columns) | Full snapshot is a simple, uniform serialization with no diffing logic to get wrong. Diffing is a clean future improvement once the mechanism itself is proven — not worth a new timing-sensitive bug class on day one. |

## Schema — `platform.audit_logs`

```
id              bigint, auto-increment PK   -- NOT uuid, deliberately: nothing
                                              -- FKs to this table, and an
                                              -- auto-increment gives free
                                              -- chronological ordering
actor_user_id   uuid, nullable, FK -> platform.users.id ON DELETE SET NULL
action          varchar(100)                 -- e.g. "stock.adjust"
entity_type     varchar(100)                 -- e.g. "Stock" — plain string,
                                              -- no real FK to the entity table
                                              -- (a generic package can't FK to
                                              -- five different domain tables)
entity_id       varchar(100)                 -- stringified, since entity PKs
                                              -- vary in type across the system
old_value       jsonb, nullable               -- null for creates
new_value       jsonb, nullable               -- null for deletes
ip_address      varchar(45), nullable         -- fits IPv6
created_at      timestamptz, default now()
```

Indexes: `(entity_type, entity_id)` composite — lets you query "full history of
this one Stock row" — and `(created_at)` for chronological listing.

## Files

```
src/packages/audit/
    models.py        AuditLog SQLAlchemy model
    context.py        contextvars: set_actor(), set_ip(), get_actor_user_id(), get_ip_address()
    utils.py           serialize_model() — full-row JSON-safe snapshot of any SQLAlchemy instance
    repository.py      AuditRepository.create() — flush() only, rides the caller's transaction
    service.py         AuditService.record() — pulls actor/IP from context, writes via repository
    dependencies.py    get_audit_service() — same get_db session as the calling service

src/core/middleware/
    audit_context.py   AuditContextMiddleware — sets IP on every incoming request
```

## How it's wired in right now

1. `AuditContextMiddleware` sets the request's IP address as soon as it arrives.
2. `get_current_user` sets the actor's user ID once the JWT is decoded and the
   user is confirmed valid — **after** the None/is_active check, not before
   (an early version of this had `set_actor(user.id)` run before that check,
   which would `AttributeError` on `None` for a deleted-but-still-tokened user).
3. `StockService.adjust_stock()` is the one pilot integration: captures a full
   snapshot of the Stock row before mutating quantity, applies the delta,
   captures another snapshot after, and calls `audit_service.record(...)` — all
   inside the same `AsyncSession` as the Stock update itself, so the audit
   write and the business mutation commit or roll back together.

## `serialize_model()` — the one gotcha worth knowing

Postgres JSONB binding uses the stdlib `json` encoder under the hood, which only
understands JSON's native types. Any SQLAlchemy column type that maps to
something else needs an explicit conversion branch in `serialize_model()`.
Currently handled: `datetime`/`date` → ISO string, `Decimal` → string (never
`float`, same reasoning as everywhere else money is handled in this project),
`uuid.UUID` → string. **The next new column type this project introduces that
isn't a plain `str`/`int`/`bool`/`float` (e.g. an `Enum` column) will need a new
branch added here** — this bit us once already with UUID during the Stock pilot.

## Known, accepted limitations (not bugs — deliberate trade-offs)

- No real foreign key from `entity_type`/`entity_id` to actual domain tables —
  traded referential integrity for keeping the package generic across future apps.
- Contextvars don't propagate into genuinely separate asyncio tasks
  (`BackgroundTasks`, worker processes) — not an issue today since nothing uses
  those, but worth remembering if that changes.
- Only Stock adjustments are audited right now. Medicine, Purchase, Category,
  and Supplier mutations are **not yet instrumented** — see
  `audit-logging-extension-guide.md` for the exact steps to add them.