"""Health, config, and status routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from mojiokoshi.config import (
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    LANGUAGES,
    MODEL_SIZES,
    detect_device,
)
from mojiokoshi.models import ConfigResponse, StatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Cache device detection result (expensive operation)
_cached_device: str | None = None


def _get_device() -> str:
    global _cached_device  # noqa: PLW0603
    if _cached_device is None:
        _cached_device = detect_device()
        logger.info("Device detected: %s", _cached_device)
    return _cached_device


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "device": _get_device()}


@router.get("/config")
async def config() -> ConfigResponse:
    return ConfigResponse(
        models=MODEL_SIZES,
        languages=LANGUAGES,
        default_model=DEFAULT_MODEL,
        default_language=DEFAULT_LANGUAGE,
        device=_get_device(),
    )


@router.get("/status")
async def status(request: Request) -> StatusResponse:
    manager = getattr(request.app.state, "startup_manager", None)
    if manager is None:
        return StatusResponse(state="ready", message="Ready", ready=True)
    return StatusResponse(**manager.get_status())
