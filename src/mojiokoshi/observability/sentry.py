"""Optional Sentry initialization, gated on ``MOJIOKOSHI_SENTRY_DSN``.

Only active when installed as ``mojiokoshi[observability]`` *and* the DSN is
present in settings. In all other cases this is a no-op.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mojiokoshi.settings import Settings


def maybe_init_sentry(settings: Settings) -> bool:
    """Initialize the Sentry SDK if configured; return whether init occurred."""
    if not settings.sentry_dsn:
        return False

    # Local imports keep the optional dependency truly optional: if sentry-sdk
    # is not installed, we skip silently rather than raising at import time.
    try:  # pragma: no cover  # import path exercised only when extra installed
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:  # pragma: no cover
        return False

    sentry_sdk.init(  # pragma: no cover
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(transaction_style="url"),
            StarletteIntegration(transaction_style="url"),
            LoggingIntegration(level=None, event_level=None),
        ],
        send_default_pii=False,
        release="mojiokoshi@0.1.0",
    )
    return True  # pragma: no cover
