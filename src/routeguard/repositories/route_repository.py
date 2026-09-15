from datetime import UTC, datetime, time
from typing import Protocol
from uuid import uuid4

from routeguard.domain.models import (
    MoveApplicationResult,
    RouteChangeAudit,
    Shipment,
    Stop,
    Tour,
    TourStatus,
)


class TourNotFoundError(Exception):
    pass


class ShipmentNotFoundError(Exception):
    pass


class VersionConflictError(Exception):
    pass


class ShipmentNotOnTourError(Exception):
    pass


class IdempotencyRecordConflictError(Exception):
    pass


class RouteRepository(Protocol):
    def get_tour(
        self,
        tour_id: int,
    ) -> Tour: ...

    def get_shipment(
        self,
        shipment_id: str,
    ) -> Shipment: ...

    def move_shipment(
        self,
        *,
        shipment_id: str,
        source_tour_id: int,
        target_tour_id: int,
        expected_source_version: int,
        expected_target_version: int,
        target_eta: time | None = None,
    ) -> tuple[Tour, Tour]: ...

    def add_audit_event(
        self,
        event: RouteChangeAudit,
    ) -> None: ...

    def list_audit_events(
        self,
    ) -> list[RouteChangeAudit]: ...

    def get_idempotency_record(
        self,
        idempotency_key: str,
    ) -> (
        tuple[
            str,
            MoveApplicationResult,
        ]
        | None
    ): ...

    def save_idempotency_record(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        result: MoveApplicationResult,
    ) -> None: ...

    def apply_move_atomic(
        self,
        *,
        shipment_id: str,
        source_tour_id: int,
        target_tour_id: int,
        expected_source_version: int,
        expected_target_version: int,
        target_eta: time | None,
        operator: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> MoveApplicationResult: ...


class InMemoryRouteRepository:
    def __init__(self) -> None:
        self._shipments = {
            "S100": Shipment(
                shipment_id="S100",
                capacity=20,
                requested_start=time(9, 0),
                requested_end=time(12, 0),
            ),
            "S102": Shipment(
                shipment_id="S102",
                capacity=25,
                requested_start=time(10, 0),
                requested_end=time(15, 0),
            ),
            "S200": Shipment(
                shipment_id="S200",
                capacity=35,
                requested_start=time(8, 0),
                requested_end=time(11, 0),
            ),
            "S300": Shipment(
                shipment_id="S300",
                capacity=50,
                requested_start=time(10, 0),
                requested_end=time(15, 0),
            ),
            "S201": Shipment(
                shipment_id="S201",
                capacity=10,
                requested_start=time(14, 0),
                requested_end=time(17, 0),
            ),
        }

        self._tours = {
            12: Tour(
                tour_id=12,
                status=TourStatus.PLANNED,
                vehicle_capacity=100,
                version=3,
                stops=[
                    Stop(
                        stop_id="ST100",
                        sequence_index=0,
                        shipment_id="S100",
                        eta=time(10, 0),
                    ),
                    Stop(
                        stop_id="ST102",
                        sequence_index=1,
                        shipment_id="S102",
                        eta=time(11, 0),
                    ),
                    Stop(
                        stop_id="ST300",
                        sequence_index=2,
                        shipment_id="S300",
                        eta=time(12, 0),
                    ),
                ],
            ),
            15: Tour(
                tour_id=15,
                status=TourStatus.PLANNED,
                vehicle_capacity=70,
                version=4,
                stops=[
                    Stop(
                        stop_id="ST200",
                        sequence_index=0,
                        shipment_id="S200",
                        eta=time(9, 0),
                    ),
                ],
            ),
            16: Tour(
                tour_id=16,
                status=TourStatus.PLANNED,
                vehicle_capacity=100,
                version=1,
                stops=[
                    Stop(
                        stop_id="ST201",
                        sequence_index=0,
                        shipment_id="S201",
                        eta=time(15, 10),
                    ),
                ],
            ),
        }

        self._audit_events: list[RouteChangeAudit] = []

        self._idempotency_records: dict[
            str,
            tuple[
                str,
                MoveApplicationResult,
            ],
        ] = {}

    def get_tour(
        self,
        tour_id: int,
    ) -> Tour:
        try:
            return self._tours[tour_id]
        except KeyError as exc:
            raise TourNotFoundError(f"Tour {tour_id} was not found.") from exc

    def get_shipment(
        self,
        shipment_id: str,
    ) -> Shipment:
        try:
            return self._shipments[shipment_id]
        except KeyError as exc:
            raise ShipmentNotFoundError(f"Shipment {shipment_id} was not found.") from exc

    def move_shipment(
        self,
        *,
        shipment_id: str,
        source_tour_id: int,
        target_tour_id: int,
        expected_source_version: int,
        expected_target_version: int,
        target_eta: time | None = None,
    ) -> tuple[Tour, Tour]:
        source_tour = self.get_tour(source_tour_id)

        target_tour = self.get_tour(target_tour_id)

        if source_tour.version != expected_source_version:
            raise VersionConflictError(
                "Source tour version conflict: "
                f"expected {expected_source_version}, "
                f"current {source_tour.version}."
            )

        if target_tour.version != expected_target_version:
            raise VersionConflictError(
                "Target tour version conflict: "
                f"expected {expected_target_version}, "
                f"current {target_tour.version}."
            )

        source_stop = next(
            (stop for stop in source_tour.stops if stop.shipment_id == shipment_id),
            None,
        )

        if source_stop is None:
            raise ShipmentNotOnTourError(
                f"Shipment {shipment_id} is not assigned to Tour {source_tour_id}."
            )

        remaining_stops = [stop for stop in source_tour.stops if stop.shipment_id != shipment_id]

        source_tour.stops = [
            stop.model_copy(
                update={
                    "sequence_index": index,
                }
            )
            for index, stop in enumerate(remaining_stops)
        ]

        moved_stop = source_stop.model_copy(
            update={
                "sequence_index": len(target_tour.stops),
                "eta": target_eta,
            }
        )

        target_tour.stops = [
            *target_tour.stops,
            moved_stop,
        ]

        source_tour.version += 1
        target_tour.version += 1

        return (
            source_tour,
            target_tour,
        )

    def add_audit_event(
        self,
        event: RouteChangeAudit,
    ) -> None:
        self._audit_events.append(event)

    def list_audit_events(
        self,
    ) -> list[RouteChangeAudit]:
        return list(self._audit_events)

    def get_idempotency_record(
        self,
        idempotency_key: str,
    ) -> (
        tuple[
            str,
            MoveApplicationResult,
        ]
        | None
    ):
        return self._idempotency_records.get(idempotency_key)

    def save_idempotency_record(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        result: MoveApplicationResult,
    ) -> None:
        existing = self._idempotency_records.get(idempotency_key)

        if existing is not None:
            (
                existing_fingerprint,
                existing_result,
            ) = existing

            if existing_fingerprint != request_fingerprint or existing_result != result:
                raise (
                    IdempotencyRecordConflictError(
                        "The idempotency key already exists for a different request."
                    )
                )

            return

        self._idempotency_records[idempotency_key] = (
            request_fingerprint,
            result,
        )

    def apply_move_atomic(
        self,
        *,
        shipment_id: str,
        source_tour_id: int,
        target_tour_id: int,
        expected_source_version: int,
        expected_target_version: int,
        target_eta: time | None,
        operator: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> MoveApplicationResult:
        existing = self.get_idempotency_record(idempotency_key)

        if existing is not None:
            (
                existing_fingerprint,
                existing_result,
            ) = existing

            if existing_fingerprint != request_fingerprint:
                raise (
                    IdempotencyRecordConflictError(
                        "The idempotency key was already used for a different request."
                    )
                )

            return existing_result

        source_before = self.get_tour(source_tour_id).version

        target_before = self.get_tour(target_tour_id).version

        (
            updated_source,
            updated_target,
        ) = self.move_shipment(
            shipment_id=shipment_id,
            source_tour_id=source_tour_id,
            target_tour_id=target_tour_id,
            expected_source_version=(expected_source_version),
            expected_target_version=(expected_target_version),
            target_eta=target_eta,
        )

        audit = RouteChangeAudit(
            audit_id=str(uuid4()),
            timestamp=datetime.now(UTC),
            operator=operator,
            idempotency_key=(idempotency_key),
            shipment_id=shipment_id,
            source_tour_id=(source_tour_id),
            target_tour_id=(target_tour_id),
            source_version_before=(source_before),
            source_version_after=(updated_source.version),
            target_version_before=(target_before),
            target_version_after=(updated_target.version),
        )

        self.add_audit_event(audit)

        result = MoveApplicationResult(
            shipment_id=shipment_id,
            source_tour_id=(source_tour_id),
            target_tour_id=(target_tour_id),
            source_version=(updated_source.version),
            target_version=(updated_target.version),
            audit_id=audit.audit_id,
        )

        self.save_idempotency_record(
            idempotency_key=(idempotency_key),
            request_fingerprint=(request_fingerprint),
            result=result,
        )

        return result
