"""Tests for :mod:`mojiokoshi.observability.sentry`.

Only the opt-out path is exercised here; the init path requires sentry-sdk
to be installed *and* would open a network client, so it's marked
``pragma: no cover`` in the source.
"""

from __future__ import annotations

from mojiokoshi.observability.sentry import maybe_init_sentry
from mojiokoshi.settings import Settings


def test_returns_false_when_no_dsn():
    assert maybe_init_sentry(Settings(sentry_dsn=None)) is False
