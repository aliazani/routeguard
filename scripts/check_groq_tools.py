import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from routeguard.agent.mcp_client import get_mcp_tools
from routeguard.ai.model import create_chat_model
from routeguard.config import get_settings

SYSTEM_PROMPT = """
You are RouteGuard, an operational route-planning assistant.

Use the available tools whenever operational information is required.

Rules:
- Never invent operational data.
- Never invent identifiers.
- Route changes must be simulated before being recommended.
- If required information is missing, ask the user instead of guessing.
- Never claim an operation was executed unless an available tool confirms it.
""".strip()


async def main() -> None:
    settings = get_settings()
    model = create_chat_model(settings)

    async with get_mcp_tools() as tools:
        print("Discovered tools:")

        for tool in tools:
            print(f"- {tool.name}")

        model_with_tools = model.bind_tools(tools)

        response = await model_with_tools.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=("Can I move shipment S102 from Tour 12 to Tour 15?")),
            ]
        )

        print("\nModel response:")
        print(response.content)

        print("\nRequested tool calls:")

        for call in response.tool_calls:
            print(f"{call['name']}({call['args']})")


if __name__ == "__main__":
    asyncio.run(main())
