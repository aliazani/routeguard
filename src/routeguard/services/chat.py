from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

SYSTEM_PROMPT = """
You are RouteGuard, an assistant for route-planning operations.

For now, you only answer general questions about route planning.

You do not modify routes or claim to have access to operational data.
Keep answers concise and factual.
""".strip()


class ChatService:
    def __init__(self, model: BaseChatModel) -> None:
        self.model = model

    async def answer(self, message: str) -> str:
        response = await self.model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=message),
            ]
        )

        if not isinstance(response.content, str):
            raise RuntimeError("Unexpected model response format")

        return response.content
