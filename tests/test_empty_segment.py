"""An empty segment is unreadable, as any other unreadable segment is."""
import pytest

from phonematcher.features import feature_distance, vectorize_phones


def test_an_empty_segment_raises_value_error():
    with pytest.raises(ValueError):
        vectorize_phones("")


def test_an_empty_segment_is_far_from_every_segment():
    assert feature_distance("", "a") == 1.0
