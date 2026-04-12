"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from mojiokoshi.models import (
    ConfigResponse,
    ErrorMessage,
    Segment,
    TranscriptionResult,
    UploadResponse,
    WsClientMessage,
    WsServerMessage,
)


class TestSegment:
    def test_valid_segment(self):
        seg = Segment(id=0, start=0.0, end=3.2, text="こんにちは")
        assert seg.id == 0
        assert seg.start == 0.0
        assert seg.end == 3.2
        assert seg.text == "こんにちは"

    def test_start_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            Segment(id=0, start=-1.0, end=3.0, text="test")

    def test_end_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            Segment(id=0, start=0.0, end=-1.0, text="test")

    def test_id_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            Segment(id=-1, start=0.0, end=3.0, text="test")

    def test_empty_text_is_valid(self):
        seg = Segment(id=0, start=0.0, end=1.0, text="")
        assert seg.text == ""


class TestTranscriptionResult:
    def test_valid_result(self):
        result = TranscriptionResult(
            text="こんにちは\n今日はいい天気ですね",
            language="ja",
            segments=[
                Segment(id=0, start=0.0, end=3.2, text="こんにちは"),
                Segment(id=1, start=3.2, end=6.8, text="今日はいい天気ですね"),
            ],
            duration_seconds=6.8,
        )
        assert result.text == "こんにちは\n今日はいい天気ですね"
        assert len(result.segments) == 2

    def test_duration_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            TranscriptionResult(text="test", language="ja", segments=[], duration_seconds=-1.0)

    def test_language_min_length(self):
        with pytest.raises(ValidationError):
            TranscriptionResult(text="test", language="", segments=[], duration_seconds=1.0)

    def test_language_max_length(self):
        with pytest.raises(ValidationError):
            TranscriptionResult(text="test", language="toolong", segments=[], duration_seconds=1.0)

    def test_empty_segments_is_valid(self):
        result = TranscriptionResult(text="", language="ja", segments=[], duration_seconds=0.0)
        assert result.segments == []


class TestUploadResponse:
    def test_valid_upload_response(self):
        resp = UploadResponse(file_id="abc-123", filename="test.mp3")
        assert resp.file_id == "abc-123"
        assert resp.filename == "test.mp3"

    def test_file_id_must_not_be_empty(self):
        with pytest.raises(ValidationError):
            UploadResponse(file_id="", filename="test.mp3")


class TestWsClientMessage:
    def test_start_message(self):
        msg = WsClientMessage(type="start", file_id="abc-123", model_size="small", language="ja")
        assert msg.type == "start"

    def test_cancel_message(self):
        msg = WsClientMessage(type="cancel")
        assert msg.type == "cancel"

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            WsClientMessage(type="invalid")

    def test_start_requires_file_id(self):
        with pytest.raises(ValidationError):
            WsClientMessage(type="start", model_size="small", language="ja")

    def test_start_requires_language(self):
        with pytest.raises(ValidationError):
            WsClientMessage(type="start", file_id="abc-123", model_size="small")


class TestWsServerMessage:
    def test_segment_message(self):
        msg = WsServerMessage(
            type="segment",
            segment=Segment(id=0, start=0.0, end=3.0, text="test"),
        )
        assert msg.type == "segment"

    def test_progress_message(self):
        msg = WsServerMessage(type="progress", percent=45, elapsed_seconds=2.5)
        assert msg.percent == 45
        assert msg.elapsed_seconds == 2.5

    def test_done_message(self):
        msg = WsServerMessage(type="done", full_text="result text", elapsed_seconds=8.3)
        assert msg.full_text == "result text"
        assert msg.elapsed_seconds == 8.3

    def test_error_message(self):
        msg = WsServerMessage(type="error", message="something went wrong")
        assert msg.message == "something went wrong"


class TestErrorMessage:
    def test_error_message(self):
        err = ErrorMessage(message="not found")
        assert err.message == "not found"


class TestConfigResponse:
    def test_valid_config(self):
        config = ConfigResponse(
            models=["tiny", "small"],
            languages={"Japanese": "ja", "English": "en"},
            default_model="small",
            default_language="ja",
            device="cuda",
        )
        assert config.device == "cuda"
        assert config.default_model == "small"
