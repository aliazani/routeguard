from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel


class ApprovalState(BaseModel):
    shipment_id: str
    source_tour_id: int
    target_tour_id: int

    source_version: int
    target_version: int

    feasible: bool

    approved: bool | None = None

    status: Literal[
        "pending",
        "approved",
        "rejected",
    ] = "pending"


def approval_node(
    state: ApprovalState,
) -> dict[str, bool]:
    decision = interrupt(
        {
            "type": "route_change_approval",
            "question": ("Do you approve this route change?"),
            "shipment_id": state.shipment_id,
            "source_tour_id": (state.source_tour_id),
            "target_tour_id": (state.target_tour_id),
            "source_version": (state.source_version),
            "target_version": (state.target_version),
            "feasible": state.feasible,
        }
    )

    return {
        "approved": decision is True,
    }


def route_after_approval(
    state: ApprovalState,
) -> Literal[
    "approved",
    "rejected",
]:
    if state.approved is True:
        return "approved"

    return "rejected"


def approved_node(
    state: ApprovalState,
) -> dict[str, str]:
    return {
        "status": "approved",
    }


def rejected_node(
    state: ApprovalState,
) -> dict[str, str]:
    return {
        "status": "rejected",
    }


def build_approval_graph():
    builder = StateGraph(ApprovalState)

    builder.add_node(
        "approval",
        approval_node,
    )

    builder.add_node(
        "approved",
        approved_node,
    )

    builder.add_node(
        "rejected",
        rejected_node,
    )

    builder.add_edge(
        START,
        "approval",
    )

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "approved": "approved",
            "rejected": "rejected",
        },
    )

    builder.add_edge(
        "approved",
        END,
    )

    builder.add_edge(
        "rejected",
        END,
    )

    checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
