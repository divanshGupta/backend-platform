# Feature: Role-Based Access Control — roles, permissions, and the relationships between

## User - Roles - Permission

## Layer - src/modules/role/ and src/modules/permission/

### Schema design

- RBAC principle: Permissions are the source of truth. Roles contain permissions. Users contain roles. That sentence actually specifies the exact shape of three tables and two join tables. Let's design them properly.

platform.roles
  id UUID PK
  name VARCHAR(50) UNIQUE   -- e.g. "Pharmacist", "Admin"
  description VARCHAR(255) NULL
  created_at, updated_at

platform.permissions
  id UUID PK
  name VARCHAR(100) UNIQUE  -- e.g. "medicine.read", "medicine.create"
  description VARCHAR(255) NULL
  created_at

platform.role_permissions   (pure join table, no surrogate id needed)
  role_id UUID FK -> roles.id
  permission_id UUID FK -> permissions.id
  PRIMARY KEY (role_id, permission_id)

platform.user_roles         (pure join table, no surrogate id needed)
  user_id UUID FK -> users.id
  role_id UUID FK -> roles.id
  PRIMARY KEY (user_id, role_id)

## Seed Script

- Concept: why a dedicated seed script, not manual INSERT via psql, and not creating roles/permissions through the API

- What a seed script is: A script (same category as test_create_user.py) that establishes the platform's fixed, known-in-advance data — permissions and roles that define what the system can do, as opposed to variable data like actual users that get created dynamically at runtime.

- Why not create permissions via an API endpoint? Permissions aren't something an end user or even most admins should be able to invent on the fly through a UI — they correspond 1:1 to actual capabilities your code checks for (medicine.read only means something because some route literally checks for that exact string). If permissions could be created ad-hoc via API, you'd risk permission strings existing in the DB that no code actually checks, or code checking for a string that was never seeded — a silent mismatch bug. Permissions belong in version-controlled code (the seed script), reviewed like any other code change, not created through a runtime UI.

- Why not manual psql INSERT statements? Not reproducible, not versioned, easy to typo, and every fresh deployment (a new client, a teammate's machine, CI) would need someone to remember to do it by hand. A seed script is just Python — reviewable in a PR, runnable identically anywhere.

- When you WOULD want an API/admin UI for this instead: if you were building a genuinely dynamic permissions system where non-technical admins invent new permission strings freely (rare, and usually a sign of a more complex plugin-style architecture) — not your situation. Your permissions are a fixed, known vocabulary tied directly to your code.

### Idempotency — a real production concern, not an afterthought
- The problem: if you run a seed script twice (which will happen — CI runs, redeploys, you forgetting you already ran it), a naive script does a second INSERT and either crashes on the unique constraint or, worse, silently creates duplicate rows if you didn't put unique constraints on name (we did, correctly, back in the model design — this is exactly why that mattered).

- The fix: the seed script must be safe to run any number of times — check-then-create, or "get or create," for every row.