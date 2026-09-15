from routeguard.config import get_settings
from routeguard.repositories.route_repository import (
    RouteRepository,
)
from routeguard.repositories.sqlite_route_repository import (
    SQLiteRouteRepository,
)


def create_route_repository() -> RouteRepository:
    settings = get_settings()

    return SQLiteRouteRepository(settings.route_db_path)
