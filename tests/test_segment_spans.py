"""segment_spans: the offsets of the segments in the input string. Expected spans are counted by
hand, one code point at a time, in the comment beside each case."""
import random
import unicodedata

import pytest

from phonematcher import segment_spans, segments
from phonematcher.distance import SUPRASEGMENTALS
from phonematcher.features import PRE_DIACRITICS, POST_DIACRITICS, SPELLINGS, TIES, phone_features
from phonematcher.tone import DIACRITIC_TONES, LEVELS, NUMERALS


@pytest.mark.parametrize("text, spans", [
    # ˈ0 t1 ͡2 ʃ3 ɐ4 ̃5 w6 ̃7: the stress mark is a gap, the tie joins t and ʃ
    ("ˈt͡ʃɐ̃w̃", [(1, 4), (4, 6), (6, 8)]),
    # ʁ0 ɨ1 .2 ˈ3 t4 i5 .6 ɾ7 a8 .9 d10 ɐ11: syllable dots and stress are gaps
    ("ʁɨ.ˈti.ɾa.dɐ", [(0, 1), (1, 2), (4, 5), (5, 6), (7, 8), (8, 9), (10, 11), (11, 12)]),
    # ʧ0 a1 ʦ2 ʰ3: a ligature is one character and keeps its spelling in the span
    ("ʧaʦʰ", [(0, 1), (1, 2), (2, 4)]),
    # m0 a1 ◌́2 (NFD): the tone mark stays in the span of a
    ("má", [(0, 1), (1, 3)]),
    # m0 á1 (NFC)
    ("má", [(0, 1), (1, 2)]),
    # m0 a1 ˥2 ˩3 space4 t5 a6 ²7 ¹8 ⁴9: a tone run is in the span of its vowel, the space a gap
    ("ma˥˩ ta²¹⁴", [(0, 1), (1, 4), (5, 6), (6, 10)]),
    # m0 U+200B1 a2 U+FEFF3: format characters are gaps
    ("m​a﻿", [(0, 1), (2, 3)]),
    # a0 ͡1 i2: a diphthong is two segments and the tie bar is a gap
    ("a͡i", [(0, 1), (2, 3)]),
    # ⁿ0 d1 a2: a prenasal mark belongs to the stop after it
    ("ⁿda", [(0, 2), (2, 3)]),
    # p0 a1 space2 tab3 t4 a5
    ("pa \tta", [(0, 1), (1, 2), (4, 5), (5, 6)]),
    ("", []),
    ("ˈ. ", []),
])
def test_hand_counted_spans(text, spans):
    assert segment_spans(text) == spans


def test_the_spans_give_the_substrings_as_written():
    text = "ˈʧɐ̃w̃"
    assert [text[s:e] for s, e in segment_spans(text)] == ["ʧ", "ɐ̃", "w̃"]
    assert segments(text) == ["t͡ʃ", "ɐ̃", "w̃"]


def check(text):
    spans = segment_spans(text)
    assert all(0 <= s < e <= len(text) for s, e in spans), (text, spans)
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), (text, spans)
    gaps = [text[a:b] for a, b in zip([0] + [e for _, e in spans], [s for s, _ in spans] + [len(text)])]
    assert all(seg == " " for gap in gaps for seg in segments(gap)), (text, spans)
    return spans


SYLLABLE_ONSETS = ["p", "b", "t", "d", "k", "ɡ", "m", "n", "s", "ʃ", "ʁ", "l", "ɾ", "t͡ʃ", "d͡ʒ", "ʧ", "ʦ", "ⁿd", "kʰ", "tʲ", "ŋ͡m", "ɓ"]
VOWELS = ["a", "e", "i", "o", "u", "ɐ", "ɐ̃", "ã", "ẽ", "ɛ", "ɔ", "ə", "ɨ", "aː", "i̯", "a͡i"]
TONES = ["", "", "́", "̀", "̌", "˥", "˥˩", "²¹⁴", "꜒꜔", "˧"]
MARKS = ["", "", "", "ˈ", "ˌ", ".", "​"]


def well_formed(rng):
    words = []
    for _ in range(rng.randint(1, 3)):
        word = ""
        for _ in range(rng.randint(1, 4)):
            vowel = rng.choice(VOWELS)
            tone = rng.choice(TONES)
            if unicodedata.combining(tone[:1] or " ") and "͡" not in vowel:
                vowel += tone
                tone = ""
            word += rng.choice(MARKS) + rng.choice(SYLLABLE_ONSETS) + vowel + tone
        words.append(word)
    text = " ".join(words)
    return unicodedata.normalize(rng.choice(["NFC", "NFD"]), text)


def test_each_span_segments_as_the_text_does_on_random_well_formed_ipa():
    rng = random.Random(0)
    texts = [well_formed(rng) for _ in range(5000)]
    checked = 0
    for text in texts:
        spans = check(text)
        assert [seg for s, e in spans for seg in segments(text[s:e])] == [seg for seg in segments(text) if seg != " "], text
        checked += 1
    assert checked == len(texts) == 5000


def test_spans_are_ordered_and_gaps_hold_no_segment_on_random_characters():
    chars = sorted({c for k in phone_features for c in unicodedata.normalize("NFC", k)} | POST_DIACRITICS
                   | set(PRE_DIACRITICS) | set(TIES) | set(DIACRITIC_TONES) | set(LEVELS) | set(NUMERALS)
                   | SUPRASEGMENTALS | {chr(k) for k in SPELLINGS} | set(" \t​﻿áãâǎ"))
    rng = random.Random(1)
    texts = ["".join(rng.choice(chars) for _ in range(rng.randint(0, 12))) for _ in range(5000)]
    assert sum(1 for text in texts if check(text) is not None) == 5000
