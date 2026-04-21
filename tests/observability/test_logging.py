"""Tests for :mod:`mojiokoshi.observability.logging`."""

from __future__ import annotations

import io
import json
import logging
from contextlib import redirect_stdout
from typing import TYPE_CHECKING

import pytest
import structlog
from asgi_correlation_id.context import correlation_id

from mojiokoshi.observability.logging import configure_logging

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@pytest.fixture(autouse=True)
def reset_logging() -> Iterator[None]:
    """Restore the root logger and structlog state after each test."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)
    structlog.reset_defaults()


def _capture(log_format: str, log_level: str, work: Callable[[], None]) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        configure_logging(log_format=log_format, log_level=log_level)
        work()
        for handler in logging.getLogger().handlers:
            handler.flush()
    return buf.getvalue()


def test_json_mode_emits_parseable_json():
    def emit() -> None:
        structlog.get_logger("unit.test").info("hello_event", value=42)

    out = _capture("json", "INFO", emit)
    line = out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["event"] == "hello_event"
    assert payload["value"] == 42
    assert payload["level"] == "info"
    assert "timestamp" in payload
    assert "correlation_id" not in payload


def test_console_mode_emits_human_readable():
    def emit() -> None:
        structlog.get_logger("unit.test").warning("boom", code=7)

    out = _capture("console", "DEBUG", emit)
    assert "boom" in out
    assert "code" in out


def test_correlation_id_is_injected():
    token = correlation_id.set("test-cid-123")
    try:

        def emit() -> None:
            structlog.get_logger("unit.test").info("cid_event")

        out = _capture("json", "INFO", emit)
        payload = json.loads(out.strip().splitlines()[-1])
        assert payload["correlation_id"] == "test-cid-123"
    finally:
        correlation_id.reset(token)


def test_stdlib_logger_flows_through_structlog():
    """Stdlib ``logging.getLogger(...).info(...)`` must render via our pipeline."""

    def emit() -> None:
        logging.getLogger("uvicorn.access").info("hit %s", "/health")

    out = _capture("json", "INFO", emit)
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["event"] == "hit /health"
    assert payload["logger"] == "uvicorn.access"


def test_configure_is_idempotent():
    configure_logging(log_format="console", log_level="INFO")
    first_handlers = logging.getLogger().handlers[:]
    configure_logging(log_format="json", log_level="DEBUG")
    second_handlers = logging.getLogger().handlers[:]
    assert len(first_handlers) == 1
    assert len(second_handlers) == 1
    assert first_handlers != second_handlers
