from tests.factories import SupplierFactory


async def test_create_supplier(client):
    supplier = SupplierFactory.build()

    response = await client.post("/suppliers", json={
        "name": supplier.name,
        "contact_email": supplier.contact_email,
        "contact_phone": supplier.contact_phone,
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == supplier.name


async def test_create_supplier_missing_name(client):
    response = await client.post("/suppliers", json={
        "contact_email": "test@example.com",
    })

    assert response.status_code == 422


async def test_create_supplier_empty_name(client):
    response = await client.post("/suppliers", json={
        "name": "",
        "contact_email": "test@example.com",
    })

    assert response.status_code == 422


async def test_create_supplier_name_too_long(client):
    response = await client.post("/suppliers", json={
        "name": "a" * 151,
        "contact_email": "test@example.com",
    })

    assert response.status_code == 422