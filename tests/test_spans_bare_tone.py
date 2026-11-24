"""segment_spans on text that holds only tone letters: phoonnx cuts the gap after a coda this way."""
import pytest

from phonematcher import segment_spans


# A run with no bearer is one tone segment; a change of notation starts a new run.
@pytest.mark.parametrize("text, spans", [
    ("˧˧", [(0, 2)]),
    ("˧˧ ", [(0, 2)]),
    ("²¹⁴", [(0, 3)]),
    ("˨˩˦꜔꜒", [(0, 3), (3, 5)]),
    ("˥⁵", [(0, 1), (1, 2)]),
])
def test_bare_tone_runs_have_one_span_per_run(text, spans):
    assert segment_spans(text) == spans
