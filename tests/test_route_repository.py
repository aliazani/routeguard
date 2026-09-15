import pytest

from routeguard.repositories.route_repository import (
    InMemoryRouteRepository,
    ShipmentNotFoundError,
    TourNotFoundError,
)


def test_get_existing_tour() -> None:
    repository = InMemoryRouteRepository()

    tour = repository.get_tour(12)

    assert tour.tour_id == 12
    assert tour.vehicle_capacity == 100
    assert tour.version == 3
    assert len(tour.stops) == 3

    assert [stop.shipment_id for stop in tour.stops] == [
        "S100",
        "S102",
        "S300",
    ]


def test_get_missing_tour() -> None:
    repository = InMemoryRouteRepository()

    with pytest.raises(TourNotFoundError):
        repository.get_tour(999)


def test_get_existing_shipment() -> None:
    repository = InMemoryRouteRepository()

    shipment = repository.get_shipment("S102")

    assert shipment.shipment_id == "S102"
    assert shipment.capacity == 25


def test_get_missing_shipment() -> None:
    repository = InMemoryRouteRepository()

    with pytest.raises(ShipmentNotFoundError):
        repository.get_shipment("S999")
