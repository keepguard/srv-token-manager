"""Correlation ID middleware for HTTP requests."""

import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_HEADER = "X-Correlation-ID"
SKIP_PREFIXES = ("/health", "/metrics")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path.startswith(SKIP_PREFIXES):
            return await call_next(request)

        correlation_id = (request.headers.get(CORRELATION_HEADER) or "").strip()
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(correlationId=correlation_id)
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("correlationId")

        response.headers[CORRELATION_HEADER] = correlation_id
        return response
