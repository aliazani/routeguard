from typing import Any

import pytest
from langgraph.types import Command

from routeguard.agent.approval import (
    build_approval_graph,
)


def create_initial_state() -> dict[str, Any]:
    return {
        "shipment_id": "S102",
        "source_tour_id": 12,
        "target_tour_id": 15,
        "source_version": 3,
        "target_version": 4,
        "feasible": True,
        "status": "pending",
    }


@pytest.mark.anyio
async def test_approval_flow_pauses() -> None:
    graph = build_approval_graph()

    config = {
        "configurable": {
            "thread_id": "approval-test-1",
        }
    }

    result = await graph.ainvoke(
        create_initial_state(),
        config=config,
    )

    assert "__interrupt__" in result

    interrupts = result["__interrupt__"]

    assert len(interrupts) == 1

    payload = interrupts[0].value

    assert payload["type"] == "route_change_approval"

    assert payload["shipment_id"] == "S102"

    assert payload["source_tour_id"] == 12

    assert payload["target_tour_id"] == 15

    assert payload["source_version"] == 3

    assert payload["target_version"] == 4


@pytest.mark.anyio
async def test_approval_can_be_accepted() -> None:
    graph = build_approval_graph()

    config = {
        "configurable": {
            "thread_id": "approval-test-2",
        }
    }

    await graph.ainvoke(
        create_initial_state(),
        config=config,
    )

    result = await graph.ainvoke(
        Command(
            resume=True,
        ),
        config=config,
    )

    assert result["status"] == "approved"

    assert result["approved"] is True


@pytest.mark.anyio
async def test_approval_can_be_rejected() -> None:
    graph = build_approval_graph()

    config = {
        "configurable": {
            "thread_id": "approval-test-3",
        }
    }

    await graph.ainvoke(
        create_initial_state(),
        config=config,
    )

    result = await graph.ainvoke(
        Command(
            resume=False,
        ),
        config=config,
    )

    assert result["status"] == "rejected"

    assert result["approved"] is False
