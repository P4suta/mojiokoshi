"""Upload and WebSocket transcription routes."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from mojiokoshi.config import (
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_AUDIO_EXTENSIONS,
    TRANSCRIPTION_TIMEOUT_SECONDS,
    VALID_LANGUAGE_CODES,
)
from mojiokoshi.models import Segment, UploadResponse, WsClientMessage, WsServerMessage
from mojiokoshi.services.whisper import TranscriptionError, TranscriptionService

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Thread-safe store for uploaded files (maps file_id -> temp file path)
_uploaded_files: dict[str, str] = {}
_uploaded_files_lock = Lock()


def _store_file(file_id: str, path: str) -> None:
    with _uploaded_files_lock:
        _uploaded_files[file_id] = path


def _pop_file(file_id: str) -> str | None:
    with _uploaded_files_lock:
        return _uploaded_files.pop(file_id, None)


def _get_file(file_id: str) -> str | None:
    with _uploaded_files_lock:
        return _uploaded_files.get(file_id)


@router.post("/upload")
async def upload_audio(file: UploadFile) -> UploadResponse:
    if not file.filename:  # pragma: no cover
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {ext}. Supported: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes. Maximum: {MAX_UPLOAD_SIZE_BYTES} bytes",
        )

    file_id = str(uuid.uuid4())

    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_name = tmp.name
    except OSError as e:  # pragma: no cover
        logger.exception("Failed to write temp file")
        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded file",
        ) from e

    _store_file(file_id, tmp_name)
    logger.info("File uploaded: %s (%s, %d bytes)", file.filename, file_id, len(content))

    return UploadResponse(file_id=file_id, filename=file.filename)


async def _send_error(websocket: WebSocket, message: str) -> None:
    """Send an error message to the WebSocket client."""
    try:
        await websocket.send_json(WsServerMessage(type="error", message=message).model_dump())
    except Exception:  # pragma: no cover
        logger.debug("Failed to send error message to WebSocket client")


def _create_ws_router(  # noqa: PLR0915
    service_getter: Callable[[], TranscriptionService | None],
) -> APIRouter:
    """Create a WebSocket router bound to a service getter function."""
    ws_router = APIRouter(prefix="/api")

    @ws_router.websocket("/ws/transcribe")
    async def websocket_transcribe(websocket: WebSocket) -> None:  # noqa: PLR0912, PLR0915
        await websocket.accept()
        logger.debug("WebSocket connection accepted")

        try:
            while True:
                raw_data = await websocket.receive_json()

                # Validate message through Pydantic
                try:
                    msg = WsClientMessage.model_validate(raw_data)
                except ValidationError as e:
                    logger.warning("Invalid WebSocket message: %s", e)
                    await _send_error(
                        websocket,
                        f"Invalid message format: {e.error_count()} validation error(s)",
                    )
                    continue

                if msg.type == "cancel":
                    logger.info("Transcription cancelled by client")
                    await websocket.close()
                    return

                # msg.type == "start" (guaranteed by Pydantic validation)
                file_id = msg.file_id
                language = msg.language
                assert file_id is not None  # guaranteed by model validator
                assert language is not None  # guaranteed by model validator

                # Validate language code
                if language not in VALID_LANGUAGE_CODES:
                    await _send_error(
                        websocket,
                        f"Unsupported language: {language}. Supported: {', '.join(sorted(VALID_LANGUAGE_CODES))}",
                    )
                    continue

                audio_path = _get_file(file_id)
                if audio_path is None:
                    await _send_error(websocket, f"File not found: {file_id}")
                    continue

                service = service_getter()
                if service is None:
                    await _send_error(websocket, "Model is still loading, please wait")
                    continue

                start_time = time.monotonic()

                try:

                    def _run_transcription(
                        service: TranscriptionService = service,
                        audio_path: str = audio_path,
                        language: str = language,
                    ) -> tuple[float, list[dict[str, Any]]]:
                        duration, seg_gen = service.transcribe_stream_with_info(
                            audio_path, language=language
                        )
                        segments = [seg.model_dump() for seg in seg_gen]
                        return duration, segments

                    duration, segments = await asyncio.wait_for(
                        asyncio.to_thread(_run_transcription),
                        timeout=TRANSCRIPTION_TIMEOUT_SECONDS,
                    )

                    text_parts: list[str] = []
                    for seg_data in segments:
                        elapsed = time.monotonic() - start_time

                        await websocket.send_json(
                            WsServerMessage(
                                type="segment",
                                segment=Segment(**seg_data),
                                elapsed_seconds=round(elapsed, 1),
                            ).model_dump()
                        )
                        text_parts.append(seg_data["text"])

                        # Send progress update
                        if duration > 0:  # pragma: no branch
                            percent = min(int(seg_data["end"] / duration * 100), 99)
                            await websocket.send_json(
                                WsServerMessage(
                                    type="progress",
                                    percent=percent,
                                    elapsed_seconds=round(elapsed, 1),
                                ).model_dump()
                            )

                    elapsed = time.monotonic() - start_time
                    full_text = "\n".join(text_parts)
                    await websocket.send_json(
                        WsServerMessage(
                            type="done",
                            full_text=full_text,
                            elapsed_seconds=round(elapsed, 1),
                        ).model_dump()
                    )
                    logger.info(
                        "Transcription done: %s (%d segments, %.1fs)",
                        file_id,
                        len(segments),
                        elapsed,
                    )

                except TimeoutError:  # pragma: no cover
                    logger.exception("Transcription timed out for file %s", file_id)
                    await _send_error(
                        websocket,
                        f"Transcription timed out after {TRANSCRIPTION_TIMEOUT_SECONDS}s",
                    )

                except TranscriptionError as e:
                    logger.exception("Transcription error for %s", file_id)
                    await _send_error(websocket, str(e))

                except OSError:  # pragma: no cover
                    logger.exception("I/O error during transcription of %s", file_id)
                    await _send_error(websocket, "File I/O error during transcription")

                except Exception:  # pragma: no cover
                    logger.exception("Unexpected error during transcription of %s", file_id)
                    await _send_error(websocket, "Internal server error")

                finally:
                    # Clean up temp file
                    removed_path = _pop_file(file_id)
                    if removed_path is not None:  # pragma: no branch
                        try:
                            await asyncio.to_thread(Path(removed_path).unlink, missing_ok=True)
                        except OSError:  # pragma: no cover
                            logger.warning("Failed to delete temp file: %s", removed_path)

        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected")

    return ws_router
