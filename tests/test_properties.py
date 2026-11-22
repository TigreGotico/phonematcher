"""Metric properties of the segment, tone and string distances, checked on sampled inputs."""
import itertools
import random
import unicodedata

from phonematcher.clustering import phone_clusters
from phonematcher.distance import edit_distance, segments
from phonematcher.features import phone_features, feature_distance
from phonematcher.tone import DIACRITIC_TONES, tone_distance

EPS = 1e-12
LETTERS = sorted(phone_clusters(0.1))
TABLE = sorted(phone_features)
TONES = ["".join(p) for p in itertools.product("˩˨˧˦˥", repeat=2)]


def _random_words(rng, count):
    return [[rng.choice(LETTERS) for _ in range(rng.randint(1, 8))] for _ in range(count)]


def test_the_letter_set_and_the_tone_set_have_their_expected_sizes():
    assert len(LETTERS) > 100
    assert len(TONES) == 25


def test_letter_distance_is_in_range_symmetric_and_zero_on_identity():
    for a, b in itertools.product(LETTERS, repeat=2):
        d = feature_distance(a, b)
        assert 0 <= d <= 1, (a, b, d)
        assert d == feature_distance(b, a), (a, b)
    for a in LETTERS:
        assert feature_distance(a, a) == 0


def test_letter_distance_obeys_the_triangle_inequality_on_sampled_triples():
    rng = random.Random(0)
    for _ in range(20000):
        a, b, c = (rng.choice(TABLE) for _ in range(3))
        assert feature_distance(a, c) <= feature_distance(a, b) + feature_distance(b, c) + EPS, (a, b, c)


def test_edit_distance_is_symmetric_and_zero_on_identity():
    rng = random.Random(0)
    words = _random_words(rng, 4000)
    for a, b in zip(words[:2000], words[2000:]):
        assert edit_distance(a, b) == edit_distance(b, a), (a, b)
        assert edit_distance(a, a) == 0
        assert edit_distance(b, b) == 0


def test_edit_distance_obeys_the_triangle_inequality_on_sampled_triples():
    rng = random.Random(1)
    words = _random_words(rng, 6000)
    for a, b, c in zip(words[:2000], words[2000:4000], words[4000:]):
        assert edit_distance(a, c) <= edit_distance(a, b) + edit_distance(b, c) + EPS, (a, b, c)


def test_edit_distance_never_exceeds_the_longer_length():
    rng = random.Random(2)
    words = _random_words(rng, 4000)
    for a, b in zip(words[:2000], words[2000:]):
        assert edit_distance(a, b) <= max(len(a), len(b)) + EPS, (a, b)


def test_segments_round_trip_random_words_of_letters():
    rng = random.Random(3)
    for _ in range(2000):
        words = _random_words(rng, rng.randint(1, 4))
        text = " ".join("".join(w) for w in words)
        expected = [seg for i, w in enumerate(words) for seg in (w if i == 0 else [" "] + w)]
        assert segments(text) == expected, (words, text)


def test_segments_give_the_same_output_for_nfc_and_nfd_input():
    # Tone diacritics on vowels are the case where the two forms differ: NFC writes á as one code point.
    rng = random.Random(4)
    marks = "".join(DIACRITIC_TONES)
    for _ in range(2000):
        text = " ".join(
            "".join(rng.choice(TABLE) + (rng.choice(marks) if rng.random() < 0.4 else "")
                    for _ in range(rng.randint(1, 6)))
            for _ in range(rng.randint(1, 3)))
        nfc, nfd = unicodedata.normalize("NFC", text), unicodedata.normalize("NFD", text)
        assert segments(nfc) == segments(nfd), (nfc, nfd)


def test_tone_distance_is_in_range_symmetric_and_zero_on_identity():
    for a, b in itertools.product(TONES, repeat=2):
        d = tone_distance(a, b)
        assert 0 <= d <= 1, (a, b, d)
        assert d == tone_distance(b, a), (a, b)
    for a in TONES:
        assert tone_distance(a, a) == 0


def test_tone_distance_obeys_the_triangle_inequality():
    for a, b, c in itertools.product(TONES, repeat=3):
        assert tone_distance(a, c) <= tone_distance(a, b) + tone_distance(b, c) + EPS, (a, b, c)
