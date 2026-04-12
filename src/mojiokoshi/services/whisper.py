"""Transcription service wrapping faster-whisper."""

from __future__ import annotations

import logging
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Any, Protocol

import deal

from mojiokoshi.models import Segment, TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperModelProtocol(Protocol):  # pragma: no cover
    """Protocol for faster-whisper WhisperModel."""

    def transcribe(
        self, audio: str, **kwargs: Any
    ) -> tuple[Iterable[Any], Any]: ...


class TranscriptionError(Exception):
    """Raised when transcription fails."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class TranscriptionService:
    """Service for transcribing audio files using a whisper model."""

    @deal.pre(lambda self, model: model is not None, message="model must not be None")
    def __init__(self, model: WhisperModelProtocol) -> None:
        self._model = model

    @deal.pre(
        lambda self, audio_path, language: Path(audio_path).exists(),
        message="audio file must exist",
    )
    @deal.pre(
        lambda self, audio_path, language: len(language) > 0,
        message="language must not be empty",
    )
    def transcribe(self, audio_path: str, language: str) -> TranscriptionResult:
        """Transcribe an audio file and return the complete result."""
        effective_language = None if language == "auto" else language
        logger.info("Starting transcription: %s (language=%s)", audio_path, language)

        try:
            segments_iter, info = self._model.transcribe(
                audio_path, language=effective_language, beam_size=5
            )
        except RuntimeError as e:
            logger.error("Model transcription failed for %s: %s", audio_path, e)
            raise TranscriptionError(
                f"Transcription engine error: {type(e).__name__}", cause=e
            ) from e
        except FileNotFoundError as e:
            logger.error("Audio file not found: %s", audio_path)
            raise TranscriptionError("Audio file not found", cause=e) from e
        except Exception as e:
            logger.error("Unexpected error during transcription of %s: %s", audio_path, e)
            raise TranscriptionError(
                f"Unexpected transcription error: {type(e).__name__}", cause=e
            ) from e

        segments: list[Segment] = []
        text_parts: list[str] = []

        for seg in segments_iter:
            segments.append(
                Segment(id=seg.id, start=seg.start, end=seg.end, text=seg.text)
            )
            text_parts.append(seg.text)

        logger.info(
            "Transcription complete: %d segments, %.1fs duration",
            len(segments),
            info.duration,
        )

        return TranscriptionResult(
            text="\n".join(text_parts),
            language=info.language,
            segments=segments,
            duration_seconds=info.duration,
        )

    @deal.pre(
        lambda self, audio_path, language: Path(audio_path).exists(),
        message="audio file must exist",
    )
    @deal.pre(
        lambda self, audio_path, language: len(language) > 0,
        message="language must not be empty",
    )
    def transcribe_stream(
        self, audio_path: str, language: str
    ) -> Generator[Segment, None, None]:
        """Yield segments one by one for real-time streaming."""
        effective_language = None if language == "auto" else language
        logger.info("Starting streaming transcription: %s (language=%s)", audio_path, language)

        try:
            segments_iter, _info = self._model.transcribe(
                audio_path, language=effective_language, beam_size=5
            )
        except RuntimeError as e:
            logger.error("Model transcription failed for %s: %s", audio_path, e)
            raise TranscriptionError(
                f"Transcription engine error: {type(e).__name__}", cause=e
            ) from e
        except FileNotFoundError as e:
            logger.error("Audio file not found: %s", audio_path)
            raise TranscriptionError("Audio file not found", cause=e) from e
        except Exception as e:
            logger.error("Unexpected error during transcription of %s: %s", audio_path, e)
            raise TranscriptionError(
                f"Unexpected transcription error: {type(e).__name__}", cause=e
            ) from e

        for seg in segments_iter:
            yield Segment(id=seg.id, start=seg.start, end=seg.end, text=seg.text)

    @deal.pre(
        lambda self, audio_path, language: Path(audio_path).exists(),
        message="audio file must exist",
    )
    @deal.pre(
        lambda self, audio_path, language: len(language) > 0,
        message="language must not be empty",
    )
    def transcribe_stream_with_info(
        self, audio_path: str, language: str
    ) -> tuple[float, Generator[Segment, None, None]]:
        """Return (audio_duration, segment_generator) for progress tracking."""
        effective_language = None if language == "auto" else language
        logger.info("Starting streaming transcription: %s (language=%s)", audio_path, language)

        try:
            segments_iter, info = self._model.transcribe(
                audio_path, language=effective_language, beam_size=5
            )
        except RuntimeError as e:
            logger.error("Model transcription failed for %s: %s", audio_path, e)
            raise TranscriptionError(
                f"Transcription engine error: {type(e).__name__}", cause=e
            ) from e
        except FileNotFoundError as e:
            logger.error("Audio file not found: %s", audio_path)
            raise TranscriptionError("Audio file not found", cause=e) from e
        except Exception as e:
            logger.error("Unexpected error during transcription of %s: %s", audio_path, e)
            raise TranscriptionError(
                f"Unexpected transcription error: {type(e).__name__}", cause=e
            ) from e

        def segment_generator() -> Generator[Segment, None, None]:
            for seg in segments_iter:
                yield Segment(id=seg.id, start=seg.start, end=seg.end, text=seg.text)

        return info.duration, segment_generator()
