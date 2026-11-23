"""Every example in README.md and docs/*.md runs, and every documented value is the real one.

A fenced ``python`` block is run with its page's earlier blocks. On an expression line, the
comment ``# value`` is a Python literal, optionally followed by ``: a note``. The result of the
line, with its floats rounded to the decimals of the literal, must print the same. A ``text``
fence that follows a ``python`` fence holds the output that the block prints.
"""
import ast
import contextlib
import io
import re
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PAGES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
FENCE = re.compile(r"^```(\w*)\s*$")


def fences(text):
    """The fenced blocks of a page as (language, code, line after the fence) triples."""
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        opening = FENCE.match(lines[i])
        if opening:
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            out.append((opening.group(1), "\n".join(lines[i + 1:j]), i, j))
            i = j
        i += 1
    return out


def rounded(value, places):
    if isinstance(value, float):
        return round(value, places)
    if isinstance(value, (list, tuple)):
        return type(value)(rounded(v, places) for v in value)
    return value


def expected_value(comment, where):
    note = comment.lstrip("#").strip()
    for text in (note, note.split(": ", 1)[0]):
        try:
            return ast.literal_eval(text), text
        except (ValueError, SyntaxError):
            continue
    pytest.fail(f"{where}: the comment {comment!r} on an expression line is not a Python value")


def run_block(code, namespace, where, first_line):
    """Run *code* and return (checked values, printed output)."""
    comments = {tok.start[0]: tok.string for tok in tokenize.generate_tokens(io.StringIO(code).readline)
                if tok.type == tokenize.COMMENT}
    checked, printed = 0, io.StringIO()
    with contextlib.redirect_stdout(printed):
        for node in ast.parse(code).body:
            if not isinstance(node, ast.Expr):
                exec(compile(ast.Module([node], []), where, "exec"), namespace)
                continue
            result = eval(compile(ast.Expression(node.value), where, "eval"), namespace)
            comment = comments.get(node.end_lineno)
            if comment is None:
                continue
            at = f"{where}:{first_line + node.end_lineno - 1}"
            expected, text = expected_value(comment, at)
            places = max((len(f) for f in re.findall(r"\d+\.(\d+)", text)), default=0)
            assert repr(rounded(result, places)) == repr(expected), f"{at}: {text} documented, {result!r} computed"
            checked += 1
    return checked, printed.getvalue()


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_example_runs_and_every_documented_value_is_the_computed_one(page, monkeypatch):
    monkeypatch.chdir(ROOT)
    blocks = fences(page.read_text(encoding="utf-8"))
    namespace = {"__name__": "__docs__"}
    for n, (language, code, start, end) in enumerate(blocks):
        if language != "python":
            continue
        _, printed = run_block(code, namespace, page.name, start + 2)
        following = blocks[n + 1] if n + 1 < len(blocks) else None
        if following and following[0] == "text" and following[2] == end + 2:
            assert printed.rstrip("\n") == following[1], f"{page.name}:{following[2] + 2}: the output block differs"
        else:
            assert not printed, f"{page.name}:{start + 2}: the block prints, and no text block follows it"


def test_the_pages_hold_documented_values_to_check():
    checked = 0
    for page in PAGES:
        namespace = {}
        for language, code, start, _ in fences(page.read_text(encoding="utf-8")):
            if language == "python":
                checked += run_block(code, namespace, page.name, start + 2)[0]
    assert checked >= 40


def test_the_index_lists_every_page():
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    linked = set(re.findall(r"\]\(([\w-]+\.md)\)", index))
    assert linked - {"index.md"} == {p.name for p in PAGES[1:]} - {"index.md"}
    assert "](../whitepaper.md)" in index and (ROOT / "whitepaper.md").exists()


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_a_page_has_an_agent_hint_after_its_title_and_a_footer(page):
    lines = page.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# ")
    assert lines[1] == "<!-- agent-hint"
    hint = lines[2:lines.index("-->")]
    assert [line.split(":")[0] for line in hint] == ["covers", "source", "generated", "verify", "see"]
    for source in hint[1].removeprefix("source: ").split(", "):
        assert list(ROOT.glob(source.split(":")[0])), f"{page.name}: no file {source}"
    assert page.name == "README.md" or lines[-1].startswith("[Index](index.md)"), lines[-1]
