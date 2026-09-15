from datetime import time
from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from routeguard.repositories.route_repository import (
    RouteRepository,
)
from routeguard.services.route_change import (
    RouteChangeService,
)
from routeguard.services.route_simulation import (
    RouteSimulationService,
)


class RouteChangeWorkflowState(BaseModel):
    shipment_id: str
    source_tour_id: int
    target_tour_id: int

    operator: str
    idempotency_key: str

    feasible: bool | None = None

    source_tour_version: int | None = None
    target_tour_version: int | None = None

    projected_load: int | None = None
    vehicle_capacity: int | None = None

    projected_arrival: time | None = None
    projected_service_start: time | None = None

    extra_distance_km: float | None = None
    extra_duration_minutes: int | None = None

    reason: str | None = None

    approved: bool | None = None

    status: Literal[
        "pending",
        "awaiting_approval",
        "rejected",
        "infeasible",
        "applied",
    ] = "pending"

    audit_id: str | None = None

    source_version_after: int | None = None
    target_version_after: int | None = None


def build_route_change_workflow(
    repository: RouteRepository,
):
    simulation_service = RouteSimulationService(repository)

    route_change_service = RouteChangeService(repository)

    def simulate_node(
        state: RouteChangeWorkflowState,
    ) -> dict[str, object]:
        simulation = simulation_service.simulate_move(
            shipment_id=state.shipment_id,
            source_tour_id=state.source_tour_id,
            target_tour_id=state.target_tour_id,
        )

        return {
            "feasible": simulation.feasible,
            "source_tour_version": (simulation.source_tour_version),
            "target_tour_version": (simulation.target_tour_version),
            "projected_load": (simulation.projected_load),
            "vehicle_capacity": (simulation.vehicle_capacity),
            "projected_arrival": (simulation.projected_arrival),
            "projected_service_start": (simulation.projected_service_start),
            "extra_distance_km": (simulation.extra_distance_km),
            "extra_duration_minutes": (simulation.extra_duration_minutes),
            "reason": simulation.reason,
            "status": ("awaiting_approval" if simulation.feasible else "infeasible"),
        }

    def route_after_simulation(
        state: RouteChangeWorkflowState,
    ) -> Literal[
        "approval",
        "infeasible",
    ]:
        if state.feasible is True:
            return "approval"

        return "infeasible"

    def approval_node(
        state: RouteChangeWorkflowState,
    ) -> dict[str, bool]:
        decision = interrupt(
            {
                "type": "route_change_approval",
                "question": ("Do you approve this route change?"),
                "shipment_id": state.shipment_id,
                "source_tour_id": (state.source_tour_id),
                "target_tour_id": (state.target_tour_id),
                "source_tour_version": (state.source_tour_version),
                "target_tour_version": (state.target_tour_version),
                "projected_load": (state.projected_load),
                "vehicle_capacity": (state.vehicle_capacity),
                "projected_arrival": (state.projected_arrival),
                "projected_service_start": (state.projected_service_start),
                "extra_distance_km": (state.extra_distance_km),
                "extra_duration_minutes": (state.extra_duration_minutes),
            }
        )

        return {
            "approved": decision is True,
        }

    def route_after_approval(
        state: RouteChangeWorkflowState,
    ) -> Literal[
        "apply",
        "rejected",
    ]:
        if state.approved is True:
            return "apply"

        return "rejected"

    def apply_node(
        state: RouteChangeWorkflowState,
    ) -> dict[str, object]:
        if state.source_tour_version is None:
            raise RuntimeError("Source tour version is missing.")

        if state.target_tour_version is None:
            raise RuntimeError("Target tour version is missing.")

        result = route_change_service.apply_move(
            shipment_id=state.shipment_id,
            source_tour_id=state.source_tour_id,
            target_tour_id=state.target_tour_id,
            expected_source_version=(state.source_tour_version),
            expected_target_version=(state.target_tour_version),
            operator=state.operator,
            idempotency_key=(state.idempotency_key),
        )

        return {
            "status": "applied",
            "audit_id": result.audit_id,
            "source_version_after": (result.source_version),
            "target_version_after": (result.target_version),
        }

    def rejected_node(
        state: RouteChangeWorkflowState,
    ) -> dict[str, str]:
        return {
            "status": "rejected",
        }

    def infeasible_node(
        state: RouteChangeWorkflowState,
    ) -> dict[str, str]:
        return {
            "status": "infeasible",
        }

    builder = StateGraph(RouteChangeWorkflowState)

    builder.add_node(
        "simulate",
        simulate_node,
    )

    builder.add_node(
        "approval",
        approval_node,
    )

    builder.add_node(
        "apply",
        apply_node,
    )

    builder.add_node(
        "rejected",
        rejected_node,
    )

    builder.add_node(
        "infeasible",
        infeasible_node,
    )

    builder.add_edge(
        START,
        "simulate",
    )

    builder.add_conditional_edges(
        "simulate",
        route_after_simulation,
        {
            "approval": "approval",
            "infeasible": "infeasible",
        },
    )

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "apply": "apply",
            "rejected": "rejected",
        },
    )

    builder.add_edge(
        "apply",
        END,
    )

    builder.add_edge(
        "rejected",
        END,
    )

    builder.add_edge(
        "infeasible",
        END,
    )

    checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
