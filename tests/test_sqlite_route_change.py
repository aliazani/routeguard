import pytest

from routeguard.repositories.route_repository import (
    VersionConflictError,
)
from routeguard.repositories.sqlite_route_repository import (
    SQLiteRouteRepository,
)
from routeguard.services.route_change import (
    IdempotencyConflictError,
    RouteChangeService,
)


def test_idempotent_retry_survives_new_service_instance(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    repository_1 = SQLiteRouteRepository(database)

    service_1 = RouteChangeService(repository_1)

    first = service_1.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key=("persistent-001"),
    )

    repository_2 = SQLiteRouteRepository(database)

    service_2 = RouteChangeService(repository_2)

    second = service_2.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key=("persistent-001"),
    )

    assert first == second

    assert repository_2.get_tour(12).version == 4

    assert repository_2.get_tour(15).version == 5

    assert len(repository_2.list_audit_events()) == 1

    record = repository_2.get_idempotency_record("persistent-001")

    assert record is not None

    _, stored_result = record

    assert stored_result == first


def test_reused_key_with_different_request_is_rejected(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    repository = SQLiteRouteRepository(database)

    service = RouteChangeService(repository)

    service.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key=("persistent-001"),
    )

    second_repository = SQLiteRouteRepository(database)

    second_service = RouteChangeService(second_repository)

    with pytest.raises(IdempotencyConflictError):
        second_service.apply_move(
            shipment_id="S100",
            source_tour_id=12,
            target_tour_id=16,
            expected_source_version=3,
            expected_target_version=1,
            operator="demo-user",
            idempotency_key=("persistent-001"),
        )


def test_atomic_move_writes_route_audit_and_idempotency(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    repository = SQLiteRouteRepository(database)

    service = RouteChangeService(repository)

    result = service.apply_move(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
        operator="demo-user",
        idempotency_key=("atomic-success-001"),
    )

    source = repository.get_tour(12)

    target = repository.get_tour(15)

    assert source.version == 4
    assert target.version == 5

    assert all(stop.shipment_id != "S102" for stop in source.stops)

    assert any(stop.shipment_id == "S102" for stop in target.stops)

    audits = repository.list_audit_events()

    assert len(audits) == 1

    assert audits[0].audit_id == result.audit_id

    assert audits[0].shipment_id == "S102"

    idempotency_record = repository.get_idempotency_record("atomic-success-001")

    assert idempotency_record is not None

    _, stored_result = idempotency_record

    assert stored_result == result


def test_failed_atomic_move_leaves_no_partial_state(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    repository = SQLiteRouteRepository(database)

    service = RouteChangeService(repository)

    with pytest.raises(VersionConflictError):
        service.apply_move(
            shipment_id="S102",
            source_tour_id=12,
            target_tour_id=15,
            expected_source_version=3,
            expected_target_version=999,
            operator="demo-user",
            idempotency_key=("atomic-failure-001"),
        )

    source = repository.get_tour(12)

    target = repository.get_tour(15)

    assert source.version == 3
    assert target.version == 4

    assert any(stop.shipment_id == "S102" for stop in source.stops)

    assert all(stop.shipment_id != "S102" for stop in target.stops)

    assert repository.list_audit_events() == []

    assert repository.get_idempotency_record("atomic-failure-001") is None
