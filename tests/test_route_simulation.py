from datetime import time

from routeguard.repositories.route_repository import (
    InMemoryRouteRepository,
)
from routeguard.services.route_simulation import (
    RouteSimulationService,
)


def test_simulate_valid_move() -> None:
    repository = InMemoryRouteRepository()
    service = RouteSimulationService(repository)

    result = service.simulate_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
    )

    assert result.feasible is True

    assert result.source_tour_version == 3
    assert result.target_tour_version == 4

    assert result.capacity_violation is False
    assert result.time_window_violation is False

    assert result.projected_load == 60
    assert result.vehicle_capacity == 70

    assert result.projected_arrival == time(9, 8)
    assert result.projected_service_start == time(10, 0)


def test_move_rejected_when_shipment_not_in_source_tour() -> None:
    repository = InMemoryRouteRepository()
    service = RouteSimulationService(repository)

    result = service.simulate_move(
        shipment_id="S200",
        source_tour_id=12,
        target_tour_id=15,
    )

    assert result.feasible is False

    assert result.source_tour_version == 3
    assert result.target_tour_version == 4

    assert result.capacity_violation is False
    assert result.time_window_violation is False

    assert result.reason is not None


def test_move_rejected_when_capacity_exceeded() -> None:
    repository = InMemoryRouteRepository()
    service = RouteSimulationService(repository)

    result = service.simulate_move(
        shipment_id="S300",
        source_tour_id=12,
        target_tour_id=15,
    )

    assert result.feasible is False

    assert result.source_tour_version == 3
    assert result.target_tour_version == 4

    assert result.capacity_violation is True
    assert result.time_window_violation is False

    assert result.projected_load == 85
    assert result.vehicle_capacity == 70

    assert result.reason is not None


def test_move_rejected_when_time_window_exceeded() -> None:
    repository = InMemoryRouteRepository()
    service = RouteSimulationService(repository)

    result = service.simulate_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=16,
    )

    assert result.feasible is False

    assert result.source_tour_version == 3
    assert result.target_tour_version == 1

    assert result.capacity_violation is False
    assert result.time_window_violation is True

    assert result.projected_arrival == time(15, 18)
    assert result.projected_service_start == time(15, 18)

    assert result.reason is not None
