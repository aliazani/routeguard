import json
import sqlite3
from datetime import UTC, datetime, time
from pathlib import Path
from uuid import uuid4

from routeguard.domain.models import (
    MoveApplicationResult,
    RouteChangeAudit,
    Shipment,
    Stop,
    Tour,
)
from routeguard.repositories.route_repository import (
    IdempotencyRecordConflictError,
    ShipmentNotFoundError,
    ShipmentNotOnTourError,
    TourNotFoundError,
    VersionConflictError,
)


class SQLiteRouteRepository:
    def __init__(
        self,
        database_path: str | Path,
        *,
        seed: bool = True,
    ) -> None:
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database(seed=seed)

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=5.0,
        )

        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute("PRAGMA busy_timeout = 5000")

        return connection

    def _initialize_database(
        self,
        *,
        seed: bool,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS shipments (
                    shipment_id TEXT PRIMARY KEY,
                    capacity INTEGER NOT NULL,
                    requested_start TEXT,
                    requested_end TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tours (
                    tour_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL,
                    vehicle_capacity INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    stops_json TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    audit_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    shipment_id TEXT NOT NULL,
                    source_tour_id INTEGER NOT NULL,
                    target_tour_id INTEGER NOT NULL,
                    source_version_before INTEGER NOT NULL,
                    source_version_after INTEGER NOT NULL,
                    target_version_before INTEGER NOT NULL,
                    target_version_after INTEGER NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    request_fingerprint TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )

            if seed:
                self._seed_database(connection)

    def _seed_database(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        shipments = [
            (
                "S100",
                20,
                "09:00:00",
                "12:00:00",
            ),
            (
                "S102",
                25,
                "10:00:00",
                "15:00:00",
            ),
            (
                "S200",
                35,
                "08:00:00",
                "11:00:00",
            ),
            (
                "S300",
                50,
                "10:00:00",
                "15:00:00",
            ),
            (
                "S201",
                10,
                "14:00:00",
                "17:00:00",
            ),
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO shipments (
                shipment_id,
                capacity,
                requested_start,
                requested_end
            )
            VALUES (?, ?, ?, ?)
            """,
            shipments,
        )

        tours = [
            Tour(
                tour_id=12,
                status="planned",
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
            Tour(
                tour_id=15,
                status="planned",
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
            Tour(
                tour_id=16,
                status="planned",
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
        ]

        for tour in tours:
            connection.execute(
                """
                INSERT OR IGNORE INTO tours (
                    tour_id,
                    status,
                    vehicle_capacity,
                    version,
                    stops_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tour.tour_id,
                    tour.status.value,
                    tour.vehicle_capacity,
                    tour.version,
                    self._serialize_stops(tour.stops),
                ),
            )

    @staticmethod
    def _serialize_stops(
        stops: list[Stop],
    ) -> str:
        return json.dumps([stop.model_dump(mode="json") for stop in stops])

    @staticmethod
    def _row_to_tour(
        row: sqlite3.Row,
    ) -> Tour:
        return Tour(
            tour_id=row["tour_id"],
            status=row["status"],
            vehicle_capacity=(row["vehicle_capacity"]),
            version=row["version"],
            stops=json.loads(row["stops_json"]),
        )

    def get_tour(
        self,
        tour_id: int,
    ) -> Tour:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    tour_id,
                    status,
                    vehicle_capacity,
                    version,
                    stops_json
                FROM tours
                WHERE tour_id = ?
                """,
                (tour_id,),
            ).fetchone()

        if row is None:
            raise TourNotFoundError(f"Tour {tour_id} was not found.")

        return self._row_to_tour(row)

    def get_shipment(
        self,
        shipment_id: str,
    ) -> Shipment:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    shipment_id,
                    capacity,
                    requested_start,
                    requested_end
                FROM shipments
                WHERE shipment_id = ?
                """,
                (shipment_id,),
            ).fetchone()

        if row is None:
            raise ShipmentNotFoundError(f"Shipment {shipment_id} was not found.")

        return Shipment(
            shipment_id=row["shipment_id"],
            capacity=row["capacity"],
            requested_start=(
                time.fromisoformat(row["requested_start"])
                if row["requested_start"] is not None
                else None
            ),
            requested_end=(
                time.fromisoformat(row["requested_end"])
                if row["requested_end"] is not None
                else None
            ),
        )

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
        connection = self._connect()

        try:
            connection.execute("BEGIN IMMEDIATE")

            source_row = connection.execute(
                """
                SELECT
                    tour_id,
                    status,
                    vehicle_capacity,
                    version,
                    stops_json
                FROM tours
                WHERE tour_id = ?
                """,
                (source_tour_id,),
            ).fetchone()

            target_row = connection.execute(
                """
                SELECT
                    tour_id,
                    status,
                    vehicle_capacity,
                    version,
                    stops_json
                FROM tours
                WHERE tour_id = ?
                """,
                (target_tour_id,),
            ).fetchone()

            if source_row is None:
                raise TourNotFoundError(f"Tour {source_tour_id} was not found.")

            if target_row is None:
                raise TourNotFoundError(f"Tour {target_tour_id} was not found.")

            source_tour = self._row_to_tour(source_row)

            target_tour = self._row_to_tour(target_row)

            if source_tour.version != expected_source_version:
                raise VersionConflictError(
                    "Source tour version "
                    "conflict: "
                    f"expected "
                    f"{expected_source_version}, "
                    f"current "
                    f"{source_tour.version}."
                )

            if target_tour.version != expected_target_version:
                raise VersionConflictError(
                    "Target tour version "
                    "conflict: "
                    f"expected "
                    f"{expected_target_version}, "
                    f"current "
                    f"{target_tour.version}."
                )

            source_stop = next(
                (stop for stop in source_tour.stops if stop.shipment_id == shipment_id),
                None,
            )

            if source_stop is None:
                raise ShipmentNotOnTourError(
                    f"Shipment {shipment_id} is not assigned to Tour {source_tour_id}."
                )

            remaining_stops = [
                stop for stop in source_tour.stops if stop.shipment_id != shipment_id
            ]

            source_tour.stops = [
                stop.model_copy(
                    update={
                        "sequence_index": (index),
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

            source_update = connection.execute(
                """
                    UPDATE tours
                    SET
                        version = ?,
                        stops_json = ?
                    WHERE
                        tour_id = ?
                        AND version = ?
                    """,
                (
                    source_tour.version,
                    self._serialize_stops(source_tour.stops),
                    source_tour_id,
                    expected_source_version,
                ),
            )

            target_update = connection.execute(
                """
                    UPDATE tours
                    SET
                        version = ?,
                        stops_json = ?
                    WHERE
                        tour_id = ?
                        AND version = ?
                    """,
                (
                    target_tour.version,
                    self._serialize_stops(target_tour.stops),
                    target_tour_id,
                    expected_target_version,
                ),
            )

            if source_update.rowcount != 1 or target_update.rowcount != 1:
                raise VersionConflictError("Tour state changed while applying the route change.")

            connection.commit()

            return (
                source_tour,
                target_tour,
            )

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

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
        connection = self._connect()

        try:
            connection.execute("BEGIN IMMEDIATE")

            existing_row = connection.execute(
                """
                    SELECT
                        request_fingerprint,
                        result_json
                    FROM idempotency_records
                    WHERE idempotency_key = ?
                    """,
                (idempotency_key,),
            ).fetchone()

            if existing_row is not None:
                existing_fingerprint = existing_row["request_fingerprint"]

                if existing_fingerprint != request_fingerprint:
                    raise (
                        IdempotencyRecordConflictError(
                            "The idempotency key was already used for a different request."
                        )
                    )

                result = MoveApplicationResult.model_validate_json(existing_row["result_json"])

                connection.commit()

                return result

            source_row = connection.execute(
                """
                SELECT
                    tour_id,
                    status,
                    vehicle_capacity,
                    version,
                    stops_json
                FROM tours
                WHERE tour_id = ?
                """,
                (source_tour_id,),
            ).fetchone()

            target_row = connection.execute(
                """
                SELECT
                    tour_id,
                    status,
                    vehicle_capacity,
                    version,
                    stops_json
                FROM tours
                WHERE tour_id = ?
                """,
                (target_tour_id,),
            ).fetchone()

            if source_row is None:
                raise TourNotFoundError(f"Tour {source_tour_id} was not found.")

            if target_row is None:
                raise TourNotFoundError(f"Tour {target_tour_id} was not found.")

            source_tour = self._row_to_tour(source_row)

            target_tour = self._row_to_tour(target_row)

            if source_tour.version != expected_source_version:
                raise VersionConflictError(
                    "Source tour version "
                    "conflict: "
                    f"expected "
                    f"{expected_source_version}, "
                    f"current "
                    f"{source_tour.version}."
                )

            if target_tour.version != expected_target_version:
                raise VersionConflictError(
                    "Target tour version "
                    "conflict: "
                    f"expected "
                    f"{expected_target_version}, "
                    f"current "
                    f"{target_tour.version}."
                )

            source_stop = next(
                (stop for stop in source_tour.stops if stop.shipment_id == shipment_id),
                None,
            )

            if source_stop is None:
                raise ShipmentNotOnTourError(
                    f"Shipment {shipment_id} is not assigned to Tour {source_tour_id}."
                )

            remaining_stops = [
                stop for stop in source_tour.stops if stop.shipment_id != shipment_id
            ]

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

            source_before = source_tour.version

            target_before = target_tour.version

            source_tour.version += 1
            target_tour.version += 1

            source_update = connection.execute(
                """
                    UPDATE tours
                    SET
                        version = ?,
                        stops_json = ?
                    WHERE
                        tour_id = ?
                        AND version = ?
                    """,
                (
                    source_tour.version,
                    self._serialize_stops(source_tour.stops),
                    source_tour_id,
                    expected_source_version,
                ),
            )

            target_update = connection.execute(
                """
                    UPDATE tours
                    SET
                        version = ?,
                        stops_json = ?
                    WHERE
                        tour_id = ?
                        AND version = ?
                    """,
                (
                    target_tour.version,
                    self._serialize_stops(target_tour.stops),
                    target_tour_id,
                    expected_target_version,
                ),
            )

            if source_update.rowcount != 1 or target_update.rowcount != 1:
                raise VersionConflictError("Tour state changed while applying the route change.")

            audit = RouteChangeAudit(
                audit_id=str(uuid4()),
                timestamp=datetime.now(UTC),
                operator=operator,
                idempotency_key=(idempotency_key),
                shipment_id=shipment_id,
                source_tour_id=(source_tour_id),
                target_tour_id=(target_tour_id),
                source_version_before=(source_before),
                source_version_after=(source_tour.version),
                target_version_before=(target_before),
                target_version_after=(target_tour.version),
            )

            connection.execute(
                """
                INSERT INTO audit_events (
                    audit_id,
                    timestamp,
                    action,
                    operator,
                    idempotency_key,
                    shipment_id,
                    source_tour_id,
                    target_tour_id,
                    source_version_before,
                    source_version_after,
                    target_version_before,
                    target_version_after
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    audit.audit_id,
                    audit.timestamp.isoformat(),
                    audit.action,
                    audit.operator,
                    audit.idempotency_key,
                    audit.shipment_id,
                    audit.source_tour_id,
                    audit.target_tour_id,
                    audit.source_version_before,
                    audit.source_version_after,
                    audit.target_version_before,
                    audit.target_version_after,
                ),
            )

            result = MoveApplicationResult(
                shipment_id=shipment_id,
                source_tour_id=(source_tour_id),
                target_tour_id=(target_tour_id),
                source_version=(source_tour.version),
                target_version=(target_tour.version),
                audit_id=(audit.audit_id),
            )

            connection.execute(
                """
                INSERT INTO idempotency_records (
                    idempotency_key,
                    request_fingerprint,
                    result_json
                )
                VALUES (?, ?, ?)
                """,
                (
                    idempotency_key,
                    request_fingerprint,
                    result.model_dump_json(),
                ),
            )

            connection.commit()

            return result

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def add_audit_event(
        self,
        event: RouteChangeAudit,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    audit_id,
                    timestamp,
                    action,
                    operator,
                    idempotency_key,
                    shipment_id,
                    source_tour_id,
                    target_tour_id,
                    source_version_before,
                    source_version_after,
                    target_version_before,
                    target_version_after
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    event.audit_id,
                    event.timestamp.isoformat(),
                    event.action,
                    event.operator,
                    event.idempotency_key,
                    event.shipment_id,
                    event.source_tour_id,
                    event.target_tour_id,
                    event.source_version_before,
                    event.source_version_after,
                    event.target_version_before,
                    event.target_version_after,
                ),
            )

    def list_audit_events(
        self,
    ) -> list[RouteChangeAudit]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    audit_id,
                    timestamp,
                    action,
                    operator,
                    idempotency_key,
                    shipment_id,
                    source_tour_id,
                    target_tour_id,
                    source_version_before,
                    source_version_after,
                    target_version_before,
                    target_version_after
                FROM audit_events
                ORDER BY timestamp
                """
            ).fetchall()

        return [
            RouteChangeAudit(
                audit_id=row["audit_id"],
                timestamp=row["timestamp"],
                action=row["action"],
                operator=row["operator"],
                idempotency_key=row["idempotency_key"],
                shipment_id=row["shipment_id"],
                source_tour_id=row["source_tour_id"],
                target_tour_id=row["target_tour_id"],
                source_version_before=row["source_version_before"],
                source_version_after=row["source_version_after"],
                target_version_before=row["target_version_before"],
                target_version_after=row["target_version_after"],
            )
            for row in rows
        ]

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
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    request_fingerprint,
                    result_json
                FROM idempotency_records
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()

        if row is None:
            return None

        result = MoveApplicationResult.model_validate_json(row["result_json"])

        return (
            row["request_fingerprint"],
            result,
        )

    def save_idempotency_record(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        result: MoveApplicationResult,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO idempotency_records (
                        idempotency_key,
                        request_fingerprint,
                        result_json
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        idempotency_key,
                        request_fingerprint,
                        result.model_dump_json(),
                    ),
                )

        except sqlite3.IntegrityError as exc:
            existing = self.get_idempotency_record(idempotency_key)

            if existing is None:
                raise

            (
                existing_fingerprint,
                existing_result,
            ) = existing

            if existing_fingerprint != request_fingerprint or existing_result != result:
                raise (
                    IdempotencyRecordConflictError(
                        "The idempotency key already exists for a different request."
                    )
                ) from exc
