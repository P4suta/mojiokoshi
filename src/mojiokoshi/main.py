"""FastAPI application factory and entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import deal
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from mojiokoshi.routes.health import router as health_router
from mojiokoshi.routes.transcribe import _create_ws_router, router as upload_router
from mojiokoshi.services.startup import StartupManager
from mojiokoshi.services.whisper import TranscriptionService

logger = logging.getLogger(__name__)

FRONTEND_BUILD_DIR = Path(__file__).parent.parent.parent / "frontend" / "build"


def create_app(
    transcription_service: TranscriptionService | None = None,
    startup_manager: StartupManager | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Mojiokoshi", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(deal.PreContractError)
    async def handle_pre_contract_error(  # pragma: no cover
        request: Request, exc: deal.PreContractError
    ) -> JSONResponse:
        logger.warning("Contract violation: %s", exc)
        return JSONResponse(
            status_code=422,
            content={"detail": f"Validation error: {exc}"},
        )

    if startup_manager is not None:
        app.state.startup_manager = startup_manager

    app.include_router(health_router)
    app.include_router(upload_router)

    if transcription_service is not None:
        # Direct service injection (used in tests)
        ws_router = _create_ws_router(lambda: transcription_service)
        app.include_router(ws_router)
    elif startup_manager is not None:
        # Lazy service from startup manager (used in production)
        ws_router = _create_ws_router(lambda: startup_manager.service)
        app.include_router(ws_router)

    if FRONTEND_BUILD_DIR.exists():  # pragma: no cover
        app.mount(
            "/",
            StaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True),
            name="frontend",
        )

    return app


def cli() -> None:  # pragma: no cover
    """CLI entry point to run the server."""
    import threading
    import webbrowser

    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from mojiokoshi.config import DEFAULT_MODEL, detect_device, get_compute_type

    device = detect_device()
    compute_type = get_compute_type(device)

    logger.info("Device: %s, Compute type: %s", device, compute_type)

    manager = StartupManager()
    app = create_app(startup_manager=manager)

    # Start model loading in background thread
    thread = threading.Thread(
        target=manager.load_model,
        args=(DEFAULT_MODEL, device, compute_type),
        daemon=True,
    )
    thread.start()

    webbrowser.open("http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
