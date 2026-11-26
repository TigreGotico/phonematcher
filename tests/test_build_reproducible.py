"""The shipped table is what ``scripts/build_features.py`` makes from its inputs.

The build reads PanPhon 0.22.2 data, ``overrides.json`` and the files in ``scripts/sources/``.
A change to ``overrides.json`` or to the script that is not followed by a rebuild leaves
``features.json`` behind, and this test fails.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import panphon  # noqa: F401  (the build extra; a missing install is an error, not a skip)

ROOT = Path(__file__).resolve().parent.parent


def test_build_reproduces_features_json_byte_for_byte(tmp_path):
    out = tmp_path / "features.json"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_features.py"), "--out", str(out)],
                   check=True, capture_output=True)
    assert out.read_bytes() == (ROOT / "phonematcher" / "data" / "features.json").read_bytes()


def test_a_segments_entry_that_names_an_unknown_segment_stops_the_build_with_a_message(tmp_path):
    overrides = json.loads((ROOT / "phonematcher" / "data" / "overrides.json").read_text(encoding="utf-8"))
    for field, entry in (("from", 0), ("place_of", 0)):
        broken = json.loads(json.dumps(overrides))
        broken["segments"][entry][field] = "ʞ"  # a letter the IPA chart does not hold
        data = tmp_path / field
        data.mkdir()
        (data / "overrides.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
        spec = importlib.util.spec_from_file_location("build_features", ROOT / "scripts" / "build_features.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        build.HERE = data
        with pytest.raises(SystemExit) as stopped:
            build.main(tmp_path / "out.json")
        assert str(stopped.value) == (
            f"segments entry {broken['segments'][entry]['segment']} names segments PanPhon does not list: ['ʞ']")
