import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

logger = logging.getLogger("scheduling.requests")


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id, started, status = str(uuid4()), perf_counter(), 500

        async def wrapped_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            route = scope.get("route")
            logger.info(
                json.dumps(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "request_id": request_id,
                        "method": scope["method"],
                        "route": getattr(route, "path", "unmatched"),
                        "status": status,
                        "duration_ms": round((perf_counter() - started) * 1000, 3),
                    }
                )
            )
