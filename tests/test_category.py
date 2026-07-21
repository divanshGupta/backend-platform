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


async def test_create_duplicate_category(client, db_session):
    existing_category = CategoryFactory.build()

    db_session.add(existing_category)
    await db_session.commit()

    response = await client.post("/categories", json={
        "name": existing_category.name,
        "description": "some other description",
    })

    assert response.status_code == 409


async def test_create_category_missing_name(client):
    response = await client.post("/categories", json={
        "description": "some description",
    })

    assert response.status_code == 422


async def test_create_category_empty_name(client):
    response = await client.post("/categories", json={
        "name": "",
        "description": "some description",
    })

    assert response.status_code == 422


async def test_create_category_name_too_long(client):
    response = await client.post("/categories", json={
        "name": "a" * 101,
        "description": "some description",
    })

    assert response.status_code == 422


async def test_create_category_description_too_long(client):
    category = CategoryFactory.build()

    response = await client.post("/categories", json={
        "name": category.name,
        "description": "a" * 501,
    })

    assert response.status_code == 422