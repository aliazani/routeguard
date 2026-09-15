from fastapi import APIRouter

from routeguard.api.agent import (
    router as agent_router,
)
from routeguard.api.routes.chat import router as chat_router
from routeguard.api.routes.health import router as health_router
from routeguard.api.routes.intent import router as intent_router

api_router = APIRouter(prefix="/api")

api_router.include_router(
    health_router,
    tags=["health"],
)

api_router.include_router(
    chat_router,
    tags=["chat"],
)

api_router.include_router(
    intent_router,
    tags=["intent"],
)

api_router.include_router(agent_router)
