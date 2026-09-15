import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from routeguard.observability.context import request_id_var

logger = logging.getLogger("routeguard.http")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)

        request_id = headers.get("x-request-id") or str(uuid4())

        token = request_id_var.set(request_id)
        started_at = perf_counter()

        status_code: int | None = None

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

                response_headers = MutableHeaders(scope=message)
                response_headers["X-Request-ID"] = request_id

            await send(message)

        logger.info(
            "request_started",
            extra={
                "method": scope["method"],
                "path": scope["path"],
            },
        )

        try:
            await self.app(
                scope,
                receive,
                send_with_request_id,
            )
        finally:
            duration_ms = (perf_counter() - started_at) * 1000

            logger.info(
                "request_completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            request_id_var.reset(token)
