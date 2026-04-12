"""Unit tests for StartupManager."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from mojiokoshi.main import create_app
from mojiokoshi.services.startup import StartupManager, StartupState
from mojiokoshi.services.whisper import TranscriptionService

from ..conftest import FakeWhisperModel


class TestStartupManagerStates:
    def test_initial_state_is_starting(self):
        manager = StartupManager()
        assert manager.state == StartupState.STARTING
        assert manager.service is None

    def test_get_status_initial(self):
        manager = StartupManager()
        status = manager.get_status()
        assert status["state"] == "starting"
        assert status["ready"] is False
        assert status["error"] is None

    def test_set_state_updates_state_and_message(self):
        manager = StartupManager()
        manager._set_state(StartupState.DOWNLOADING, "Downloading...")
        assert manager.state == StartupState.DOWNLOADING
        status = manager.get_status()
        assert status["message"] == "Downloading..."

    def test_load_model_success(self):
        manager = StartupManager()
        fake_model = FakeWhisperModel()

        # Override the download and create methods
        manager._download_model = MagicMock(return_value="/fake/path")
        manager._create_model = MagicMock(return_value=fake_model)

        manager.load_model("small", "cpu", "int8")

        assert manager.state == StartupState.READY
        assert manager.service is not None
        assert isinstance(manager.service, TranscriptionService)
        status = manager.get_status()
        assert status["ready"] is True
        assert status["error"] is None

    def test_load_model_download_failure(self):
        manager = StartupManager()
        manager._download_model = MagicMock(side_effect=RuntimeError("Network error"))

        manager.load_model("small", "cpu", "int8")

        assert manager.state == StartupState.ERROR
        assert manager.service is None
        status = manager.get_status()
        assert status["ready"] is False
        assert "Network error" in status["error"]
        assert "RuntimeError" in status["message"]

    def test_load_model_create_failure(self):
        manager = StartupManager()
        manager._download_model = MagicMock(return_value="/fake/path")
        manager._create_model = MagicMock(side_effect=RuntimeError("CUDA out of memory"))

        manager.load_model("large-v3", "cuda", "float16")

        assert manager.state == StartupState.ERROR
        assert "CUDA out of memory" in manager.get_status()["error"]

    def test_load_model_goes_through_all_states(self):
        """Verify state transitions: starting -> downloading -> loading -> ready."""
        manager = StartupManager()
        states_seen: list[str] = []

        original_set_state = manager._set_state

        def track_state(state, message):
            states_seen.append(state.value)
            original_set_state(state, message)

        manager._set_state = track_state
        manager._download_model = MagicMock(return_value="/fake/path")
        manager._create_model = MagicMock(return_value=FakeWhisperModel())

        manager.load_model("small", "cpu", "int8")

        assert "downloading" in states_seen
        assert "loading" in states_seen
        assert manager.state == StartupState.READY


class TestStatusEndpoint:
    def test_status_without_manager_returns_ready(self):
        """When no startup manager (test mode), status is always ready."""
        app = create_app(transcription_service=None)
        client = TestClient(app)
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "ready"
        assert data["ready"] is True

    def test_status_with_manager_starting(self):
        manager = StartupManager()
        app = create_app(startup_manager=manager)
        client = TestClient(app)
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "starting"
        assert data["ready"] is False

    def test_status_with_manager_ready(self):
        manager = StartupManager()
        manager._download_model = MagicMock(return_value="/fake/path")
        manager._create_model = MagicMock(return_value=FakeWhisperModel())
        manager.load_model("small", "cpu", "int8")

        app = create_app(startup_manager=manager)
        client = TestClient(app)
        resp = client.get("/api/status")
        data = resp.json()
        assert data["state"] == "ready"
        assert data["ready"] is True

    def test_status_with_manager_error(self):
        manager = StartupManager()
        manager._download_model = MagicMock(side_effect=RuntimeError("Download failed"))
        manager.load_model("small", "cpu", "int8")

        app = create_app(startup_manager=manager)
        client = TestClient(app)
        resp = client.get("/api/status")
        data = resp.json()
        assert data["state"] == "error"
        assert data["ready"] is False
        assert "Download failed" in data["error"]


class TestWebSocketWithManager:
    def test_websocket_model_not_loaded_yet(self):
        """When manager has no service yet, WebSocket returns error."""
        from io import BytesIO

        manager = StartupManager()
        app = create_app(startup_manager=manager)
        client = TestClient(app)

        # Upload a file
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
                    "language": "ja",
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "still loading" in msg["message"]
