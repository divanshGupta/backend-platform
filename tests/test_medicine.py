import pytest_asyncio

from tests.factories import CategoryFactory, SupplierFactory


@pytest_asyncio.fixture
async def category_and_supplier(db_session):
    category = CategoryFactory.build()
    supplier = SupplierFactory.build()

    db_session.add(category)
    db_session.add(supplier)
    await db_session.commit()

    return category, supplier


async def test_create_medicine(client, category_and_supplier):
    category, supplier = category_and_supplier

    response = await client.post("/medicines", json={
        "name": "Paracetamol 500mg",
        "category_id": str(category.id),
        "supplier_id": str(supplier.id),
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Paracetamol 500mg"