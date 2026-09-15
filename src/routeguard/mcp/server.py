from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from routeguard.repositories.factory import (
    create_route_repository,
)
from routeguard.repositories.route_repository import (
    ShipmentNotFoundError,
    TourNotFoundError,
)
from routeguard.services.route_simulation import (
    RouteSimulationService,
)

repository = create_route_repository()
simulation_service = RouteSimulationService(repository)


mcp = MCPServer(
    "routeguard-routing",
    instructions=(
        "Provides read-only route information and safe route-change "
        "simulation tools. These tools do not modify operational state."
    ),
)


@mcp.tool()
def get_tour(tour_id: int) -> dict[str, Any]:
    """Get the current operational state of a tour.

    Use this when you need information about a specific tour.
    """
    try:
        tour = repository.get_tour(tour_id)

    except TourNotFoundError as exc:
        raise ToolError(str(exc)) from exc

    return tour.model_dump(mode="json")


@mcp.tool()
def get_shipment(shipment_id: str) -> dict[str, Any]:
    """Get the current details of a shipment.

    Use this when you need information about a specific shipment.
    """
    try:
        shipment = repository.get_shipment(shipment_id)

    except ShipmentNotFoundError as exc:
        raise ToolError(str(exc)) from exc

    return shipment.model_dump(mode="json")


@mcp.tool()
def simulate_move(
    shipment_id: str,
    source_tour_id: int,
    target_tour_id: int,
) -> dict[str, Any]:
    """Simulate moving a shipment between two tours.

    This tool does not modify operational state.

    It deterministically checks route feasibility including
    capacity and delivery time-window constraints.
    """
    try:
        result = simulation_service.simulate_move(
            shipment_id=shipment_id,
            source_tour_id=source_tour_id,
            target_tour_id=target_tour_id,
        )

    except (ShipmentNotFoundError, TourNotFoundError) as exc:
        raise ToolError(str(exc)) from exc

    return result.model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
