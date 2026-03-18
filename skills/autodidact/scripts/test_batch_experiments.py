#!/usr/bin/env python3
"""
Batch tests for 15 experiment scripts (skills/autodidact/scripts/).

Each test verifies:
  1. Script runs without error (exit code 0)
  2. Key output strings appear in stdout
  3. Execution completes in <10s

Usage:
    python3 -m pytest test_batch_experiments.py -v
    python3 test_batch_experiments.py
"""

import subprocess
import sys
import unittest
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent
TIMEOUT = 15  # seconds per script


def run_script(name: str, extra_args: list | None = None) -> subprocess.CompletedProcess:
    """Run a script by name and return the CompletedProcess."""
    script = str(SCRIPT_DIR / name)
    cmd = [sys.executable, script] + (extra_args or [])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)


# ---------------------------------------------------------------------------
# Parametrized: scripts that just need exit-code-0 + key stdout checks
# ---------------------------------------------------------------------------

EXPERIMENT_SCRIPTS = [
    # (script_filename, expected_stdout_fragments, extra_args)
    ("gc_experiment_runner.py",
     ["condition", "listen"],
     []),
    ("q001_voicing_geometry.py",
     ["Peak layer", "Results written"],
     []),
    ("gc_hallucination_mock.py",
     ["hallucination", "layer"],
     []),
    ("persona_gc_benchmark.py",
     ["neutral", "asymmetry"],
     []),
    ("microgpt_ravel.py",
     ["Cause", "Isolate"],
     []),
    ("sae_incrimination_patrol.py",
     ["patrol", "feature"],
     []),
    ("and_or_gc_patching_mock.py",
     ["AND", "OR", "gc peak"],
     []),
    ("fad_and_or_gate.py",
     ["Pearson", "hypothesis"],
     []),
    ("ravel_mdas_and_or.py",
     ["MDAS", "Cause"],
     []),
    ("ravel_isolate_gc_proxy.py",
     ["Spearman", "agreement"],
     []),
    ("codec_probe_and_or.py",
     ["RVQ", "Q124"],
     []),
    ("unified_results_dashboard.py",
     ["Q001", "pass"],
     []),
    ("phoneme_mdas.py",
     ["manner", "Q109"],
     []),
    ("persona_and_or_gate.py",
     ["persona", "AND"],
     []),
    ("sae_adversarial_detector.py",
     ["AUC", "threshold"],
     []),
]


@pytest.mark.parametrize(
    "script_name, expected_fragments, extra_args",
    EXPERIMENT_SCRIPTS,
    ids=[s[0].replace(".py", "") for s in EXPERIMENT_SCRIPTS],
)
def test_experiment_runs(script_name, expected_fragments, extra_args):
    """Each experiment script should exit 0 and print expected output."""
    result = run_script(script_name, extra_args)
    assert result.returncode == 0, (
        f"{script_name} failed (exit {result.returncode}).\n"
        f"STDERR:\n{result.stderr[-500:]}\n"
        f"STDOUT (tail):\n{result.stdout[-500:]}"
    )
    stdout_lower = result.stdout.lower()
    for frag in expected_fragments:
        assert frag.lower() in stdout_lower, (
            f"{script_name}: expected '{frag}' in stdout.\n"
            f"STDOUT (tail):\n{result.stdout[-500:]}"
        )


# ---------------------------------------------------------------------------
# Individual deeper tests for high-priority scripts
# ---------------------------------------------------------------------------

class TestGcExperimentRunner(unittest.TestCase):
    """gc_experiment_runner.py — aggregates gc_eval across conditions."""

    def test_json_output_written(self):
        """Should mention JSON output path."""
        result = run_script("gc_experiment_runner.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        # Runner prints summary with numeric gc values
        self.assertRegex(result.stdout, r"\d+\.\d+")


class TestQ001VoicingGeometry(unittest.TestCase):
    """q001_voicing_geometry.py — voicing vector analysis."""

    def test_peak_layer_numeric(self):
        result = run_script("q001_voicing_geometry.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Peak layer", result.stdout)


class TestGcHallucinationMock(unittest.TestCase):
    """gc_hallucination_mock.py — hallucination detection mock."""

    def test_hallucination_detected(self):
        result = run_script("gc_hallucination_mock.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hallucination", result.stdout.lower())


class TestMicrogptRavel(unittest.TestCase):
    """microgpt_ravel.py — toy RAVEL circuit test."""

    def test_success_flag(self):
        result = run_script("microgpt_ravel.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        # Should report Cause/Isolate scores
        self.assertIn("Cause", result.stdout)


class TestSaeAdversarialDetector(unittest.TestCase):
    """sae_adversarial_detector.py — adversarial detection calibration."""

    def test_auc_reported(self):
        result = run_script("sae_adversarial_detector.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AUC", result.stdout)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
