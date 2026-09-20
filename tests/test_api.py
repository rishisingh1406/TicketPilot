from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_ticket():
    response = client.post(
        "/tickets",
        json={
            "user_id": 123,
            "message": "I was charged extra",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticket_id"]
    assert data["status"] == "CREATED"
    assert data["message"] == "Ticket created successfully"


def test_create_ticket_rejects_empty_message():
    response = client.post(
        "/tickets",
        json={
            "user_id": 123,
            "message": "",
        },
    )

    assert response.status_code == 422


def test_get_tickets():
    response = client.get("/tickets")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


def test_ticket_decision():
    response = client.post(
        "/tickets/1/decision",
        json={
            "decision": "RESOLVED",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticket_id"] == "1"
    assert data["status"] == "RESOLVED"
    assert data["message"] == "Ticket decision updated successfully"