import pytest

from routeguard.repositories.route_repository import (
    InMemoryRouteRepository,
    VersionConflictError,
)
from routeguard.services.route_change import (
    IdempotencyConflictError,
    InfeasibleMoveError,
    RouteChangeService,
)


def create_service() -> tuple[
    InMemoryRouteRepository,
    RouteChangeService,
]:
    repository = InMemoryRouteRepository()

    service = RouteChangeService(repository)

    return repository, service


def test_apply_feasible_move() -> None:
    repository, service = create_service()

    result = service.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key="move-001",
    )

    assert result.applied is True
    assert result.source_version == 4
    assert result.target_version == 5

    source = repository.get_tour(12)
    target = repository.get_tour(15)

    assert all(stop.shipment_id != "S102" for stop in source.stops)

    assert any(stop.shipment_id == "S102" for stop in target.stops)

    audits = repository.list_audit_events()

    assert len(audits) == 1

    audit = audits[0]

    assert audit.shipment_id == "S102"
    assert audit.source_version_before == 3
    assert audit.source_version_after == 4
    assert audit.target_version_before == 4
    assert audit.target_version_after == 5


def test_rejects_stale_version() -> None:
    _, service = create_service()

    with pytest.raises(VersionConflictError):
        service.apply_move(
            shipment_id="S102",
            source_tour_id=12,
            target_tour_id=15,
            expected_source_version=2,
            expected_target_version=4,
            operator="demo-user",
            idempotency_key=("move-stale"),
        )


def test_rejects_infeasible_move() -> None:
    _, service = create_service()

    with pytest.raises(
        InfeasibleMoveError,
        match="85",
    ):
        service.apply_move(
            shipment_id="S300",
            source_tour_id=12,
            target_tour_id=15,
            expected_source_version=3,
            expected_target_version=4,
            operator="demo-user",
            idempotency_key=("move-infeasible"),
        )


def test_idempotent_retry_does_not_apply_twice() -> None:
    repository, service = create_service()

    first = service.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key="move-001",
    )

    second = service.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key="move-001",
    )

    assert first == second

    assert repository.get_tour(12).version == 4

    assert repository.get_tour(15).version == 5

    assert len(repository.list_audit_events()) == 1


def test_rejects_reused_idempotency_key_for_different_request() -> None:
    _, service = create_service()

    service.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key="move-001",
    )

    with pytest.raises(IdempotencyConflictError):
        service.apply_move(
            shipment_id="S100",
            source_tour_id=12,
            target_tour_id=16,
            expected_source_version=3,
            expected_target_version=1,
            operator="demo-user",
            idempotency_key="move-001",
        )
