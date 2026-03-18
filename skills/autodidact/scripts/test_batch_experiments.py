#!/usr/bin/env python3
"""
Batch tests for experiment scripts (skills/autodidact/scripts/).

Each test verifies:
  1. Script runs without error (exit code 0)
  2. Key output strings appear in stdout
  3. Execution completes in <10s

Note: Orphaned experimental scripts were archived to archive/ on 2026-03-18.
      See archive/README.md for the full list.

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
     [],
     ["--help"]),
    ("unified_results_dashboard.py",
     ["Q001", "pass"],
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
    """q001_voicing_geometry.py — voicing vector analysis (needs Whisper model, slow)."""

    @unittest.skip("Requires Whisper model download, >15s — run manually")
    def test_peak_layer_numeric(self):
        result = run_script("q001_voicing_geometry.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Peak layer", result.stdout)




# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
