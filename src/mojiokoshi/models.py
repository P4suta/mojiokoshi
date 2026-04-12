"""Pydantic schemas for request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Segment(BaseModel):
    """A single transcription segment with timing information."""

    id: int = Field(ge=0)
    start: float = Field(ge=0.0)
    end: float = Field(ge=0.0)
    text: str


class TranscriptionResult(BaseModel):
    """Complete transcription result."""

    text: str
    language: str = Field(min_length=2, max_length=5)
    segments: list[Segment]
    duration_seconds: float = Field(ge=0.0)


class UploadResponse(BaseModel):
    """Response after uploading an audio file."""

    file_id: str = Field(min_length=1)
    filename: str


class WsClientMessage(BaseModel):
    """Message from WebSocket client to server."""

    type: Literal["start", "cancel"]
    file_id: str | None = None
    model_size: str | None = None
    language: str | None = None

    @model_validator(mode="after")
    def validate_start_fields(self) -> WsClientMessage:
        if self.type == "start":
            if not self.file_id:
                msg = "file_id is required for 'start' messages"
                raise ValueError(msg)
            if not self.language:
                msg = "language is required for 'start' messages"
                raise ValueError(msg)
        return self


class WsServerMessage(BaseModel):
    """Message from server to WebSocket client."""

    type: Literal["segment", "progress", "done", "error"]
    segment: Segment | None = None
    percent: int | None = None
    elapsed_seconds: float | None = None
    full_text: str | None = None
    message: str | None = None


class ErrorMessage(BaseModel):
    """Generic error response."""

    message: str


class ConfigResponse(BaseModel):
    """Response for /api/config endpoint."""

    models: list[str]
    languages: dict[str, str]
    default_model: str
    default_language: str
    device: str


class StatusResponse(BaseModel):
    """Response for /api/status endpoint."""

    state: Literal["starting", "downloading", "loading", "ready", "error"]
    message: str
    ready: bool
    error: str | None = None
