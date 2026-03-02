#!/usr/bin/env python3
"""
Unit tests for listen_layer_audit.py (mock mode, Tier 0 — no model required)
Track T5: Listen-Layer Audit (Paper C / MATS)
"""
import subprocess
import json
import sys
import os

SCRIPT = os.path.join(os.path.dirname(__file__), "listen_layer_audit.py")


def run_mock():
    result = subprocess.run(
        [sys.executable, SCRIPT, "--mock"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)


def test_output_structure():
    out = run_mock()
    assert "model" in out
    assert "n_layers" in out
    assert "layers" in out
    assert "listen_layer_candidate" in out
    assert "alert" in out
    assert "summary" in out
    print("✅ test_output_structure: PASS")


def test_layer_fields():
    out = run_mock()
    n = out["n_layers"]
    assert n > 0
    for i in range(n):
        layer = out["layers"][str(i)]
        assert "safety_score" in layer, f"Layer {i} missing safety_score"
        assert "gc_k" in layer, f"Layer {i} missing gc_k"
        assert 0.0 <= layer["safety_score"] <= 1.0, f"safety_score out of range at layer {i}"
        assert 0.0 <= layer["gc_k"] <= 1.0, f"gc_k out of range at layer {i}"
    print(f"✅ test_layer_fields: PASS (n_layers={n})")


def test_listen_layer_candidate():
    out = run_mock()
    candidate = out["listen_layer_candidate"]
    n = out["n_layers"]
    assert isinstance(candidate, int)
    assert 0 <= candidate < n, f"listen_layer_candidate {candidate} out of bounds"
    # Candidate should have high gc_k (audio-dominant)
    gc = out["layers"][str(candidate)]["gc_k"]
    assert gc > 0.5, f"Listen layer gc(k)={gc:.3f} unexpectedly low"
    print(f"✅ test_listen_layer_candidate: PASS (layer {candidate}, gc(k)={gc:.3f})")


def test_alert_flag():
    out = run_mock()
    assert isinstance(out["alert"], bool)
    print(f"✅ test_alert_flag: PASS (alert={out['alert']})")


def test_summary_string():
    out = run_mock()
    s = out["summary"]
    assert isinstance(s, str) and len(s) > 10
    assert "listen" in s.lower() or "layer" in s.lower()
    print(f"✅ test_summary_string: PASS")


if __name__ == "__main__":
    print("Running listen_layer_audit unit tests (mock mode)...")
    tests = [
        test_output_structure,
        test_layer_fields,
        test_listen_layer_candidate,
        test_alert_flag,
        test_summary_string,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"❌ {t.__name__}: FAIL — {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {len(tests)-failed}/{len(tests)} passed")
    sys.exit(0 if failed == 0 else 1)
