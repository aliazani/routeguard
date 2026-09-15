from datetime import datetime, time
from enum import StrEnum

from pydantic import BaseModel, Field


class TourStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    STARTED = "started"
    FINISHED = "finished"


class Shipment(BaseModel):
    shipment_id: str
    capacity: int = Field(gt=0)
    requested_start: time | None = None
    requested_end: time | None = None


class Stop(BaseModel):
    stop_id: str
    sequence_index: int = Field(ge=0)
    shipment_id: str | None = None
    eta: time | None = None


class Tour(BaseModel):
    tour_id: int
    status: TourStatus
    vehicle_capacity: int = Field(gt=0)
    version: int = Field(ge=0)
    stops: list[Stop] = Field(default_factory=list)


class SimulationResult(BaseModel):
    feasible: bool

    shipment_id: str
    source_tour_id: int
    target_tour_id: int

    source_tour_version: int
    target_tour_version: int

    projected_load: int
    vehicle_capacity: int

    capacity_violation: bool
    time_window_violation: bool

    projected_arrival: time | None = None
    projected_service_start: time | None = None

    extra_distance_km: float
    extra_duration_minutes: int

    reason: str | None = None


class RouteChangeAudit(BaseModel):
    audit_id: str
    timestamp: datetime

    action: str = "move_shipment"

    operator: str
    idempotency_key: str

    shipment_id: str
    source_tour_id: int
    target_tour_id: int

    source_version_before: int
    source_version_after: int

    target_version_before: int
    target_version_after: int


class MoveApplicationResult(BaseModel):
    applied: bool = True

    shipment_id: str
    source_tour_id: int
    target_tour_id: int

    source_version: int
    target_version: int

    audit_id: str
