# Alembic

1. python -m alembic revision --autogenerate -m "add hospital.stocks table" - generating alembic migration
2. python -m alembic upgrade head - applying the migration into db

# Docker exec

1. docker exec -it backend_platform_db psql -U platform -d backend_platform - sql editor in vscode terminal
2. \d hospital.stocks - prints the stocks table

# SQL

1. SELECT name FROM platform.permissions ORDER BY name;

# Python

1. uv run python -m scripts.seed_rbac - running the scripts
2. uv run uvicorn src.main:app  --reload - starting the main app (server)