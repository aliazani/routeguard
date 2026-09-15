from typing import Any

import pytest
from langgraph.types import Command

from routeguard.agent.route_change_workflow import (
    build_route_change_workflow,
)
from routeguard.repositories.route_repository import (
    InMemoryRouteRepository,
    VersionConflictError,
)


def valid_request() -> dict[str, Any]:
    return {
        "shipment_id": "S102",
        "source_tour_id": 12,
        "target_tour_id": 15,
        "operator": "demo-user",
        "idempotency_key": "workflow-move-001",
        "status": "pending",
    }


@pytest.mark.anyio
async def test_feasible_move_pauses_for_approval() -> None:
    repository = InMemoryRouteRepository()

    graph = build_route_change_workflow(repository)

    config = {
        "configurable": {
            "thread_id": "workflow-approval-1",
        }
    }

    result = await graph.ainvoke(
        valid_request(),
        config=config,
    )

    assert "__interrupt__" in result

    interrupt_data = result["__interrupt__"][0].value

    assert interrupt_data["type"] == "route_change_approval"

    assert interrupt_data["shipment_id"] == "S102"

    assert interrupt_data["source_tour_id"] == 12

    assert interrupt_data["target_tour_id"] == 15

    assert interrupt_data["source_tour_version"] == 3

    assert interrupt_data["target_tour_version"] == 4

    assert interrupt_data["projected_load"] == 60

    assert interrupt_data["vehicle_capacity"] == 70


@pytest.mark.anyio
async def test_approved_move_is_applied() -> None:
    repository = InMemoryRouteRepository()

    graph = build_route_change_workflow(repository)

    config = {
        "configurable": {
            "thread_id": "workflow-approval-2",
        }
    }

    await graph.ainvoke(
        valid_request(),
        config=config,
    )

    result = await graph.ainvoke(
        Command(
            resume=True,
        ),
        config=config,
    )

    assert result["status"] == "applied"

    assert result["source_version_after"] == 4

    assert result["target_version_after"] == 5

    assert result["audit_id"] is not None

    source = repository.get_tour(12)
    target = repository.get_tour(15)

    assert all(stop.shipment_id != "S102" for stop in source.stops)

    assert any(stop.shipment_id == "S102" for stop in target.stops)

    assert len(repository.list_audit_events()) == 1


@pytest.mark.anyio
async def test_rejected_move_is_not_applied() -> None:
    repository = InMemoryRouteRepository()

    graph = build_route_change_workflow(repository)

    config = {
        "configurable": {
            "thread_id": "workflow-rejection-1",
        }
    }

    await graph.ainvoke(
        valid_request(),
        config=config,
    )

    result = await graph.ainvoke(
        Command(
            resume=False,
        ),
        config=config,
    )

    assert result["status"] == "rejected"

    source = repository.get_tour(12)
    target = repository.get_tour(15)

    assert source.version == 3
    assert target.version == 4

    assert any(stop.shipment_id == "S102" for stop in source.stops)

    assert all(stop.shipment_id != "S102" for stop in target.stops)

    assert repository.list_audit_events() == []


@pytest.mark.anyio
async def test_infeasible_move_does_not_request_approval() -> None:
    repository = InMemoryRouteRepository()

    graph = build_route_change_workflow(repository)

    config = {
        "configurable": {
            "thread_id": "workflow-infeasible-1",
        }
    }

    request = {
        "shipment_id": "S300",
        "source_tour_id": 12,
        "target_tour_id": 15,
        "operator": "demo-user",
        "idempotency_key": ("workflow-infeasible-001"),
        "status": "pending",
    }

    result = await graph.ainvoke(
        request,
        config=config,
    )

    assert "__interrupt__" not in result

    assert result["status"] == "infeasible"

    assert result["feasible"] is False

    assert result["reason"] is not None

    assert repository.list_audit_events() == []


@pytest.mark.anyio
async def test_stale_version_prevents_mutation_after_approval() -> None:
    repository = InMemoryRouteRepository()

    graph = build_route_change_workflow(repository)

    config = {
        "configurable": {
            "thread_id": "workflow-stale-1",
        }
    }

    await graph.ainvoke(
        valid_request(),
        config=config,
    )

    # Simulate another process changing
    # Tour 15 while approval is pending.
    target = repository.get_tour(15)
    target.version += 1

    assert target.version == 5

    with pytest.raises(VersionConflictError):
        await graph.ainvoke(
            Command(
                resume=True,
            ),
            config=config,
        )

    # No route change was executed.
    source = repository.get_tour(12)
    target = repository.get_tour(15)

    assert any(stop.shipment_id == "S102" for stop in source.stops)

    assert all(stop.shipment_id != "S102" for stop in target.stops)

    assert repository.list_audit_events() == []
