#!/usr/bin/env python3
"""
Batch subprocess smoke tests for experiment scripts.

Runs each script as a subprocess and asserts exit code == 0.
Scripts that are too slow for bare invocation use --help instead.

Usage:
    python3 -m pytest test_batch_subprocess.py -v --tb=short
"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent

# Scripts that need --help because bare invocation is too slow (>10s)
HELP_ONLY = {
    "q001_voicing_geometry.py",
    "q002_causal_contribution.py",
}

SCRIPTS = [
    "gc_experiment_runner.py",
    "q001_voicing_geometry.py",
    "q002_causal_contribution.py",
    "persona_gc_benchmark.py",
    "microgpt_ravel.py",
    "sae_incrimination_patrol.py",
    "and_or_gc_patching_mock.py",
    "fad_and_or_gate.py",
    "unified_results_dashboard.py",
    "ravel_mdas_and_or.py",
    "ravel_isolate_gc_proxy.py",
    "codec_probe_and_or.py",
    "persona_and_or_gate.py",
    "sae_adversarial_detector.py",
    "cascade_degree.py",
    "backdoor_cascade.py",
    "emotion_and_or_gate.py",
    "phoneme_mdas.py",
    "collapse_onset_and_or.py",
    "gc_incrimination_mock.py",
]


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_runs(script: str) -> None:
    """Each experiment script should exit 0 when invoked."""
    path = SCRIPT_DIR / script
    assert path.exists(), f"Script not found: {path}"

    cmd = [sys.executable, str(path)]
    if script in HELP_ONLY:
        cmd.append("--help")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (
        f"{script} exited with code {result.returncode}\n"
        f"--- stderr ---\n{result.stderr[-500:]}"
    )
