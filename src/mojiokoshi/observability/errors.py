"""FastAPI exception handlers that return RFC 7807 Problem Details payloads.

Every response carries a ``trace_id`` (taken from the ``X-Request-ID`` header
populated by :class:`asgi_correlation_id.CorrelationIdMiddleware`, or freshly
generated), and every handler emits a structured log event so diagnosis starts
from the log collector rather than a traceback fished out of stderr.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import deal
import structlog
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

log = structlog.get_logger(__name__)

_PROBLEM_TYPE_PREFIX = "https://errors.mojiokoshi/"


def _trace_id_from(request: Request) -> str:
    """Return the request's ``X-Request-ID`` or a fresh UUID4."""
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _problem(*, status: int, title: str, detail: Any, trace_id: str) -> JSONResponse:
    body = {
        "type": f"{_PROBLEM_TYPE_PREFIX}{status}",
        "title": title,
        "status": status,
        "detail": detail,
        "trace_id": trace_id,
    }
    return JSONResponse(
        status_code=status,
        content=body,
        headers={"X-Request-ID": trace_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all observability-backed exception handlers on ``app``."""

    @app.exception_handler(RequestValidationError)
    async def _on_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = _trace_id_from(request)
        # jsonable_encoder flattens ``ctx`` values that are exception instances
        # (pydantic v2 can stash a ``ValueError`` there) into JSON-safe strings.
        errors = jsonable_encoder(exc.errors())
        log.warning(
            "request_validation_failed",
            path=request.url.path,
            method=request.method,
            errors=errors,
            trace_id=trace_id,
        )
        return _problem(
            status=422,
            title="Validation failed",
            detail=errors,
            trace_id=trace_id,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _on_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        trace_id = _trace_id_from(request)
        log.info(
            "http_exception",
            path=request.url.path,
            status=exc.status_code,
            detail=exc.detail,
            trace_id=trace_id,
        )
        return _problem(
            status=exc.status_code,
            title="HTTP error",
            detail=exc.detail,
            trace_id=trace_id,
        )

    @app.exception_handler(deal.PreContractError)
    async def _on_pre_contract(request: Request, exc: deal.PreContractError) -> JSONResponse:
        trace_id = _trace_id_from(request)
        log.warning(
            "contract_precondition_failed",
            path=request.url.path,
            error=str(exc),
            trace_id=trace_id,
        )
        return _problem(
            status=422,
            title="Precondition violation",
            detail=str(exc),
            trace_id=trace_id,
        )

    @app.exception_handler(deal.PostContractError)
    async def _on_post_contract(  # pragma: no cover
        request: Request, exc: deal.PostContractError
    ) -> JSONResponse:
        trace_id = _trace_id_from(request)
        log.error(
            "contract_postcondition_failed",
            path=request.url.path,
            error=str(exc),
            trace_id=trace_id,
            exc_info=True,
        )
        return _problem(
            status=500,
            title="Internal invariant violation",
            detail=None,
            trace_id=trace_id,
        )

    @app.exception_handler(Exception)
    async def _on_unhandled(request: Request, exc: Exception) -> JSONResponse:
        trace_id = _trace_id_from(request)
        log.exception(
            "unhandled_exception",
            path=request.url.path,
            exc_type=type(exc).__name__,
            trace_id=trace_id,
        )
        return _problem(
            status=500,
            title="Internal server error",
            detail=None,
            trace_id=trace_id,
        )
