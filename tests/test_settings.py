"""Unit tests for :mod:`mojiokoshi.settings`."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from mojiokoshi.settings import Settings, get_settings

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Scrub MOJIOKOSHI_* from env and anchor CWD at an empty tmp dir."""
    for key in (
        "MOJIOKOSHI_LOG_FORMAT",
        "MOJIOKOSHI_LOG_LEVEL",
        "MOJIOKOSHI_HOST",
        "MOJIOKOSHI_PORT",
        "MOJIOKOSHI_DEFAULT_MODEL",
        "MOJIOKOSHI_SENTRY_DSN",
        "MOJIOKOSHI_SENTRY_TRACES_SAMPLE_RATE",
        "MOJIOKOSHI_OPEN_BROWSER",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


class TestDefaults:
    def test_defaults_are_reasonable(self):
        s = Settings()
        assert s.log_format == "console"
        assert s.log_level == "INFO"
        assert s.host == "0.0.0.0"
        assert s.port == 8000
        assert s.default_model == "large-v3"
        assert s.sentry_dsn is None
        assert s.sentry_traces_sample_rate == pytest.approx(0.1)
        assert s.open_browser is True

    def test_get_settings_returns_fresh_instance(self):
        a = get_settings()
        b = get_settings()
        assert a is not b
        assert a.port == b.port


class TestEnvLoading:
    def test_env_overrides_defaults(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MOJIOKOSHI_LOG_FORMAT", "json")
        monkeypatch.setenv("MOJIOKOSHI_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MOJIOKOSHI_HOST", "127.0.0.1")
        monkeypatch.setenv("MOJIOKOSHI_PORT", "9000")
        monkeypatch.setenv("MOJIOKOSHI_SENTRY_DSN", "https://sentry.example/123")
        monkeypatch.setenv("MOJIOKOSHI_OPEN_BROWSER", "false")

        s = Settings()
        assert s.log_format == "json"
        assert s.log_level == "DEBUG"
        assert s.host == "127.0.0.1"
        assert s.port == 9000
        assert s.sentry_dsn == "https://sentry.example/123"
        assert s.open_browser is False

    def test_env_file_loads(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        (tmp_path / ".env").write_text(
            "MOJIOKOSHI_LOG_FORMAT=json\nMOJIOKOSHI_PORT=1234\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        s = Settings()
        assert s.log_format == "json"
        assert s.port == 1234

    def test_unknown_env_is_ignored(self, monkeypatch: pytest.MonkeyPatch):
        """extra='ignore' must silently drop unknown MOJIOKOSHI_* vars."""
        monkeypatch.setenv("MOJIOKOSHI_NOT_A_REAL_FIELD", "oops")
        Settings()  # no exception


class TestValidation:
    @pytest.mark.parametrize("bad_port", [0, 65536, -1])
    def test_port_out_of_range_rejected(self, bad_port: int, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MOJIOKOSHI_PORT", str(bad_port))
        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_log_format_rejected(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MOJIOKOSHI_LOG_FORMAT", "yaml")
        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_log_level_rejected(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MOJIOKOSHI_LOG_LEVEL", "LOUD")
        with pytest.raises(ValidationError):
            Settings()

    @pytest.mark.parametrize("bad_rate", ["-0.1", "1.1"])
    def test_sample_rate_out_of_range_rejected(
        self, bad_rate: str, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("MOJIOKOSHI_SENTRY_TRACES_SAMPLE_RATE", bad_rate)
        with pytest.raises(ValidationError):
            Settings()
