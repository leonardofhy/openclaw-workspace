#!/usr/bin/env python3
"""
Regression test suite for autodidact experiment scripts.

Parametrized over golden_baselines.json — runs each script, compares
exit code + key metrics against locked baselines.

Usage:
    python3 -m pytest skills/autodidact/scripts/test_regression.py -v --tb=short
"""
import json
import math
import os
import re
import subprocess
import sys

import pytest

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASELINES_PATH = os.path.join(SCRIPTS_DIR, "golden_baselines.json")

FLOAT_TOL = 1e-6

# ── Script run configurations ────────────────────────────────────────────────
# Maps script name -> (args_list, timeout_seconds)
# Scripts not listed here use default (no extra args, 120s timeout).
SCRIPT_CONFIGS = {
    "cascade_degree.py":          (["--json"], 60),
    "cascade_gsae_density.py":    (["--json"], 60),
    "fad_ravel_cause_isolate.py": (["--json"], 60),
    "gc_eval.py":                 (["--mock", "--json"], 60),
    "gc_experiment_runner.py":    (["--json"], 60),
    "gc_jailbreak_classifier.py": (["--mock"], 60),
    "gc_regression_test.py":      ([], 60),
    "listen_layer_audit.py":      (["--mock"], 60),
    "microgpt_gc_eval.py":        (["--test", "--json"], 120),
    "plot_all_results.py":        ([], 60),
    "plot_q001_q002.py":          ([], 60),
    "sae_listen_layer.py":        (["--test", "--json"], 120),
    "synthetic_stimuli.py":       (["--json"], 60),
    "t3_readiness_check.py":      ([], 60),
    "t5_safety_probe_v1.py":      (["--mock", "--scenario", "both", "--json"], 60),
    "unified_eval.py":            (["--mock", "--json-only"], 60),
    "unified_results_dashboard.py": ([], 60),
}

# ── Load baselines ───────────────────────────────────────────────────────────


def load_baselines():
    if not os.path.exists(BASELINES_PATH):
        pytest.skip(f"No baselines file at {BASELINES_PATH}")
    with open(BASELINES_PATH) as f:
        return json.load(f)


BASELINES = load_baselines()


# ── Discover scripts ─────────────────────────────────────────────────────────


def discover_scripts():
    """Find all non-test, non-dunder .py files in scripts dir."""
    scripts = set()
    for fname in os.listdir(SCRIPTS_DIR):
        if (
            fname.endswith(".py")
            and not fname.startswith("test_")
            and not fname.startswith("__")
            and fname != "capture_baselines.py"
        ):
            scripts.add(fname)
    return scripts


ALL_SCRIPTS = discover_scripts()


# ── Helpers ──────────────────────────────────────────────────────────────────


def parse_r_values(text):
    metrics = {}
    for m in re.finditer(r'[Pp]earson\([^)]*\)\s*=\s*([+-]?\d+\.\d+)', text):
        key = m.group(0).split('=')[0].strip()
        metrics[key] = float(m.group(1))
    for m in re.finditer(r'\br\s*=\s*([+-]?\d+\.\d+)', text):
        metrics['r'] = float(m.group(1))
    return metrics


def parse_pass_fail(text):
    metrics = {}
    passes = len(re.findall(r'(?:PASS|✓|✅)', text))
    fails = len(re.findall(r'(?:FAIL|✗|❌)', text))
    if passes or fails:
        metrics['passes'] = passes
        metrics['fails'] = fails
    return metrics


def parse_json_output(text):
    candidates = []
    brace_depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if brace_depth == 0:
                start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start is not None:
                candidates.append(text[start:i + 1])
                start = None
    for c in reversed(candidates):
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    return None


def extract_key_metrics(json_data):
    if not json_data:
        return {}
    metrics = {}
    for k, v in json_data.items():
        if isinstance(v, (int, float, bool)):
            metrics[k] = v
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, (int, float, bool)):
                    metrics[f'{k}.{k2}'] = v2
    return metrics


