from tests.factories import CategoryFactory


async def test_create_category(client):
    category = CategoryFactory.build()

    response = await client.post("/categories", json={
        "name": category.name,
        "description": category.description,
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == category.name