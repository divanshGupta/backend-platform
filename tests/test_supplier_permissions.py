from scripts.seed_rbac import ROLES

import pytest_asyncio

from tests.factories import SupplierFactory


@pytest_asyncio.fixture
def current_user_permissions():
    return ROLES["Viewer"]

async def test_create_supplier_forbidden_for_viewer(client):
    supplier = SupplierFactory.build()

    response = await client.post("/suppliers", json={
        "name": supplier.name,
        "contact_email": supplier.contact_email,
        "contact_phone": supplier.contact_phone,
    })

    assert response.status_code == 403