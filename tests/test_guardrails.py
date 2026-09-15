import pytest
from langchain_core.tools import tool

from routeguard.agent.guardrails import (
    UnsafeToolError,
    validate_tools,
)


@tool("routing_get_tour")
def get_tour(tour_id: int) -> str:
    """Get a tour."""
    return str(tour_id)


@tool("routing_delete_tour")
def delete_tour(tour_id: int) -> str:
    """Delete a tour."""
    return str(tour_id)


def test_safe_tools_are_allowed() -> None:
    tools = validate_tools([get_tour])

    assert tools == [get_tour]


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(
        UnsafeToolError,
        match="routing_delete_tour",
    ):
        validate_tools(
            [
                get_tour,
                delete_tour,
            ]
        )
