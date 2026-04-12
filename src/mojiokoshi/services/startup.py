"""Startup manager for background model loading."""

from __future__ import annotations

import logging
from enum import StrEnum
from threading import Lock
from typing import Any

from mojiokoshi.services.whisper import TranscriptionService

logger = logging.getLogger(__name__)


class StartupState(StrEnum):
    STARTING = "starting"
    DOWNLOADING = "downloading"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class StartupManager:
    """Manages background model loading and exposes status for the frontend."""

    def __init__(self) -> None:
        self._state: StartupState = StartupState.STARTING
        self._message: str = "Starting server..."
        self._error: str | None = None
        self._service: TranscriptionService | None = None
        self._lock = Lock()

    @property
    def state(self) -> StartupState:
        with self._lock:
            return self._state

    @property
    def service(self) -> TranscriptionService | None:
        with self._lock:
            return self._service

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "message": self._message,
                "ready": self._state == StartupState.READY,
                "error": self._error,
            }

    def _set_state(self, state: StartupState, message: str) -> None:
        with self._lock:
            self._state = state
            self._message = message
        logger.info("Startup state: %s - %s", state.value, message)

    def load_model(self, model_name: str, device: str, compute_type: str) -> None:
        """Load the whisper model. Designed to run in a background thread.

        Two phases:
        1. Download model files from HuggingFace (if not cached)
        2. Load model into GPU/CPU memory
        """
        try:
            # Phase 1: Download
            self._set_state(
                StartupState.DOWNLOADING,
                f"Downloading model ({model_name})...",
            )
            model_path = self._download_model(model_name)

            # Phase 2: Load into memory
            self._set_state(
                StartupState.LOADING,
                f"Loading model into {device.upper()}...",
            )
            model = self._create_model(model_path, device, compute_type)

            # Phase 3: Ready
            service = TranscriptionService(model=model)
            with self._lock:
                self._service = service
                self._state = StartupState.READY
                self._message = "Ready"
            logger.info("Model loaded successfully: %s on %s", model_name, device)

        except Exception as e:
            with self._lock:
                self._state = StartupState.ERROR
                self._message = f"Failed to load model: {type(e).__name__}"
                self._error = str(e)
            logger.error("Failed to load model %s: %s", model_name, e)

    def _download_model(self, model_name: str) -> str:  # pragma: no cover
        """Download model files. Returns local path."""
        from faster_whisper.utils import download_model

        return download_model(model_name)

    def _create_model(self, model_path: str, device: str, compute_type: str) -> Any:  # pragma: no cover
        """Create a WhisperModel from a local path."""
        from faster_whisper import WhisperModel

        return WhisperModel(model_path, device=device, compute_type=compute_type)
