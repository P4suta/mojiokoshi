"""Unit tests for TranscriptionService."""

from __future__ import annotations

from pathlib import Path

import deal
import pytest

from mojiokoshi.models import Segment, TranscriptionResult
from mojiokoshi.services.whisper import TranscriptionError, TranscriptionService

from ..conftest import FakeTranscriptionInfo, FakeWhisperModel


class TestTranscriptionServiceInit:
    def test_creates_with_model(self, fake_model: FakeWhisperModel):
        service = TranscriptionService(model=fake_model)
        assert service._model is fake_model

    def test_rejects_none_model(self):
        with pytest.raises(deal.PreContractError):
            TranscriptionService(model=None)  # type: ignore[arg-type]


class TestTranscriptionServiceTranscribe:
    def test_transcribes_audio_file(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        result = service.transcribe(str(audio_file), language="ja")

        assert isinstance(result, TranscriptionResult)
        assert result.language == "ja"
        assert result.text == "こんにちは\n今日はいい天気ですね"
        assert len(result.segments) == 2
        assert result.duration_seconds == 6.8

    def test_passes_language_to_model(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        service.transcribe(str(audio_file), language="en")

        assert fake_model.last_transcribe_kwargs["language"] == "en"

    def test_auto_language_passes_none(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        service.transcribe(str(audio_file), language="auto")

        assert fake_model.last_transcribe_kwargs["language"] is None

    def test_rejects_nonexistent_file(self, fake_model: FakeWhisperModel):
        service = TranscriptionService(model=fake_model)
        with pytest.raises(deal.PreContractError):
            service.transcribe("/nonexistent/path.wav", language="ja")

    def test_rejects_empty_language(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        with pytest.raises(deal.PreContractError):
            service.transcribe(str(audio_file), language="")

    def test_empty_segments_returns_empty_text(self, tmp_path: Path):
        model = FakeWhisperModel(
            segments=[],
            info=FakeTranscriptionInfo(language="ja", duration=0.0),
        )
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        result = service.transcribe(str(audio_file), language="ja")

        assert result.text == ""
        assert result.segments == []

    def test_runtime_error_wrapped_as_transcription_error(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=RuntimeError("OOM"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Transcription engine error"):
            service.transcribe(str(audio_file), language="ja")

    def test_file_not_found_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=FileNotFoundError("missing"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Audio file not found"):
            service.transcribe(str(audio_file), language="ja")

    def test_unexpected_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=ValueError("bad value"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Unexpected transcription error"):
            service.transcribe(str(audio_file), language="ja")

    def test_transcription_error_preserves_cause(self, tmp_path: Path):
        original = RuntimeError("OOM")
        model = FakeWhisperModel(raise_on_transcribe=original)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError) as exc_info:
            service.transcribe(str(audio_file), language="ja")
        assert exc_info.value.cause is original

    def test_beam_size_passed_to_model(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        service.transcribe(str(audio_file), language="ja")

        assert fake_model.last_transcribe_kwargs["beam_size"] == 5


class TestTranscriptionServiceTranscribeStream:
    def test_yields_segments_incrementally(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        segments = list(service.transcribe_stream(str(audio_file), language="ja"))

        assert len(segments) == 2
        assert isinstance(segments[0], Segment)
        assert segments[0].text == "こんにちは"
        assert segments[1].text == "今日はいい天気ですね"

    def test_stream_rejects_nonexistent_file(self, fake_model: FakeWhisperModel):
        service = TranscriptionService(model=fake_model)
        with pytest.raises(deal.PreContractError):
            list(service.transcribe_stream("/nonexistent.wav", language="ja"))

    def test_stream_with_empty_segments(self, tmp_path: Path):
        model = FakeWhisperModel(segments=[], info=FakeTranscriptionInfo())
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        segments = list(service.transcribe_stream(str(audio_file), language="ja"))
        assert segments == []

    def test_stream_auto_language(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        list(service.transcribe_stream(str(audio_file), language="auto"))

        assert fake_model.last_transcribe_kwargs["language"] is None

    def test_stream_runtime_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=RuntimeError("GPU error"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Transcription engine error"):
            list(service.transcribe_stream(str(audio_file), language="ja"))

    def test_stream_unexpected_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=TypeError("bad"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Unexpected transcription error"):
            list(service.transcribe_stream(str(audio_file), language="ja"))

    def test_stream_file_not_found_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=FileNotFoundError("gone"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Audio file not found"):
            list(service.transcribe_stream(str(audio_file), language="ja"))


class TestTranscriptionServiceStreamWithInfo:
    def test_returns_duration_and_segments(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        service = TranscriptionService(model=fake_model)
        duration, seg_gen = service.transcribe_stream_with_info(str(audio_file), language="ja")

        assert duration == 6.8
        segments = list(seg_gen)
        assert len(segments) == 2
        assert segments[0].text == "こんにちは"

    def test_empty_segments_returns_zero_duration(self, tmp_path: Path):
        model = FakeWhisperModel(
            segments=[],
            info=FakeTranscriptionInfo(duration=0.0),
        )
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        service = TranscriptionService(model=model)
        duration, seg_gen = service.transcribe_stream_with_info(str(audio_file), language="ja")
        assert duration == 0.0
        assert list(seg_gen) == []

    def test_rejects_nonexistent_file(self, fake_model: FakeWhisperModel):
        service = TranscriptionService(model=fake_model)
        with pytest.raises(deal.PreContractError):
            service.transcribe_stream_with_info("/nonexistent.wav", language="ja")

    def test_rejects_empty_language(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        service = TranscriptionService(model=fake_model)
        with pytest.raises(deal.PreContractError):
            service.transcribe_stream_with_info(str(audio_file), language="")

    def test_runtime_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=RuntimeError("GPU"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Transcription engine error"):
            service.transcribe_stream_with_info(str(audio_file), language="ja")

    def test_auto_language(self, fake_model: FakeWhisperModel, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        service = TranscriptionService(model=fake_model)
        duration, seg_gen = service.transcribe_stream_with_info(str(audio_file), language="auto")
        list(seg_gen)
        assert fake_model.last_transcribe_kwargs["language"] is None

    def test_file_not_found_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=FileNotFoundError("gone"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Audio file not found"):
            service.transcribe_stream_with_info(str(audio_file), language="ja")

    def test_unexpected_error_wrapped(self, tmp_path: Path):
        model = FakeWhisperModel(raise_on_transcribe=TypeError("bad"))
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        service = TranscriptionService(model=model)
        with pytest.raises(TranscriptionError, match="Unexpected transcription error"):
            service.transcribe_stream_with_info(str(audio_file), language="ja")
