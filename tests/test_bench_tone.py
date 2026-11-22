"""C7: the tone task on the committed table and on hand values.

Pair rate of T2 and T5 (Table 12, percent per band B04, B08, B16): T2 heard as T5 is 15, 8, 7, mean
10; T5 heard as T2 is 18, 17, 15, mean 50/3. The pair is (10 + 50/3) / 2 = 40/3 percent, 0.13333.
Pair rate of T1 and T3 (Table 13): T1 heard as T3 is 15, 15, 7, mean 37/3; T3 heard as T1 is 35, 27,
25, mean 29. The pair is (37/3 + 29) / 2 = 62/3 percent, 0.20667.

Directions: 55 and 33 are level, 35 is rising, 21 is falling. The baseline distance is 0 for 55
against 33 and 1 for 55 against 35, 55 against 21 and 35 against 21.

Tone distance of 55 against 35: the contours are 5 5 5 and 3 4 5, the differences 2 + 1 + 0 = 3,
and 3 / (4 steps * 3 points) = 0.25. Tone letters: 35 is ˧˥.

Spearman of the negative distance with a rate: distances 0.1, 0.2, 0.3 against rates 3, 2, 1 are in
the same order, so 1.0.
"""
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_fake import Fake

from tasks import tone  # noqa: E402

CHAO = tone.CHAO["main"]


def test_the_committed_table_has_the_transcribed_bytes():
    digest = hashlib.sha256(tone.DATA.read_bytes()).hexdigest()
    assert digest == "3b61f7c48adf0617b8f9c7bb2b9ebcb67429d31e742ecc2e71648fc71fc50629"


def test_the_table_has_three_band_rows_for_each_of_six_tones():
    rows = tone.read_rows()
    assert len(rows) == 18
    assert sorted({r["presented"] for r in rows}) == tone.TONES


def test_symmetric_rate_is_the_mean_of_both_directions_over_the_bands():
    rates = tone.pair_rates(tone.read_rows())
    assert len(rates) == 15
    assert rates["T2", "T5"] == pytest.approx(40 / 3 / 100)
    assert rates["T1", "T3"] == pytest.approx(62 / 3 / 100)


def test_tone_letters_and_directions():
    assert tone.tone_letters("35") == "˧˥"
    assert [tone.direction(CHAO[t]) for t in ("T1", "T2", "T3", "T4")] == ["level", "rising", "level", "falling"]


def test_direction_baseline_for_55_35_21():
    assert tone.direction_distance(CHAO, "T1", "T3") == 0.0
    assert tone.direction_distance(CHAO, "T1", "T2") == 1.0
    assert tone.direction_distance(CHAO, "T1", "T4") == 1.0
    assert tone.direction_distance(CHAO, "T2", "T4") == 1.0


def test_phonematcher_distance_of_55_against_35():
    assert tone.phonematcher_distance(CHAO, "T1", "T2") == pytest.approx(0.25)


def test_the_two_chao_sets_differ_in_tone_2_only():
    main, alternative = tone.CHAO["main"], tone.CHAO["alternative"]
    assert {t for t in tone.TONES if main[t] != alternative[t]} == {"T2"}


def test_run_scores_both_chao_sets_on_fifteen_pairs_and_names_the_unscored_systems():
    payload = tone.run([Fake("phonematcher", ""), Fake("sca", "")], "seen", Path("."))
    assert set(payload["scored"]) == {"main", "alternative"}
    for row in payload["scored"].values():
        assert set(row) == {"direction_baseline", "phonematcher"}
        assert row["phonematcher"]["pairs_in"] == row["phonematcher"]["pairs_out"] == 15
    assert payload["not_scored"] == ["sca"]
