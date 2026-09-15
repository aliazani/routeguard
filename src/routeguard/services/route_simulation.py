from datetime import date, datetime, time, timedelta

from routeguard.domain.models import SimulationResult
from routeguard.repositories.route_repository import RouteRepository


class RouteSimulationService:
    def __init__(self, repository: RouteRepository) -> None:
        self.repository = repository

    @staticmethod
    def _add_minutes(value: time, minutes: int) -> time:
        dt = datetime.combine(date.min, value)
        return (dt + timedelta(minutes=minutes)).time()

    def simulate_move(
        self,
        shipment_id: str,
        source_tour_id: int,
        target_tour_id: int,
    ) -> SimulationResult:
        shipment = self.repository.get_shipment(shipment_id)

        source_tour = self.repository.get_tour(source_tour_id)
        target_tour = self.repository.get_tour(target_tour_id)

        source_contains_shipment = any(
            stop.shipment_id == shipment_id for stop in source_tour.stops
        )

        if not source_contains_shipment:
            return SimulationResult(
                feasible=False,
                shipment_id=shipment_id,
                source_tour_id=source_tour_id,
                target_tour_id=target_tour_id,
                source_tour_version=source_tour.version,
                target_tour_version=target_tour.version,
                projected_load=0,
                vehicle_capacity=target_tour.vehicle_capacity,
                capacity_violation=False,
                time_window_violation=False,
                extra_distance_km=0,
                extra_duration_minutes=0,
                reason=(f"Shipment {shipment_id} does not belong to Tour {source_tour_id}."),
            )

        target_load = sum(
            self.repository.get_shipment(stop.shipment_id).capacity
            for stop in target_tour.stops
            if stop.shipment_id is not None
        )

        projected_load = target_load + shipment.capacity

        capacity_violation = projected_load > target_tour.vehicle_capacity

        # Simplified demo assumption:
        # shipment is inserted at the end of the target tour.
        extra_distance_km = 3.7
        extra_duration_minutes = 8

        projected_arrival: time | None = None
        projected_service_start: time | None = None

        last_stop = max(
            target_tour.stops,
            key=lambda stop: stop.sequence_index,
            default=None,
        )

        if last_stop is not None and last_stop.eta is not None:
            projected_arrival = self._add_minutes(
                last_stop.eta,
                extra_duration_minutes,
            )

            projected_service_start = projected_arrival

            # Arriving early is not necessarily a violation:
            # the driver can wait until the window opens.
            if (
                shipment.requested_start is not None
                and projected_service_start < shipment.requested_start
            ):
                projected_service_start = shipment.requested_start

        time_window_violation = (
            shipment.requested_end is not None
            and projected_service_start is not None
            and projected_service_start > shipment.requested_end
        )

        feasible = not capacity_violation and not time_window_violation

        reasons: list[str] = []

        if capacity_violation:
            reasons.append(
                f"Projected load {projected_load} exceeds "
                f"vehicle capacity {target_tour.vehicle_capacity}."
            )

        if time_window_violation:
            reasons.append(
                f"Projected service time {projected_service_start} "
                f"is after requested end {shipment.requested_end}."
            )

        return SimulationResult(
            feasible=feasible,
            shipment_id=shipment_id,
            source_tour_id=source_tour_id,
            target_tour_id=target_tour_id,
            source_tour_version=source_tour.version,
            target_tour_version=target_tour.version,
            projected_load=projected_load,
            vehicle_capacity=target_tour.vehicle_capacity,
            capacity_violation=capacity_violation,
            time_window_violation=time_window_violation,
            projected_arrival=projected_arrival,
            projected_service_start=projected_service_start,
            extra_distance_km=extra_distance_km,
            extra_duration_minutes=extra_duration_minutes,
            reason=" ".join(reasons) or None,
        )
