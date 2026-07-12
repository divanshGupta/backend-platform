- Look at the revision header: Revision ID: fb8f1aa272f4, Revises: None. This is the empty "init" migration we created at the very start of Alembic setup — the one meant to just prove the connection worked, with pass/pass bodies. You didn't create a new migration for the schema; you edited that already-applied one.

- Here's why that breaks silently: Alembic doesn't diff file contents. It tracks progress purely by revision ID in the alembic_version table. When you first ran alembic upgrade head (back when we verified the connection), Postgres recorded fb8f1aa272f4 as "already applied." Then you edited that same file's upgrade() body afterward — but Alembic has no mechanism to notice "the code behind an already-applied revision changed." When you ran alembic upgrade head again, Alembic checked the version table, saw fb8f1aa272f4 was already the current head, concluded there was nothing to do, and exited "successfully" — successfully doing nothing.
This is the exact reason alembic upgrade head reported success but \dn still shows only public.

- The rule this teaches you
Never edit an already-applied migration. Not because it's forbidden syntactically — Alembic will happily let you — but because migration history is supposed to be an immutable, ordered log of what happened to the database, the same way git commits are immutable. Once a migration has run (even just on your own local DB), the correct move is always to write a new migration for the next change, never rewrite history. This matters enormously more once you have a team or a deployed environment — a migration edited after teammates already ran it means their DB and yours silently diverge with no error, ever.
Right now, locally, solo, nothing deployed — the blast radius is small, so we can safely undo and redo. But build the habit now.

# three-point review before midration upgrade head:
- schema="platform" present on the table and both indexes — check it didn't get dropped like the earlier CheckConstraint bug taught you to watch for.

- Trim any unrelated hospital.* autogenerate noise, same as every migration so far.

- Confirm the FK constraint name Alembic generates is sane (not an auto-generated None-suffixed name) — worth an explicit name="fk_audit_logs_actor_user_id_users" if your Alembic config doesn't already enforce a naming convention.