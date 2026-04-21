"""Contract tests using deal for TranscriptionService."""

from __future__ import annotations

from typing import TYPE_CHECKING

import deal
import pytest

from mojiokoshi.services.whisper import TranscriptionService

from ..conftest import FakeWhisperModel

if TYPE_CHECKING:
    from pathlib import Path


class TestTranscriptionServiceContracts:
    def test_init_contract_rejects_none(self):
        """Pre-condition: model must not be None."""
        with pytest.raises(deal.PreContractError):
            TranscriptionService(model=None)  # type: ignore[arg-type]

    def test_transcribe_contract_rejects_missing_file(self):
        """Pre-condition: audio file must exist."""
        model = FakeWhisperModel()
        service = TranscriptionService(model=model)
        with pytest.raises(deal.PreContractError):
            service.transcribe("/no/such/file.wav", language="ja")

    def test_transcribe_contract_rejects_empty_language(self, tmp_path: Path):
        """Pre-condition: language must not be empty."""
        model = FakeWhisperModel()
        service = TranscriptionService(model=model)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")
        with pytest.raises(deal.PreContractError):
            service.transcribe(str(audio_file), language="")

    def test_stream_contract_rejects_missing_file(self):
        """Pre-condition: audio file must exist for streaming."""
        model = FakeWhisperModel()
        service = TranscriptionService(model=model)
        with pytest.raises(deal.PreContractError):
            list(service.transcribe_stream("/no/such/file.wav", language="ja"))

    def test_stream_contract_rejects_empty_language(self, tmp_path: Path):
        """Pre-condition: language must not be empty for streaming."""
        model = FakeWhisperModel()
        service = TranscriptionService(model=model)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")
        with pytest.raises(deal.PreContractError):
            list(service.transcribe_stream(str(audio_file), language=""))
