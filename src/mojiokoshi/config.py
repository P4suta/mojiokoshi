"""Application configuration."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MODEL_SIZES: list[str] = ["tiny", "base", "small", "medium", "large-v3"]
DEFAULT_MODEL: str = "large-v3"

LANGUAGES: dict[str, str] = {
    "Japanese": "ja",
    "English": "en",
    "Chinese": "zh",
    "Korean": "ko",
    "Auto-detect": "auto",
}
VALID_LANGUAGE_CODES: set[str] = set(LANGUAGES.values())
DEFAULT_LANGUAGE: str = "ja"

SUPPORTED_AUDIO_EXTENSIONS: set[str] = {
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".flac",
    ".webm",
    ".wma",
    ".aac",
}

MAX_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024  # 500MB

TRANSCRIPTION_TIMEOUT_SECONDS: int = 1800  # 30 minutes


def detect_device() -> str:  # pragma: no cover
    """Detect whether CUDA is available, returning 'cuda' or 'cpu'."""
    try:
        import ctranslate2

        supported = ctranslate2.get_supported_compute_types("cuda")
        if supported:
            logger.info("CUDA device detected")
            return "cuda"
    except ImportError:
        logger.warning("ctranslate2 not installed, falling back to CPU")
    except RuntimeError as e:
        logger.warning("CUDA detection failed: %s", e)
    return "cpu"


def get_compute_type(device: str) -> str:  # pragma: no cover
    """Return the optimal compute type for the given device."""
    if device == "cuda":
        return "float16"
    return "int8"
