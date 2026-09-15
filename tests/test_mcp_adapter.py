import pytest

from routeguard.agent.mcp_client import get_mcp_tools


@pytest.mark.anyio
async def test_langchain_discovers_mcp_tools() -> None:
    async with get_mcp_tools() as tools:
        tool_names = {tool.name for tool in tools}

    assert tool_names == {
        "routing_get_tour",
        "routing_get_shipment",
        "routing_simulate_move",
        "knowledge_search_policy_documents",
    }
