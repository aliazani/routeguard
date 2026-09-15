import asyncio

from langchain_core.messages import HumanMessage

from routeguard.agent.graph import build_agent_graph
from routeguard.agent.mcp_client import get_mcp_tools
from routeguard.ai.model import create_chat_model
from routeguard.config import get_settings


async def main() -> None:
    settings = get_settings()
    model = create_chat_model(settings)

    async with get_mcp_tools() as tools:
        graph = build_agent_graph(
            model=model,
            tools=tools,
        )

        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content=("Can I move shipment S102 from Tour 12 to Tour 15?"))
                ]
            }
        )

        print("\n--- Agent execution ---\n")

        for message in result["messages"]:
            print(f"{type(message).__name__}: {message.content}")

            if getattr(message, "tool_calls", None):
                print(
                    "Tool calls:",
                    message.tool_calls,
                )


if __name__ == "__main__":
    asyncio.run(main())
