"""Every `segments(...)` example on docs/segments.md is a case, and the page is the only source of its values.

An example line reads ``segments("input")  # ['seg', ...]: reads, raises, ...``. The list is the output of
``segments``. After the colon, each word is what ``vectorize_phones`` does with the segment at that place.
"""
import ast
import re
from pathlib import Path

import pytest

from phonematcher import segment_spans, segments
from phonematcher.features import vectorize_phones

PAGE = Path(__file__).resolve().parent.parent / "docs" / "segments.md"
EXAMPLE = re.compile(r"^segments\((?P<text>\".*\")\)\s+# (?P<output>\[.*\]): (?P<verdicts>(?:reads|raises)(?:, (?:reads|raises))*)$")


def examples():
    cases = []
    for line in PAGE.read_text(encoding="utf-8").splitlines():
        found = EXAMPLE.match(line)
        if found:
            cases.append((ast.literal_eval(found["text"]), ast.literal_eval(found["output"]), found["verdicts"].split(", ")))
    return cases


def test_the_page_holds_its_examples():
    assert len(examples()) >= 40
    lines = [line for line in PAGE.read_text(encoding="utf-8").splitlines() if line.startswith("segments(")]
    assert len(lines) == len(examples())


@pytest.mark.parametrize("text, output, verdicts", examples(), ids=[text for text, _, _ in examples()])
def test_segments_gives_the_documented_output(text, output, verdicts):
    assert segments(text) == output
    assert len(verdicts) == len(output)


@pytest.mark.parametrize("text, output, verdicts", examples(), ids=[text for text, _, _ in examples()])
def test_vectorize_phones_reads_or_raises_as_documented(text, output, verdicts):
    for segment, verdict in zip(output, verdicts):
        if verdict == "reads":
            vectorize_phones(segment)
        else:
            with pytest.raises(ValueError):
                vectorize_phones(segment)


# The tone letters of a tone written after a coda are in no span: the tone belongs to the vowel before the coda,
# and a span is one range of the text.
TONE_AFTER_CODA = "tam˧˧"
SPAN_CASES = [
    pytest.param(*case, marks=pytest.mark.xfail(strict=True, reason="tone after a coda is in no span: audits/phonematcher/issue-drafts-grammar.md"))
    if case[0] == TONE_AFTER_CODA else case
    for case in examples()
]


@pytest.mark.parametrize("text, output, verdicts", SPAN_CASES, ids=[text for text, _, _ in examples()])
def test_segment_spans_cuts_the_text_into_the_same_segments(text, output, verdicts):
    spans = segment_spans(text)
    assert [segment for s, e in spans for segment in segments(text[s:e])] == [x for x in output if x != " "]
