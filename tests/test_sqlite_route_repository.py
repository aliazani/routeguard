from datetime import UTC, datetime

import pytest

from routeguard.domain.models import (
    RouteChangeAudit,
)
from routeguard.repositories.route_repository import (
    VersionConflictError,
)
from routeguard.repositories.sqlite_route_repository import (
    SQLiteRouteRepository,
)


def test_sqlite_repository_seeds_data(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    repository = SQLiteRouteRepository(database)

    tour = repository.get_tour(12)
    shipment = repository.get_shipment("S102")

    assert tour.version == 3
    assert shipment.capacity == 25


def test_two_repository_instances_share_state(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    first = SQLiteRouteRepository(database)

    second = SQLiteRouteRepository(database)

    first.move_shipment(
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        expected_source_version=3,
        expected_target_version=4,
    )

    source = second.get_tour(12)
    target = second.get_tour(15)

    assert source.version == 4
    assert target.version == 5

    assert all(stop.shipment_id != "S102" for stop in source.stops)

    assert any(stop.shipment_id == "S102" for stop in target.stops)


def test_sqlite_repository_rejects_stale_version(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    repository = SQLiteRouteRepository(database)

    with pytest.raises(VersionConflictError):
        repository.move_shipment(
            shipment_id="S102",
            source_tour_id=12,
            target_tour_id=15,
            expected_source_version=2,
            expected_target_version=4,
        )


def test_audit_events_persist_between_instances(
    tmp_path,
) -> None:
    database = tmp_path / "routeguard.db"

    first = SQLiteRouteRepository(database)

    event = RouteChangeAudit(
        audit_id="audit-001",
        timestamp=datetime.now(UTC),
        operator="demo-user",
        idempotency_key="move-001",
        shipment_id="S102",
        source_tour_id=12,
        target_tour_id=15,
        source_version_before=3,
        source_version_after=4,
        target_version_before=4,
        target_version_after=5,
    )

    first.add_audit_event(event)

    second = SQLiteRouteRepository(database)

    events = second.list_audit_events()

    assert len(events) == 1

    assert events[0].audit_id == "audit-001"

    assert events[0].shipment_id == "S102"
