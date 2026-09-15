from fastapi import FastAPI
from fastapi.testclient import (
    TestClient,
)

from routeguard.api.route_changes import (
    create_route_change_router,
)
from routeguard.repositories.route_repository import (
    InMemoryRouteRepository,
)


def create_test_client() -> tuple[
    TestClient,
    InMemoryRouteRepository,
]:
    repository = InMemoryRouteRepository()

    app = FastAPI()

    app.include_router(create_route_change_router(repository))

    return (
        TestClient(app),
        repository,
    )


def test_start_route_change_requires_approval() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/route-changes",
        json={
            "shipment_id": "S102",
            "source_tour_id": 12,
            "target_tour_id": 15,
            "operator": "demo-user",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "approval_required"

    assert data["thread_id"]

    assert data["approval"]["shipment_id"] == "S102"

    assert data["approval"]["source_tour_version"] == 3

    assert data["approval"]["target_tour_version"] == 4


def test_confirm_route_change_applies_move() -> None:
    client, repository = create_test_client()

    start = client.post(
        "/route-changes",
        json={
            "shipment_id": "S102",
            "source_tour_id": 12,
            "target_tour_id": 15,
            "operator": "demo-user",
        },
    )

    thread_id = start.json()["thread_id"]

    response = client.post(f"/route-changes/{thread_id}/confirm")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "applied"

    assert data["source_version_after"] == 4

    assert data["target_version_after"] == 5

    assert data["audit_id"]

    source = repository.get_tour(12)

    target = repository.get_tour(15)

    assert all(stop.shipment_id != "S102" for stop in source.stops)

    assert any(stop.shipment_id == "S102" for stop in target.stops)


def test_reject_route_change_does_not_mutate() -> None:
    client, repository = create_test_client()

    start = client.post(
        "/route-changes",
        json={
            "shipment_id": "S102",
            "source_tour_id": 12,
            "target_tour_id": 15,
            "operator": "demo-user",
        },
    )

    thread_id = start.json()["thread_id"]

    response = client.post(f"/route-changes/{thread_id}/reject")

    assert response.status_code == 200

    assert response.json()["status"] == "rejected"

    source = repository.get_tour(12)

    target = repository.get_tour(15)

    assert source.version == 3
    assert target.version == 4

    assert any(stop.shipment_id == "S102" for stop in source.stops)


def test_infeasible_route_change_never_requests_approval() -> None:
    client, repository = create_test_client()

    response = client.post(
        "/route-changes",
        json={
            "shipment_id": "S300",
            "source_tour_id": 12,
            "target_tour_id": 15,
            "operator": "demo-user",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "infeasible"

    assert data["feasible"] is False

    assert data["reason"]

    assert repository.list_audit_events() == []


def test_stale_state_returns_conflict() -> None:
    client, repository = create_test_client()

    start = client.post(
        "/route-changes",
        json={
            "shipment_id": "S102",
            "source_tour_id": 12,
            "target_tour_id": 15,
            "operator": "demo-user",
        },
    )

    thread_id = start.json()["thread_id"]

    # Another operation modifies the
    # target tour while approval waits.
    target = repository.get_tour(15)

    target.version += 1

    response = client.post(f"/route-changes/{thread_id}/confirm")

    assert response.status_code == 409

    source = repository.get_tour(12)

    assert any(stop.shipment_id == "S102" for stop in source.stops)


def test_confirm_unknown_thread_returns_404() -> None:
    client, _ = create_test_client()

    response = client.post("/route-changes/not-real/confirm")

    assert response.status_code == 404
