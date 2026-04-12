"""Shared test fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class FakeSegment:
    """Mimics faster_whisper segment namedtuple."""

    id: int
    start: float
    end: float
    text: str
    seek: int = 0
    tokens: list[int] | None = None
    temperature: float = 0.0
    avg_logprob: float = 0.0
    compression_ratio: float = 0.0
    no_speech_prob: float = 0.0
    words: list[Any] | None = None


@dataclass
class FakeTranscriptionInfo:
    """Mimics faster_whisper TranscriptionInfo."""

    language: str = "ja"
    language_probability: float = 0.98
    duration: float = 10.0
    duration_after_vad: float = 10.0
    all_language_probs: list[tuple[str, float]] | None = None
    transcription_options: Any = None
    vad_options: Any = None


class FakeWhisperModel:
    """Fake WhisperModel satisfying WhisperModelProtocol."""

    def __init__(
        self,
        segments: list[FakeSegment] | None = None,
        info: FakeTranscriptionInfo | None = None,
        *,
        raise_on_transcribe: Exception | None = None,
    ):
        self._segments = segments or []
        self._info = info or FakeTranscriptionInfo()
        self._raise_on_transcribe = raise_on_transcribe
        self.transcribe_call_count = 0
        self.last_transcribe_kwargs: dict[str, Any] = {}

    def transcribe(
        self, audio: str, **kwargs: Any
    ) -> tuple[Any, FakeTranscriptionInfo]:
        self.transcribe_call_count += 1
        self.last_transcribe_kwargs = kwargs
        if self._raise_on_transcribe:
            raise self._raise_on_transcribe
        return iter(self._segments), self._info


@pytest.fixture
def fake_segments() -> list[FakeSegment]:
    return [
        FakeSegment(id=0, start=0.0, end=3.2, text="こんにちは"),
        FakeSegment(id=1, start=3.2, end=6.8, text="今日はいい天気ですね"),
    ]


@pytest.fixture
def fake_info() -> FakeTranscriptionInfo:
    return FakeTranscriptionInfo(language="ja", duration=6.8)


@pytest.fixture
def fake_model(
    fake_segments: list[FakeSegment], fake_info: FakeTranscriptionInfo
) -> FakeWhisperModel:
    return FakeWhisperModel(segments=fake_segments, info=fake_info)