def run_experiment(script_name):
    """Run a script and return (exit_code, metrics_dict)."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    args, timeout = SCRIPT_CONFIGS.get(script_name, ([], 120))
    cmd = [sys.executable, script_path] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=SCRIPTS_DIR,
        )
        rc = result.returncode
        combined = result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return -1, {}
    except Exception:
        return -2, {}

    metrics = {}
    metrics.update(parse_r_values(combined))
    metrics.update(parse_pass_fail(combined))
    json_data = parse_json_output(result.stdout)
    if json_data:
        metrics.update(extract_key_metrics(json_data))

    return rc, metrics


def values_match(expected, actual, tol=FLOAT_TOL):
    """Compare two values with float tolerance."""
    if isinstance(expected, float) and isinstance(actual, float):
        if math.isnan(expected) and math.isnan(actual):
            return True
        return abs(expected - actual) < tol
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(expected) - float(actual)) < tol
    return expected == actual


# ── Parametrized tests ───────────────────────────────────────────────────────


def _baseline_scripts():
    """Scripts that have baselines and are runnable."""
    runnable = []
    for name, data in BASELINES.items():
        skip = data.get("skip_reason", "")
        if skip in ("utility_script", "requires_whisper_model", "requires_model_arg"):
            continue
        runnable.append(name)
    return sorted(runnable)


def _skipped_scripts():
    """Scripts with a skip_reason in baselines."""
    skipped = []
    for name, data in BASELINES.items():
        if data.get("skip_reason"):
            skipped.append((name, data["skip_reason"]))
    return sorted(skipped)


def _new_scripts():
    """Scripts on disk that have no baseline entry."""
    return sorted(ALL_SCRIPTS - set(BASELINES.keys()))


# ── Test: exit code + metrics match baseline ─────────────────────────────────


@pytest.mark.parametrize("script_name", _baseline_scripts())
def test_experiment_regression(script_name):
    """Run experiment and compare against golden baseline."""
    baseline = BASELINES[script_name]
    expected_rc = baseline["exit_code"]
    expected_metrics = baseline["key_metrics"]

    actual_rc, actual_metrics = run_experiment(script_name)

    # Check exit code
    assert actual_rc == expected_rc, (
        f"{script_name}: exit code {actual_rc} != expected {expected_rc}"
    )

    # Check each baseline metric exists and matches
    mismatches = []
    for key, expected_val in expected_metrics.items():
        if key not in actual_metrics:
            mismatches.append(f"  missing metric '{key}' (expected {expected_val})")
            continue
        actual_val = actual_metrics[key]
        if not values_match(expected_val, actual_val):
            mismatches.append(
                f"  {key}: {actual_val} != expected {expected_val}"
            )

    assert not mismatches, (
        f"{script_name} metric regression:\n" + "\n".join(mismatches)
    )


# ── Test: skipped scripts are still importable ───────────────────────────────


@pytest.mark.parametrize("script_name,reason", _skipped_scripts())
def test_skipped_script_importable(script_name, reason):
    """Skipped scripts (model-dependent, utility) should at least parse."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    result = subprocess.run(
        [sys.executable, "-c", f"import py_compile; py_compile.compile('{script_path}', doraise=True)"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"{script_name} (skip: {reason}) failed to compile: {result.stderr}"
    )


# ── Test: new scripts without baselines ──────────────────────────────────────


@pytest.mark.parametrize("script_name", _new_scripts() or ["_no_new_scripts_"])
def test_new_script_needs_baseline(script_name):
    """Flag new scripts that need golden baselines (xfail, not hard fail)."""
    if script_name == "_no_new_scripts_":
        pytest.skip("No new scripts found — all have baselines")
    pytest.xfail(
        f"NEW SCRIPT '{script_name}' has no golden baseline. "
        f"Run capture_baselines.py to add it."
    )
