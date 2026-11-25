# Segments
<!-- agent-hint
covers: the grammar of one segment as segments() and segment_spans() read it, each rule with a real input and output
source: phonematcher/distance.py, phonematcher/features.py
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py tests/test_segment_grammar.py -k segment
see: features.md, tones.md
-->

This page states what one segment is. `segments` cuts an IPA string into segments, and `vectorize_phones` reads one segment at a time. Each rule below gives one input and the output of `segments`. After the colon, the comment says what `vectorize_phones` does with each output segment: `reads` returns a vector, and `raises` raises `ValueError`. `tests/test_segment_grammar.py` runs every example on this page.

```python
from phonematcher import segments, segment_spans
```

## 1. A base letter with combining marks

A segment starts at a base letter. The combining marks written after the base stay in the segment. Marks and letters can come in any Unicode form: `segments` returns the composed form.

```python
segments("t̪")  # ['t̪']: reads
segments("ã")  # ['ã']: reads
segments("ḛ̃")  # ['ḛ̃']: reads
segments("ta")  # ['t', 'a']: reads, reads
```

## 2. Marks before the base

A prenasal mark (`ⁿ`, `ᵐ`, `ᵑ`) or a preglottal mark (`ˀ`) is written before its base and joins the segment of that base. More than one of these marks can join the same base. A mark with no base after it is a segment of its own, and that segment raises.

```python
segments("ⁿd")  # ['ⁿd']: reads
segments("ˀm")  # ['ˀm']: reads
segments("ˀⁿd")  # ['ˀⁿd']: reads
segments("ⁿt͡s")  # ['ⁿt͡s']: reads
segments("ⁿ")  # ['ⁿ']: raises
```

## 3. Modifier letters after the base

A modifier letter written after the base stays in the segment. The segment reads when the table lists the base with that modifier. A modifier that the table does not combine with its base makes a segment that raises. In `dzʰ`, the letters are two segments because no tie bar joins them, and `zʰ` raises.

```python
segments("tʰ")  # ['tʰ']: reads
segments("kʷ")  # ['kʷ']: reads
segments("tʲ")  # ['tʲ']: reads
segments("dzʰ")  # ['d', 'zʰ']: reads, raises
```

## 4. Tie bars

A tie bar, `͡` or `͜`, joins the symbols on both sides of it into one segment. This is how an affricate and a double articulation are written. The bar can be above or below the pair. Two letters with no tie bar are two segments.

```python
segments("t͡ʃ")  # ['t͡ʃ']: reads
segments("t͜ʃ")  # ['t͜ʃ']: reads
segments("kʷ͡p")  # ['kʷ͡p']: reads
segments("ts")  # ['t', 's']: reads, reads
```

A tie between two vowels is a diphthong. It gives two segments: the first vowel, and the second vowel with a non-syllabic mark. A chain of ties gives one non-syllabic vowel for each vowel after the first.

```python
segments("a͡i")  # ['a', 'i̯']: reads, reads
segments("a͡i͡u")  # ['a', 'i̯', 'u̯']: reads, reads, reads
```

A tie bar with no symbol on one side does not join anything. A leading tie bar stays on the next segment, and a trailing tie bar stays on the segment before it. In both cases the segment raises. A tie bar never joins across a space.

```python
segments("͡ǃ")  # ['͡ǃ']: raises
segments("t͡")  # ['t͡']: raises
segments("ai͡")  # ['a', 'i͡']: reads, raises
segments("a ͡ǃ")  # ['a', ' ', '͡ǃ']: reads, raises, raises
```

## 5. Click ties

A click tie joins a click with a velar or uvular letter. The two orders give the same kind of segment, one segment each, and both read. The rear letter can carry a combining mark.

```python
segments("ǃ͡q")  # ['ǃ͡q']: reads
segments("q͡ǃ")  # ['q͡ǃ']: reads
segments("ŋ̊͡ǃ")  # ['ŋ̊͡ǃ']: reads
segments("ǃ͡ŋ̊")  # ['ǃ͡ŋ̊']: reads
```

Two clicks tied together do not read.

```python
segments("ǃ͡ǃ")  # ['ǃ͡ǃ']: raises
```

## 6. Tone runs and their carrier

A tone is a run of tone letters, tone numerals or tone diacritics. It moves onto its carrier: the last vowel or syllabic consonant before it in the same word that has no tone yet. The tone letters then belong to the segment of the carrier. A syllabic consonant can be a carrier.

```python
segments("ma˥")  # ['m', 'a˥']: reads, reads
segments("ma˧˥")  # ['m', 'a˧˥']: reads, reads
segments("ma²¹⁴")  # ['m', 'a˨˩˦']: reads, reads
segments("má")  # ['m', 'a˦']: reads, reads
segments("ámà")  # ['a˦', 'm', 'a˨']: reads, reads, reads
segments("tam˧˧")  # ['t', 'a˧˧', 'm']: reads, reads, reads
segments("m̩˥")  # ['m̩˥']: reads
```

A tone run ends where its notation changes. In the next example the first run is the tone 214 in Chao letters, and the second run is the tone 35 in left-stem letters. The vowel has a tone already, so the second run has no carrier. It is a segment of its own, and that segment raises.

```python
segments("ma˨˩˦꜔꜒")  # ['m', 'a˨˩˦', '˧˥']: reads, reads, raises
```

A tone with no carrier is a segment of tone letters, and that segment raises.

```python
segments("˥˩")  # ['˥˩']: raises
segments("ɡ˩a")  # ['ɡ', '˩', 'a']: reads, raises, reads
```

## 7. Marks after a tone

A length mark or a combining mark written after a tone belongs to the vowel right before the tone. The tone letters move to the end of the segment.

```python
segments("a˥ː")  # ['aː˥']: reads
segments("a˥̃")  # ['ã˥']: reads
```

## 8. Length

A length mark, `ː` or `ˑ`, stays in the segment of the letter before it. A repeated length mark makes a segment that raises.

```python
segments("aː")  # ['aː']: reads
segments("aˑ")  # ['aˑ']: reads
segments("aːˑ")  # ['aːˑ']: reads
segments("maːː")  # ['m', 'aːː']: reads, raises
```

## 9. Spaces and boundaries

A space is a segment of its own. It raises, because a space is not a sound. A syllable break (`.`), a link (`‿`), a foot or intonation boundary (`|`, `‖`) and a stress mark (`ˈ`, `ˌ`) make no segment. They end a segment. A length mark written after a syllable break still belongs to the segment before it.

```python
segments("a b")  # ['a', ' ', 'b']: reads, raises, reads
segments("a.b")  # ['a', 'b']: reads, reads
segments("a|b")  # ['a', 'b']: reads, reads
segments("t‿a")  # ['t', 'a']: reads, reads
segments("ma‖ta")  # ['m', 'a', 't', 'a']: reads, reads, reads, reads
segments("ˈma")  # ['m', 'a']: reads, reads
segments("a.ː")  # ['aː']: reads
```

## 10. Where each segment is written

`segment_spans` gives the `(start, end)` offsets of each segment in the text you wrote. A space and a dropped mark fall between two spans. Segments that share a character, such as the two segments of a diphthong, share one span.

```python
segment_spans("ma˥ ta")  # [(0, 1), (1, 3), (4, 5), (5, 6)]
segment_spans("ˈma")     # [(1, 2), (2, 3)]
segment_spans("a͡i")      # [(0, 3)]
```

[Index](index.md) · Previous: [The feature table](features.md) · Next: [Design choices and limits](design.md)
