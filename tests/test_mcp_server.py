import pytest
from mcp import Client

from routeguard.mcp.server import mcp


@pytest.mark.anyio
async def test_mcp_exposes_expected_tools() -> None:
    async with Client(mcp) as client:
        result = await client.list_tools()

    tool_names = {tool.name for tool in result.tools}

    assert tool_names == {
        "get_tour",
        "get_shipment",
        "simulate_move",
    }


@pytest.mark.anyio
async def test_get_tour_mcp_tool() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_tour",
            {"tour_id": 12},
        )

    assert result.structured_content is not None
    assert result.structured_content["tour_id"] == 12
    assert result.structured_content["vehicle_capacity"] == 100


@pytest.mark.anyio
async def test_get_shipment_mcp_tool() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_shipment",
            {"shipment_id": "S102"},
        )

    assert result.structured_content is not None
    assert result.structured_content["shipment_id"] == "S102"
    assert result.structured_content["capacity"] == 25


@pytest.mark.anyio
async def test_simulate_move_mcp_tool() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "simulate_move",
            {
                "shipment_id": "S102",
                "source_tour_id": 12,
                "target_tour_id": 15,
            },
        )

    assert result.structured_content is not None
    assert result.structured_content["feasible"] is True
    assert result.structured_content["capacity_violation"] is False
    assert result.structured_content["time_window_violation"] is False
