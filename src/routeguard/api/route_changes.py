from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field

from routeguard.agent.route_change_workflow import (
    build_route_change_workflow,
)
from routeguard.repositories.route_repository import (
    RouteRepository,
    VersionConflictError,
)
from routeguard.services.route_change import (
    IdempotencyConflictError,
    InfeasibleMoveError,
)


class StartRouteChangeRequest(BaseModel):
    shipment_id: str
    source_tour_id: int
    target_tour_id: int

    operator: str = Field(min_length=1)

    idempotency_key: str | None = None


def create_route_change_router(
    repository: RouteRepository,
) -> APIRouter:
    router = APIRouter(
        prefix="/route-changes",
        tags=["route-changes"],
    )

    graph = build_route_change_workflow(repository)

    # Demo/application-process registry.
    # LangGraph still owns the actual checkpoint.
    pending_threads: set[str] = set()

    def config_for(
        thread_id: str,
    ) -> dict[str, Any]:
        return {
            "configurable": {
                "thread_id": thread_id,
            }
        }

    @router.post("")
    async def start_route_change(
        request: StartRouteChangeRequest,
    ) -> dict[str, Any]:
        thread_id = str(uuid4())

        idempotency_key = request.idempotency_key or f"route-change:{thread_id}"

        result = await graph.ainvoke(
            {
                "shipment_id": (request.shipment_id),
                "source_tour_id": (request.source_tour_id),
                "target_tour_id": (request.target_tour_id),
                "operator": (request.operator),
                "idempotency_key": (idempotency_key),
                "status": "pending",
            },
            config=config_for(thread_id),
        )

        interrupts = result.get("__interrupt__")

        if interrupts:
            pending_threads.add(thread_id)

            approval = interrupts[0].value

            return {
                "status": ("approval_required"),
                "thread_id": thread_id,
                "idempotency_key": (idempotency_key),
                "approval": approval,
            }

        return {
            "status": result.get("status"),
            "thread_id": thread_id,
            "feasible": result.get("feasible"),
            "reason": result.get("reason"),
        }

    @router.post("/{thread_id}/confirm")
    async def confirm_route_change(
        thread_id: str,
    ) -> dict[str, Any]:
        if thread_id not in pending_threads:
            raise HTTPException(
                status_code=404,
                detail=("No pending route change was found for this thread."),
            )

        try:
            result = await graph.ainvoke(
                Command(resume=True),
                config=config_for(thread_id),
            )

        except VersionConflictError as exc:
            pending_threads.discard(thread_id)

            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        except IdempotencyConflictError as exc:
            pending_threads.discard(thread_id)

            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        except InfeasibleMoveError as exc:
            pending_threads.discard(thread_id)

            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        pending_threads.discard(thread_id)

        return {
            "status": result.get("status"),
            "thread_id": thread_id,
            "shipment_id": result.get("shipment_id"),
            "source_tour_id": result.get("source_tour_id"),
            "target_tour_id": result.get("target_tour_id"),
            "source_version_after": (result.get("source_version_after")),
            "target_version_after": (result.get("target_version_after")),
            "audit_id": result.get("audit_id"),
        }

    @router.post("/{thread_id}/reject")
    async def reject_route_change(
        thread_id: str,
    ) -> dict[str, Any]:
        if thread_id not in pending_threads:
            raise HTTPException(
                status_code=404,
                detail=("No pending route change was found for this thread."),
            )

        result = await graph.ainvoke(
            Command(resume=False),
            config=config_for(thread_id),
        )

        pending_threads.discard(thread_id)

        return {
            "status": result.get("status"),
            "thread_id": thread_id,
        }

    return router
