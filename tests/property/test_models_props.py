"""Property-based tests for Pydantic schemas using Hypothesis."""

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from mojiokoshi.models import Segment, TranscriptionResult


@pytest.mark.property
class TestSegmentProperties:
    @given(
        id=st.integers(min_value=0, max_value=10000),
        start=st.floats(min_value=0.0, max_value=36000.0, allow_nan=False),
        end=st.floats(min_value=0.0, max_value=36000.0, allow_nan=False),
        text=st.text(max_size=5000),
    )
    def test_any_valid_inputs_produce_valid_segment(self, id, start, end, text):
        seg = Segment(id=id, start=start, end=end, text=text)
        assert seg.id == id
        assert seg.start == start
        assert seg.end == end
        assert seg.text == text

    @given(
        id=st.integers(max_value=-1),
    )
    def test_negative_id_always_rejected(self, id):
        with pytest.raises(ValidationError):
            Segment(id=id, start=0.0, end=1.0, text="test")

    @given(
        start=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
    )
    def test_negative_start_always_rejected(self, start):
        with pytest.raises(ValidationError):
            Segment(id=0, start=start, end=1.0, text="test")


@pytest.mark.property
class TestTranscriptionResultProperties:
    @given(
        text=st.text(max_size=10000),
        language=st.text(min_size=2, max_size=5, alphabet=st.characters(categories=("L",))),
        duration=st.floats(min_value=0.0, max_value=36000.0, allow_nan=False),
    )
    def test_valid_result_round_trips(self, text, language, duration):
        result = TranscriptionResult(
            text=text, language=language, segments=[], duration_seconds=duration
        )
        assert result.text == text
        assert result.language == language
        assert result.duration_seconds == duration

    @given(
        n_segments=st.integers(min_value=0, max_value=20),
    )
    def test_segment_count_preserved(self, n_segments):
        segments = [
            Segment(id=i, start=float(i), end=float(i + 1), text=f"seg{i}")
            for i in range(n_segments)
        ]
        result = TranscriptionResult(
            text="test", language="ja", segments=segments, duration_seconds=float(n_segments)
        )
        assert len(result.segments) == n_segments
