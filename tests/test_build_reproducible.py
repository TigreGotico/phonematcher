"""The shipped table is what ``scripts/build_features.py`` makes from its inputs.

The build reads PanPhon 0.22.2 data, ``overrides.json`` and the files in ``scripts/sources/``.
A change to ``overrides.json`` or to the script that is not followed by a rebuild leaves
``features.json`` behind, and this test fails.
"""
import subprocess
import sys
from pathlib import Path

import panphon  # noqa: F401  (the build extra; a missing install is an error, not a skip)

ROOT = Path(__file__).resolve().parent.parent


def test_build_reproduces_features_json_byte_for_byte(tmp_path):
    out = tmp_path / "features.json"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_features.py"), "--out", str(out)],
                   check=True, capture_output=True)
    assert out.read_bytes() == (ROOT / "phonematcher" / "data" / "features.json").read_bytes()
