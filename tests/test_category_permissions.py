from scripts.seed_rbac import ROLES

import pytest_asyncio

from tests.factories import CategoryFactory

@pytest_asyncio.fixture
def current_user_permissions():
    return ROLES["Viewer"]

async def test_create_category_forbidden_for_viewer(client):
    category = CategoryFactory.build()

    response = await client.post("/categories", json={
        "name": category.name,
        "description": category.description,
    })

    assert response.status_code == 403