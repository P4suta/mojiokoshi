"""Property-based tests for TranscriptionService."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from mojiokoshi.models import Segment
from mojiokoshi.services.whisper import TranscriptionService

from ..conftest import FakeSegment, FakeTranscriptionInfo, FakeWhisperModel


def make_fake_segments(n: int) -> list[FakeSegment]:
    """Create n fake segments with sequential timing."""
    return [
        FakeSegment(id=i, start=float(i), end=float(i + 1), text=f"segment {i}")
        for i in range(n)
    ]


def _write_temp_audio() -> str:
    """Create a temporary audio file and return its path."""
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    f.write(b"fake audio data")
    f.close()
    return f.name


@pytest.mark.property
class TestTranscriptionServiceProperties:
    @given(n_segments=st.integers(min_value=0, max_value=50))
    @settings(max_examples=30)
    def test_result_segment_count_matches_model_output(self, n_segments: int):
        """The result always has the same number of segments as the model yields."""
        segments = make_fake_segments(n_segments)
        model = FakeWhisperModel(
            segments=segments,
            info=FakeTranscriptionInfo(duration=float(n_segments)),
        )
        audio_path = _write_temp_audio()

        service = TranscriptionService(model=model)
        result = service.transcribe(audio_path, language="ja")

        assert len(result.segments) == n_segments
        Path(audio_path).unlink(missing_ok=True)

    @given(n_segments=st.integers(min_value=0, max_value=50))
    @settings(max_examples=30)
    def test_stream_yields_same_count_as_model(self, n_segments: int):
        """Streaming yields exactly as many segments as the model produces."""
        segments = make_fake_segments(n_segments)
        model = FakeWhisperModel(
            segments=segments,
            info=FakeTranscriptionInfo(duration=float(n_segments)),
        )
        audio_path = _write_temp_audio()

        service = TranscriptionService(model=model)
        streamed = list(service.transcribe_stream(audio_path, language="ja"))

        assert len(streamed) == n_segments
        Path(audio_path).unlink(missing_ok=True)

    @given(
        texts=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10),
    )
    @settings(max_examples=30)
    def test_full_text_is_newline_joined_segments(self, texts: list[str]):
        """The result text is always the newline-joined segment texts."""
        segments = [
            FakeSegment(id=i, start=float(i), end=float(i + 1), text=t)
            for i, t in enumerate(texts)
        ]
        model = FakeWhisperModel(
            segments=segments,
            info=FakeTranscriptionInfo(duration=float(len(texts))),
        )
        audio_path = _write_temp_audio()

        service = TranscriptionService(model=model)
        result = service.transcribe(audio_path, language="ja")

        assert result.text == "\n".join(texts)
        Path(audio_path).unlink(missing_ok=True)

    @given(
        language=st.sampled_from(["ja", "en", "zh", "ko", "de", "fr"]),
    )
    @settings(max_examples=10)
    def test_language_passed_through(self, language: str):
        """Non-auto languages are passed directly to the model."""
        model = FakeWhisperModel()
        audio_path = _write_temp_audio()

        service = TranscriptionService(model=model)
        service.transcribe(audio_path, language=language)

        assert model.last_transcribe_kwargs["language"] == language
        Path(audio_path).unlink(missing_ok=True)
