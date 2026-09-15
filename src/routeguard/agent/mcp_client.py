import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langchain.mcp import MCPAdapter
from langchain_core.tools import BaseTool

from routeguard.agent.guardrails import validate_tools


def get_mcp_config() -> dict:
    return {
        "mcpServers": {
            "routing": {
                "command": sys.executable,
                "args": [
                    "-m",
                    "routeguard.mcp.server",
                ],
            },
            "knowledge": {
                "command": sys.executable,
                "args": [
                    "-m",
                    "routeguard.mcp.knowledge_server",
                ],
            },
        }
    }


@asynccontextmanager
async def get_mcp_tools() -> AsyncGenerator[list[BaseTool], None]:
    async with MCPAdapter(get_mcp_config()) as adapter:
        tools = await adapter.list_tools()

        validated_tools = validate_tools(tools)

        yield validated_tools
