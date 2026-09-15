from enum import StrEnum

from pydantic import BaseModel


class IntentType(StrEnum):
    MOVE_SHIPMENT = "move_shipment"
    GET_TOUR = "get_tour"
    ASK_POLICY = "ask_policy"
    GENERAL = "general"


class RouteIntent(BaseModel):
    intent: IntentType
    shipment_id: str | None = None
    tour_id: int | None = None
    target_tour_id: int | None = None
    question: str | None = None
