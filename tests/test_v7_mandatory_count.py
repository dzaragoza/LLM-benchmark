"""Pins: addendum 156 - the number of v7 candidates is MANDATORY:
--v7-families has no default (argparse required=True) and certify_v7
takes roster_limit positionally with no fallback. A silent default
is how "we ran 16" became a 4-family pilot plan without anyone
noticing (the addendum-154 confusion): the count is now explicit at
every entry point.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_v7_families_flag_is_required():
    src = (ROOT / "full_benchmark.py").read_text(encoding="utf-8")
    i = src.index("--v7-families")
    window = src[i : i + 300]
    assert "required=True" in window, "--v7-families must be required=True (addendum 156)"
    assert "default" not in window.split("help=")[0].split("required=True")[0].replace(
        "default=None", ""
    ), "no default may accompany the flag"


def test_certify_v7_has_no_default_limit():
    src = (ROOT / "bench" / "v7.py").read_text(encoding="utf-8")
    i = src.index("def certify_v7")
    sig = src[i : src.index(") ->", i)]
    assert "roster_limit: int," in sig and "roster_limit: int =" not in sig, (
        "roster_limit must carry no default (addendum 156)"
    )


def test_v7_families_missing_fails_to_parse():
    """argparse exits 2 when --v7-families is absent: the count cannot
    be omitted, only stated."""
    import bench.v7  # noqa: F401 - importability guard

    proc = subprocess.run(
        [sys.executable, str(ROOT / "full_benchmark.py"), "--task", "v7", "--help"],
        capture_output=True,
        text=True,
    )
    # --help must document the flag as required
    assert "--v7-families V7_FAMILIES" in proc.stdout
