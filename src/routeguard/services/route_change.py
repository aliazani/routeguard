import hashlib
import json

from routeguard.domain.models import (
    MoveApplicationResult,
)
from routeguard.repositories.route_repository import (
    IdempotencyRecordConflictError,
    RouteRepository,
)
from routeguard.services.route_simulation import (
    RouteSimulationService,
)


class InfeasibleMoveError(Exception):
    pass


class IdempotencyConflictError(Exception):
    pass


class RouteChangeService:
    def __init__(
        self,
        repository: RouteRepository,
    ) -> None:
        self.repository = repository

        self.simulation_service = RouteSimulationService(repository)

    @staticmethod
    def _request_fingerprint(
        *,
        shipment_id: str,
        source_tour_id: int,
        target_tour_id: int,
        expected_source_version: int,
        expected_target_version: int,
        operator: str,
    ) -> str:
        payload = {
            "shipment_id": shipment_id,
            "source_tour_id": (source_tour_id),
            "target_tour_id": (target_tour_id),
            "expected_source_version": (expected_source_version),
            "expected_target_version": (expected_target_version),
            "operator": operator,
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(encoded).hexdigest()

    def apply_move(
        self,
        *,
        shipment_id: str,
        source_tour_id: int,
        target_tour_id: int,
        expected_source_version: int,
        expected_target_version: int,
        operator: str,
        idempotency_key: str,
    ) -> MoveApplicationResult:
        if not operator.strip():
            raise ValueError("operator cannot be empty")

        if not idempotency_key.strip():
            raise ValueError("idempotency_key cannot be empty")

        if source_tour_id == target_tour_id:
            raise InfeasibleMoveError("Source and target tour must be different.")

        fingerprint = self._request_fingerprint(
            shipment_id=shipment_id,
            source_tour_id=(source_tour_id),
            target_tour_id=(target_tour_id),
            expected_source_version=(expected_source_version),
            expected_target_version=(expected_target_version),
            operator=operator,
        )

        # A retry after a successful request must
        # return the original result without trying
        # to simulate the already-applied move again.
        existing = self.repository.get_idempotency_record(idempotency_key)

        if existing is not None:
            (
                existing_fingerprint,
                existing_result,
            ) = existing

            if existing_fingerprint != fingerprint:
                raise (
                    IdempotencyConflictError(
                        "The idempotency key was already used for a different request."
                    )
                )

            return existing_result

        simulation = self.simulation_service.simulate_move(
            shipment_id=shipment_id,
            source_tour_id=(source_tour_id),
            target_tour_id=(target_tour_id),
        )

        if not simulation.feasible:
            raise InfeasibleMoveError(simulation.reason or ("The proposed move is not feasible."))

        try:
            return self.repository.apply_move_atomic(
                shipment_id=shipment_id,
                source_tour_id=(source_tour_id),
                target_tour_id=(target_tour_id),
                expected_source_version=(expected_source_version),
                expected_target_version=(expected_target_version),
                target_eta=(simulation.projected_service_start),
                operator=operator,
                idempotency_key=(idempotency_key),
                request_fingerprint=(fingerprint),
            )

        except IdempotencyRecordConflictError as exc:
            raise IdempotencyConflictError(
                "The idempotency key was already used for a different request."
            ) from exc
