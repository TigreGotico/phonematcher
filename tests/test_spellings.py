"""Non-IPA spellings read as the IPA letter they stand for.

The pairs come from the annotations of the Unicode code charts U+0000 and U+0250 (IPA Extensions),
quoted in each row's ``source`` in ``data/spellings.json``.
"""
import json
from importlib.resources import files

import pytest

from phonematcher import ipa_distance, segments
from phonematcher.features import vectorize_phones

# Spelling, IPA reading, as the chart annotation names the sound (voiced/voiceless, place, manner).
CHART_PAIRS = [
    ("g", "ɡ"),    # U+0067 -> U+0261 "latin small letter script g", voiced velar stop
    ("ʦ", "t͡s"),  # U+02A6 voiceless affricate
    ("ʣ", "d͡z"),  # U+02A3 voiced affricate
    ("ʧ", "t͡ʃ"),  # U+02A7 voiceless postalveolar affricate
    ("ʤ", "d͡ʒ"),  # U+02A4 voiced postalveolar affricate
    ("ʨ", "t͡ɕ"),  # U+02A8 voiceless alveolo-palatal affricate
    ("ʥ", "d͡ʑ"),  # U+02A5 voiced alveolo-palatal affricate
]
ROWS = json.loads((files("phonematcher") / "data" / "spellings.json").read_text(encoding="utf-8"))


def test_the_file_lists_exactly_the_chart_pairs():
    assert [(r["spelling"], r["reads_as"]) for r in ROWS] == CHART_PAIRS


@pytest.mark.parametrize("spelling, reads_as", CHART_PAIRS)
def test_a_spelling_has_the_vector_of_its_ipa_reading(spelling, reads_as):
    assert vectorize_phones(spelling) == vectorize_phones(reads_as)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["spelling"])
def test_every_row_names_a_source(row):
    assert row["source"].strip()
    assert "unicode.org/charts" in row["source"]


@pytest.mark.parametrize("spelling, reads_as", CHART_PAIRS)
def test_segments_translates_a_spelling(spelling, reads_as):
    assert segments(spelling) == [reads_as]


def test_segments_keeps_the_marks_of_a_spelling():
    # ʧʰ is one aspirated affricate: the ligature, then the aspiration mark.
    assert segments("ʧʰ") == ["t͡ʃʰ"]
    assert vectorize_phones("ʧʰ") == vectorize_phones("t͡ʃʰ")


def test_ascii_g_is_the_voiced_velar_stop():
    assert ipa_distance("ɡato", "gato") == 0.0
