from fastapi.testclient import (
    TestClient,
)

from routeguard.api.agent import (
    get_agent_chat_service,
)
from routeguard.main import app


class FakeAgentChatService:
    async def reply(
        self,
        message: str,
    ) -> str:
        assert message == ("Can I move S102 from Tour 12 to Tour 15?")

        return "The move is feasible, but it has not been executed."


def override_agent_service() -> FakeAgentChatService:
    return FakeAgentChatService()


def test_agent_chat() -> None:
    app.dependency_overrides[get_agent_chat_service] = override_agent_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/agent/chat",
                json={"message": ("Can I move S102 from Tour 12 to Tour 15?")},
            )

        assert response.status_code == 200

        assert response.json() == {
            "answer": ("The move is feasible, but it has not been executed.")
        }

    finally:
        app.dependency_overrides.clear()
