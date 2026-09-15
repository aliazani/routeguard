from typing import Annotated

from fastapi import APIRouter, Depends

from routeguard.dependencies import get_intent_service
from routeguard.schemas.chat import ChatRequest
from routeguard.schemas.intent import RouteIntent
from routeguard.services.intent import IntentService

router = APIRouter()


@router.post(
    "/intent",
    response_model=RouteIntent,
)
async def classify_intent(
    request: ChatRequest,
    service: Annotated[
        IntentService,
        Depends(get_intent_service),
    ],
) -> RouteIntent:
    return await service.classify(request.message)
