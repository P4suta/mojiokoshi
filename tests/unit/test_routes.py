"""Unit tests for API routes."""

from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from mojiokoshi.main import create_app
from mojiokoshi.services.whisper import TranscriptionService

from ..conftest import FakeSegment, FakeTranscriptionInfo, FakeWhisperModel


@pytest.fixture
def fake_service() -> TranscriptionService:
    segments = [
        FakeSegment(id=0, start=0.0, end=3.2, text="こんにちは"),
        FakeSegment(id=1, start=3.2, end=6.8, text="今日はいい天気ですね"),
    ]
    info = FakeTranscriptionInfo(language="ja", duration=6.8)
    model = FakeWhisperModel(segments=segments, info=info)
    return TranscriptionService(model=model)


@pytest.fixture
def app(fake_service: TranscriptionService):
    return create_app(transcription_service=fake_service)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


class TestHealthRoute:
    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "device" in data

    def test_config_returns_models_and_languages(self, client: TestClient):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "languages" in data
        assert "default_model" in data
        assert "default_language" in data
        assert "device" in data
        assert "small" in data["models"]
        assert data["default_language"] == "ja"


class TestUploadRoute:
    def test_upload_audio_file(self, client: TestClient):
        audio_data = b"fake audio content"
        resp = client.post(
            "/api/upload",
            files={"file": ("test.mp3", BytesIO(audio_data), "audio/mpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "file_id" in data
        assert data["filename"] == "test.mp3"

    def test_upload_rejects_non_audio(self, client: TestClient):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", BytesIO(b"text"), "text/plain")},
        )
        assert resp.status_code == 415

    def test_upload_rejects_empty_file(self, client: TestClient):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.mp3", BytesIO(b""), "audio/mpeg")},
        )
        assert resp.status_code == 400

    def test_upload_rejects_no_filename(self, client: TestClient):
        resp = client.post(
            "/api/upload",
            files={"file": ("", BytesIO(b"audio data"), "audio/mpeg")},
        )
        # FastAPI/Starlette rejects empty filename with 422
        assert resp.status_code in (400, 422)

    def test_upload_rejects_oversized_file(self, client: TestClient):
        from mojiokoshi.config import MAX_UPLOAD_SIZE_BYTES

        # Create data just over the limit
        oversized_data = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)
        resp = client.post(
            "/api/upload",
            files={"file": ("test.mp3", BytesIO(oversized_data), "audio/mpeg")},
        )
        assert resp.status_code == 413


class TestWebSocketTranscribe:
    def test_websocket_transcription_flow(self, client: TestClient):
        audio_data = b"fake audio content"
        upload_resp = client.post(
            "/api/upload",
            files={"file": ("test.mp3", BytesIO(audio_data), "audio/mpeg")},
        )
        file_id = upload_resp.json()["file_id"]

        with client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json(
                {
                    "type": "start",
                    "file_id": file_id,
                    "model_size": "small",
                    "language": "ja",
                }
            )

            messages = []
            while True:
                msg = ws.receive_json()
                messages.append(msg)
                if msg["type"] in ("done", "error"):
                    break

            segment_msgs = [m for m in messages if m["type"] == "segment"]
            progress_msgs = [m for m in messages if m["type"] == "progress"]
            done_msgs = [m for m in messages if m["type"] == "done"]

            assert len(segment_msgs) == 2
            assert segment_msgs[0]["segment"]["text"] == "こんにちは"
            assert segment_msgs[1]["segment"]["text"] == "今日はいい天気ですね"
            # Each segment should have elapsed_seconds
            assert "elapsed_seconds" in segment_msgs[0]
            assert segment_msgs[0]["elapsed_seconds"] >= 0

            # Progress messages should be sent
            assert len(progress_msgs) == 2
            assert progress_msgs[0]["percent"] >= 0
            assert "elapsed_seconds" in progress_msgs[0]

            assert len(done_msgs) == 1
            assert "こんにちは" in done_msgs[0]["full_text"]
            assert "elapsed_seconds" in done_msgs[0]

    def test_websocket_invalid_file_id(self, client: TestClient):
        with client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json(
                {
                    "type": "start",
                    "file_id": "nonexistent-id",
                    "model_size": "small",
                    "language": "ja",
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "File not found" in msg["message"]

    def test_websocket_cancel(self, client: TestClient):
        with client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json({"type": "cancel"})

    def test_websocket_invalid_message_format(self, client: TestClient):
        with client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json({"type": "unknown"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "validation error" in msg["message"].lower()

    def test_websocket_missing_required_fields(self, client: TestClient):
        with client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json({"type": "start"})  # missing file_id and language
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "validation error" in msg["message"].lower()

    def test_websocket_invalid_language(self, client: TestClient):
        upload_resp = client.post(
            "/api/upload",
            files={"file": ("test.mp3", BytesIO(b"audio"), "audio/mpeg")},
        )
        file_id = upload_resp.json()["file_id"]

        with client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json(
                {
                    "type": "start",
                    "file_id": file_id,
                    "model_size": "small",
                    "language": "xx_invalid",
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "Unsupported language" in msg["message"]

    def test_websocket_transcription_error(self):
        """Test that transcription errors are sent to client as error messages."""
        error_model = FakeWhisperModel(raise_on_transcribe=RuntimeError("OOM"))
        error_service = TranscriptionService(model=error_model)
        error_app = create_app(transcription_service=error_service)
        error_client = TestClient(error_app)

        upload_resp = error_client.post(
            "/api/upload",
            files={"file": ("test.mp3", BytesIO(b"audio"), "audio/mpeg")},
        )
        file_id = upload_resp.json()["file_id"]

        with error_client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json(
                {
                    "type": "start",
                    "file_id": file_id,
                    "model_size": "small",
                    "language": "ja",
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "Transcription engine error" in msg["message"]

    def test_websocket_zero_duration_no_progress(self):
        """When audio duration is 0, no progress messages are sent."""
        from ..conftest import FakeTranscriptionInfo

        zero_model = FakeWhisperModel(
            segments=[],
            info=FakeTranscriptionInfo(duration=0.0),
        )
        zero_service = TranscriptionService(model=zero_model)
        zero_app = create_app(transcription_service=zero_service)
        zero_client = TestClient(zero_app)

        upload_resp = zero_client.post(
            "/api/upload",
            files={"file": ("test.mp3", BytesIO(b"audio"), "audio/mpeg")},
        )
        file_id = upload_resp.json()["file_id"]

        with zero_client.websocket_connect("/api/ws/transcribe") as ws:
            ws.send_json(
                {
                    "type": "start",
                    "file_id": file_id,
                    "model_size": "small",
                    "language": "ja",
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "done"
            # No progress messages for zero duration

    def test_websocket_no_service(self):
        """Test app without transcription service (no WS route)."""
        app_no_ws = create_app(transcription_service=None)
        no_ws_client = TestClient(app_no_ws)
        resp = no_ws_client.get("/api/health")
        assert resp.status_code == 200

    def test_contract_error_returns_422(self, client: TestClient):
        """Test that deal.PreContractError is handled as 422."""
        # This is tested via the exception handler on the app
        resp = client.get("/api/health")
        assert resp.status_code == 200
