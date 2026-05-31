"""Pin the contract of `scan_analyze_fixtures.py` (stub mode + helpers).

The real Scan-driven runs happen offline (Scan binary required), so
these tests cover only the deterministic plumbing: fixture discovery,
output schema, idempotent stub generation, and the helper logic that
turns Scan output into the JSON contract.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_SCRIPT = Path(__file__).resolve().parents[1] / "scan_analyze_fixtures.py"
_spec = importlib.util.spec_from_file_location("scan_analyze_fixtures", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
# Ensure backend/ is on sys.path before the module's top-level import runs.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
_spec.loader.exec_module(mod)


def test_collect_fixtures_returns_all_166():
    fixtures = mod.collect_fixtures()
    assert len(fixtures) == 166
    assert all(f.id.startswith("BEG_CH") for f in fixtures)


def test_collect_fixtures_sorted_by_id():
    ids = [f.id for f in mod.collect_fixtures()]
    assert ids == sorted(ids)


def test_first_token():
    assert mod.first_token("42-37 (19x28) 29-23") == "42-37"
    assert mod.first_token("32x14") == "32x14"
    assert mod.first_token("") is None
    assert mod.first_token(None) is None


def test_winning_for_threshold():
    assert mod.winning_for(0.7) == "white"
    assert mod.winning_for(-0.6) == "black"
    assert mod.winning_for(0.2) == "draw"
    assert mod.winning_for(-0.4) == "draw"


def test_stub_entry_has_all_spec_fields():
    fixtures = mod.collect_fixtures()
    entry = mod.analysis_stub(fixtures[0])
    # Mirrors the README format spec at
    # dilf/docs/pre_process_corpus/scan/README.md.
    for field in ("verified", "eval_start", "best_move", "pv",
                  "eval_after_pv", "winning_for", "scan_depth", "notes"):
        assert field in entry, f"missing field: {field}"
    assert entry["verified"] is False  # stub → never picked up by writer
    assert entry["pv"] == []


def test_full_skeleton_run_emits_166_entries(tmp_path):
    """End-to-end: stub mode over all fixtures produces 166 entries
    in spec format. Catches regressions in the discovery loop."""
    import subprocess
    out = tmp_path / "scan_stub.json"
    repo_root = Path(__file__).resolve().parents[2]
    subprocess.check_call(
        ["python", str(_SCRIPT), "--output", str(out), "--stub"],
        cwd=str(repo_root),
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 166
    sample = next(iter(data.values()))
    assert sample["verified"] is False
    assert "notes" in sample
