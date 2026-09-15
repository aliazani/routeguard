from fastapi import FastAPI

from routeguard.api.route_changes import (
    create_route_change_router,
)
from routeguard.api.router import api_router
from routeguard.config import get_settings
from routeguard.middleware.request_id import RequestIdMiddleware
from routeguard.observability.logging import configure_logging
from routeguard.repositories.factory import (
    create_route_repository,
)


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(settings.log_level)

    app = FastAPI(
        title="RouteGuard",
        description=("Agentic route-planning copilot with document-grounded RAG."),
        version="0.1.0",
    )

    app.state.settings = settings

    app.add_middleware(RequestIdMiddleware)

    # Existing API routes:
    # /api/health
    # /api/chat
    app.include_router(api_router)

    # Shared operational repository
    # used by the route-change workflow.
    route_repository = create_route_repository()

    # Human-approved route-change API.
    app.include_router(create_route_change_router(route_repository))

    return app


app = create_app()
