import asyncio

from src.core.database import model_registry  # noqa: F401 — ensures all models are registered
from src.core.database.session import async_session_factory
from src.modules.permission.model import Permission
from src.modules.permission.repository import PermissionRepository
from src.modules.role.model import Role
from src.modules.role.repository import RoleRepository

# The fixed vocabulary of permissions this platform currently understands.
# Adding a new permission here should correspond to a real check
# somewhere in code — never seed a permission nothing enforces.
PERMISSIONS = [
    ("medicine.read", "View medicine records"),
    ("medicine.create", "Create new medicine records"),
    ("medicine.update", "Update existing medicine records"),
    ("medicine.delete", "Delete medicine records"),
    ("user.read", "View user accounts"),
    ("user.manage", "Create, update, deactivate user accounts"),
]

# Roles and which permissions each one grants.
ROLES = {
    "Admin": [name for name, _ in PERMISSIONS],  # Admin gets everything
    "Pharmacist": ["medicine.read", "medicine.create", "medicine.update"],
    "Viewer": ["medicine.read"],
}


async def main():
    async with async_session_factory() as session:
        permission_repo = PermissionRepository(session)
        role_repo = RoleRepository(session)

        permission_objects: dict[str, Permission] = {}

        for name, description in PERMISSIONS:
            existing = await permission_repo.get_by_name(name)
            if existing:
                permission_objects[name] = existing
                print(f"Permission already exists: {name}")
            else:
                created = await permission_repo.create(
                    Permission(name=name, description=description)
                )
                permission_objects[name] = created
                print(f"Created permission: {name}")

        await session.flush()  # ensure all permissions have real IDs before linking

        for role_name, permission_names in ROLES.items():
            existing_role = await role_repo.get_by_name(role_name)
            if existing_role:
                print(f"Role already exists: {role_name}")
                continue

            role = Role(name=role_name)
            role.permissions = [permission_objects[name] for name in permission_names]
            await role_repo.create(role)
            print(f"Created role: {role_name} with {len(permission_names)} permissions")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())