"""``scripts/build_features.py`` refuses a malformed ``overrides.json`` with a message naming the entry.

Each test breaks one entry of a copy of the shipped overrides and runs the build against it.
"""
import importlib.util
import json
from pathlib import Path

import pytest
import panphon  # noqa: F401  (the build extra; a missing install is an error, not a skip)

ROOT = Path(__file__).resolve().parent.parent
SHIPPED = json.loads((ROOT / "phonematcher" / "data" / "overrides.json").read_text(encoding="utf-8"))


def build_with(tmp_path, change) -> str:
    broken = json.loads(json.dumps(SHIPPED))
    change(broken)
    data = tmp_path / "data"
    data.mkdir()
    (data / "overrides.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("build_features", ROOT / "scripts" / "build_features.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.HERE = data
    with pytest.raises(SystemExit) as stopped:
        build.main(tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()
    return str(stopped.value)


def test_a_value_outside_plus_minus_zero_is_refused(tmp_path):
    message = build_with(tmp_path, lambda o: o["overrides"][0].update(value="x"))
    assert message == "override ɹ: value 'x' of hi is not '+', '-' or '0'"


def test_an_unknown_feature_name_is_refused(tmp_path):
    message = build_with(tmp_path, lambda o: o["overrides"][0].update(feature="hgh"))
    assert message == "override ɹ: unknown feature 'hgh'"


def test_an_unknown_diacritic_content_key_is_refused(tmp_path):
    message = build_with(tmp_path, lambda o: o["diacritics"][0]["content"].update(frnt="-"))
    assert message == f"diacritic {SHIPPED['diacritics'][0]['marker']}: unknown feature 'frnt'"


def test_an_override_on_a_segment_that_is_not_a_bare_letter_is_refused(tmp_path):
    message = build_with(tmp_path, lambda o: o["overrides"][0].update(phone="tʰ"))
    assert message == "override tʰ: the segment is not a bare table letter"


def test_an_unknown_feature_in_a_segments_set_is_refused(tmp_path):
    message = build_with(tmp_path, lambda o: o["segments"][0]["set"].update(tapp="+"))
    assert message == "segments entry ⱱ: unknown feature 'tapp'"


@pytest.mark.parametrize("kind, key", [("overrides", "phone"), ("diacritics", "marker"), ("segments", "segment")])
def test_an_entry_with_no_source_is_refused(tmp_path, kind, key):
    message = build_with(tmp_path, lambda o: o[kind][0].pop("source"))
    assert message == f"{kind} entry {SHIPPED[kind][0][key]} has no source"
