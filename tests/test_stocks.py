import uuid


async def test_create_stock(client, medicine):
    response = await client.post("/stocks", json={
        "medicine_id": str(medicine.id),
        "batch_number": "BATCH-001",
        "quantity": 100,
        "expiry_date": "2027-01-01",
    })

    assert response.status_code == 201
    data = response.json()
    assert data["batch_number"] == "BATCH-001"
    assert data["quantity"] == 100


async def test_create_stock_invalid_medicine(client):
    response = await client.post("/stocks", json={
        "medicine_id": str(uuid.uuid4()),
        "batch_number": "BATCH-001",
        "quantity": 100,
        "expiry_date": "2027-01-01",
    })

    assert response.status_code == 400