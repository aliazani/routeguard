from fastapi.testclient import TestClient

from routeguard.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_returns_request_id() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]


def test_request_id_is_propagated() -> None:
    request_id = "test-request-123"

    response = client.get(
        "/api/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.headers["x-request-id"] == request_id
