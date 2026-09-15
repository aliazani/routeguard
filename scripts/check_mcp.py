import asyncio
import sys

from langchain.mcp import MCPAdapter


async def main() -> None:
    config = {
        "mcpServers": {
            "routing": {
                "command": sys.executable,
                "args": [
                    "-m",
                    "routeguard.mcp.server",
                ],
            }
        }
    }

    async with MCPAdapter(config) as adapter:
        tools = await adapter.list_tools()

        print("Discovered MCP tools:")

        for tool in tools:
            print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
