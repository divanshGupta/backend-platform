import uuid
from scripts.seed_rbac import PERMISSIONS

ALL_PERMISSION_NAMES = [name for name, _ in PERMISSIONS]


class FakePermission:
    def __init__(self, name: str):
        self.name = name


class FakeRole:
    def __init__(self, permission_names: list[str]):
        self.permissions = [FakePermission(name) for name in permission_names]


class FakeUser:
    def __init__(self, permission_names: list[str] = ALL_PERMISSION_NAMES):
        self.id = uuid.uuid4()
        self.is_active = True
        self.roles = [FakeRole(permission_names)]