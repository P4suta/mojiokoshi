"""Typed environment-driven settings."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogFormat = Literal["json", "console"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and/or a local .env file.

    All variables share the ``MOJIOKOSHI_`` prefix so they don't collide with
    unrelated process env. A file named ``.env`` in the working directory is
    read if present, but host-level environment takes precedence.
    """

    model_config = SettingsConfigDict(
        env_prefix="MOJIOKOSHI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_format: LogFormat = "console"
    log_level: LogLevel = "INFO"
    # Server binds to all interfaces by design; S104 is silenced via per-file-ignore.
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    default_model: str = "large-v3"
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    open_browser: bool = True


def get_settings() -> Settings:
    """Build a fresh :class:`Settings` instance from the current environment."""
    return Settings()
