"""Structured logging pipeline built on structlog and rich.

Dev builds render colored, multi-line tracebacks; prod builds emit JSON lines
suitable for log collectors. Stdlib loggers (uvicorn / faster_whisper / fastapi)
are routed through the same pipeline so nothing bypasses the structured format.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog
from asgi_correlation_id.context import correlation_id

if TYPE_CHECKING:
    from structlog.types import EventDict, Processor


def _inject_correlation_id(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """Attach the active ASGI correlation id (if any) to every event."""
    cid = correlation_id.get()
    if cid is not None:
        event_dict["correlation_id"] = cid
    return event_dict


_NOISY_STDLIB_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
    "faster_whisper",
)


def _shared_processors() -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        _inject_correlation_id,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def _build_renderer(log_format: str) -> Processor:
    if log_format == "json":
        return structlog.processors.JSONRenderer()
    # Dev: rich traceback with locals on uncaught errors, plus ConsoleRenderer.
    from rich.traceback import install as _rich_install

    _rich_install(show_locals=True, width=120, word_wrap=True)
    return structlog.dev.ConsoleRenderer(colors=True)


def configure_logging(*, log_format: str, log_level: str) -> None:
    """Configure structlog + stdlib logging.

    Idempotent: calling this repeatedly replaces prior handlers instead of
    stacking them, which is important for tests.

    Args:
        log_format: ``"json"`` for prod, ``"console"`` for dev.
        log_level: Any stdlib logging level name.
    """
    shared = _shared_processors()
    renderer = _build_renderer(log_format)

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    # Let framework loggers propagate up so they hit our single handler.
    for name in _NOISY_STDLIB_LOGGERS:
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
