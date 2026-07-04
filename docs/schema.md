# schema placement for platform-level tables

## Why public is worth questioning

- It's Postgres's default schema for everything unqualified. Any tool, any raw query, any dev who forgets to schema-qualify a table name lands in public by default. As your platform grows more apps (hospital, restaurant, school...), public risks becoming a junk drawer for "stuff nobody assigned a schema to" rather than a deliberate namespace.

- Naming collisions become more likely over time. If public holds your platform's core tables and becomes the default fallback for careless migrations later, you're one Alembic autogenerate mistake away from a table landing somewhere it shouldn't.

- It doesn't communicate intent. A DBA or future collaborator looking at your schema list sees public, hospital, restaurant, school — public doesn't say "this is the platform's own identity/access-control data," it just says "default."

