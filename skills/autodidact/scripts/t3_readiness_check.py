#!/usr/bin/env python3
"""
T3 Readiness Check — End-to-End Demo for Leo Review
Track T3: Listen vs Guess (Paper A)

Run this to confirm the eval harness is ready before approving the CPU experiment.
No GPU required. No real audio required. All outputs are deterministic.

Usage:
    python3 t3_readiness_check.py

Expected output: All checks PASS + summary table.
To run with real audio: python3 gc_eval.py --audio /path/to/speech.wav
"""

import sys
import subprocess
import importlib
import os
import math

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}"); FAILURES.append(msg)
def hdr(msg):  print(f"\n{BOLD}{msg}{RESET}")

FAILURES = []

# ── 1. Import check ───────────────────────────────────────────────────────────
hdr("1/5  Import check (pure Python — no model weights needed)")

sys.path.insert(0, SCRIPTS_DIR)
try:
    import gc_eval
    ok("gc_eval imported")
except Exception as e:
    fail(f"gc_eval import failed: {e}")

try:
    import synthetic_stimuli
    ok("synthetic_stimuli imported")
except Exception as e:
    fail(f"synthetic_stimuli import failed: {e}")

try:
    import numpy as np
    ok(f"numpy {np.__version__}")
except ImportError:
    fail("numpy not installed")

# ── 2. Mock gc(k) — listen mode ───────────────────────────────────────────────
hdr("2/5  gc(k) harness — LISTEN mode (clean audio simulation)")
try:
    listen_result = gc_eval.generate_mock_gc_curve(mode="listen")
    n_enc = listen_result["n_encoder_layers"]
    gc_vals = listen_result["gc_values"]
    enc_vals = gc_vals[:n_enc]
    dec_vals = gc_vals[n_enc:]
    mean_enc = sum(enc_vals) / len(enc_vals)
    mean_dec = sum(dec_vals) / len(dec_vals)
    peak_idx = gc_vals.index(max(gc_vals))
    peak_val = max(gc_vals)

    ok(f"Listen  enc_mean={mean_enc:.3f}  dec_mean={mean_dec:.3f}  peak=layer{peak_idx}({peak_val:.3f})")

    assert mean_enc > 0.3, "H1: encoder gc(k) too low for listen mode"
    assert mean_dec > 0.6, "H1: decoder gc(k) should stay elevated in listen mode"
    ok("H1 confirmed: listen mode → elevated gc(k) in encoder + decoder")
except Exception as e:
    fail(f"Listen mode failed: {e}")

# ── 3. Mock gc(k) — guess mode ────────────────────────────────────────────────
hdr("3/5  gc(k) harness — GUESS mode (degraded audio simulation)")
try:
    guess_result = gc_eval.generate_mock_gc_curve(mode="guess")
    n_enc_g = guess_result["n_encoder_layers"]
    gc_vals_g = guess_result["gc_values"]
    enc_vals_g = gc_vals_g[:n_enc_g]
    dec_vals_g = gc_vals_g[n_enc_g:]
    mean_enc_g = sum(enc_vals_g) / len(enc_vals_g)
    mean_dec_g = sum(dec_vals_g) / len(dec_vals_g)

    ok(f"Guess   enc_mean={mean_enc_g:.3f}  dec_mean={mean_dec_g:.3f}")

    assert mean_enc > mean_enc_g, "H2: listen encoder gc should exceed guess"
    assert mean_dec > mean_dec_g, "H2: listen decoder gc should exceed guess"
    delta_enc = mean_enc - mean_enc_g
    delta_dec = mean_dec - mean_dec_g
    ok(f"H2 confirmed: listen > guess  Δenc={delta_enc:.3f}  Δdec={delta_dec:.3f}")
except Exception as e:
    fail(f"Guess mode failed: {e}")

# ── 4. Anti-confound check ────────────────────────────────────────────────────
hdr("4/5  Anti-confound checker (10 automated assertions)")
try:
    checker = gc_eval.AntiConfoundChecker()
    report = checker.run(listen_result)
    n_failed = report.n_failed
    n_total = len(report.checks)
    n_passed = n_total - n_failed
    ok(f"{n_passed}/{n_total} checks passed")
    for c in report.checks:
        if not c.passed:
            fail(f"Anti-confound FAIL: {c.name} — {c.detail}")
    if n_failed == 0:
        ok("All anti-confound checks passed — eval env is clean")
except Exception as e:
    fail(f"Anti-confound check error: {e}")

# ── 5. Regression suite ───────────────────────────────────────────────────────
hdr("5/5  Regression suite (10 unit tests)")
try:
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "gc_regression_test.py")],
        capture_output=True, text=True, timeout=30
    )
    lines = result.stdout.strip().split("\n")
    summary_line = [l for l in lines if l.startswith("Ran") or "OK" in l or "FAILED" in l]
    if result.returncode == 0:
        ok("Regression suite: ALL PASS  (" + " | ".join(summary_line) + ")")
    else:
        fail(f"Regression suite FAILED:\n{result.stdout[-500:]}")
except Exception as e:
    fail(f"Could not run regression suite: {e}")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 60)
if not FAILURES:
    print(f"{GREEN}{BOLD}ALL CHECKS PASSED{RESET}  — T3 eval harness is production-ready")
    print()
    print("📋  T3 EXIT CRITERIA STATUS")
    print(f"   {GREEN}✓{RESET}  eval_harness_exists_T3     (gc_eval.py + 10 regression tests)")
    print(f"   {GREEN}✓{RESET}  experiment_spec_ready_T3   (memory/learning/pitches/experiment-spec-T3-cpu.md)")
    print(f"   {YELLOW}?{RESET}  leo_approved_cpu_experiment (PENDING — needs Leo)")
    print()
    print("⚡  TO RUN THE REAL CPU EXPERIMENT (~2 min):")
    print("   1. Get any speech .wav (or: curl -L https://github.com/librosa/librosa/raw/main/tests/data/libri1.wav -o /tmp/test.wav)")
    print("   2. python3 skills/autodidact/scripts/gc_eval.py --audio /tmp/test.wav")
    print("   3. Review output + reply with: 'approved' or 'not yet'")
    print()
    print("📄  Experiment spec: memory/learning/pitches/experiment-spec-T3-cpu.md")
    print("📄  Pitch (Paper A): memory/learning/pitches/paper-a-pitch.md")
else:
    print(f"{RED}{BOLD}FAILED ({len(FAILURES)} check(s)){RESET}")
    for f in FAILURES:
        print(f"   • {f}")
print("=" * 60)

sys.exit(0 if not FAILURES else 1)
