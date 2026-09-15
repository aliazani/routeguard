from fastapi.testclient import TestClient

from routeguard.dependencies import get_chat_service
from routeguard.main import app


class FakeChatService:
    async def answer(self, message: str) -> str:
        return f"Test answer for: {message}"


def override_chat_service() -> FakeChatService:
    return FakeChatService()


def test_chat() -> None:
    app.dependency_overrides[get_chat_service] = override_chat_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={"message": "What is VRP?"},
            )

        assert response.status_code == 200
        assert response.json() == {"answer": "Test answer for: What is VRP?"}

    finally:
        app.dependency_overrides.clear()
