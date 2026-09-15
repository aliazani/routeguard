from langchain_core.messages import HumanMessage

from routeguard.agent.evaluation import (
    extract_final_answer,
)
from routeguard.agent.graph import (
    build_agent_graph,
)
from routeguard.agent.mcp_client import (
    get_mcp_tools,
)
from routeguard.ai.model import (
    create_chat_model,
)
from routeguard.config import get_settings


class AgentChatService:
    async def reply(
        self,
        message: str,
    ) -> str:
        message = message.strip()

        if not message:
            raise ValueError("message cannot be empty")

        settings = get_settings()

        model = create_chat_model(settings)

        async with get_mcp_tools() as tools:
            graph = build_agent_graph(
                model,
                tools,
            )

            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config={
                    "tags": [
                        "api",
                        "agent-chat",
                    ],
                    "metadata": {
                        "source": "fastapi",
                    },
                },
            )

        answer = extract_final_answer(result["messages"])

        if not answer.strip():
            raise RuntimeError("Agent returned no final answer.")

        return answer
