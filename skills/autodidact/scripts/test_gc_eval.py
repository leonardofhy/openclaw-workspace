#!/usr/bin/env python3
"""
Unit tests for gc_eval.py — gc(k) Evaluation Harness
Track T3: Listen vs Guess (Paper A)

Runs fully on CPU with mock data. No model weights required.

Usage:
    python3 test_gc_eval.py
    python3 -m pytest test_gc_eval.py -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import gc_eval  # noqa: E402

import numpy as np


class TestGenerateMockGcCurve(unittest.TestCase):
    """Test mock curve generation — core Tier 0 functionality."""

    def test_listen_mode_shape(self):
        result = gc_eval.generate_mock_gc_curve(n_encoder_layers=6, n_decoder_layers=6, mode="listen")
        self.assertEqual(len(result["layers"]), 12)
        self.assertEqual(len(result["gc_values"]), 12)
        self.assertEqual(result["n_encoder_layers"], 6)
        self.assertEqual(result["n_decoder_layers"], 6)

    def test_guess_mode_shape(self):
        result = gc_eval.generate_mock_gc_curve(n_encoder_layers=4, n_decoder_layers=4, mode="guess")
        self.assertEqual(len(result["layers"]), 8)
        self.assertEqual(len(result["gc_values"]), 8)

    def test_values_in_range(self):
        for mode in ["listen", "guess"]:
            with self.subTest(mode=mode):
                result = gc_eval.generate_mock_gc_curve(mode=mode)
                vals = result["gc_values"]
                self.assertTrue(all(0.0 <= v <= 1.0 for v in vals),
                                msg=f"gc values out of [0,1] in {mode} mode: {vals}")

    def test_listen_vs_guess_encoder_mean(self):
        """Listen mode should have higher mean gc in encoder than guess mode."""
        listen = gc_eval.generate_mock_gc_curve(mode="listen", seed=0)
        guess = gc_eval.generate_mock_gc_curve(mode="guess", seed=0)
        n_enc = listen["n_encoder_layers"]
        listen_enc_mean = np.mean(listen["gc_values"][:n_enc])
        guess_enc_mean = np.mean(guess["gc_values"][:n_enc])
        self.assertGreater(listen_enc_mean, guess_enc_mean,
                           "listen mode should have higher encoder gc than guess mode")

    def test_listen_vs_guess_decoder_mean(self):
        """Listen mode should have higher decoder gc than guess mode."""
        listen = gc_eval.generate_mock_gc_curve(mode="listen", seed=1)
        guess = gc_eval.generate_mock_gc_curve(mode="guess", seed=1)
        n_enc = listen["n_encoder_layers"]
        listen_dec_mean = np.mean(listen["gc_values"][n_enc:])
        guess_dec_mean = np.mean(guess["gc_values"][n_enc:])
        self.assertGreater(listen_dec_mean, guess_dec_mean,
                           "listen mode should have higher decoder gc than guess mode")

    def test_reproducibility(self):
        """Same seed → same result."""
        r1 = gc_eval.generate_mock_gc_curve(seed=42)
        r2 = gc_eval.generate_mock_gc_curve(seed=42)
        self.assertEqual(r1["gc_values"], r2["gc_values"])

    def test_different_seeds(self):
        """Different seeds → different result."""
        r1 = gc_eval.generate_mock_gc_curve(seed=0)
        r2 = gc_eval.generate_mock_gc_curve(seed=99)
        self.assertNotEqual(r1["gc_values"], r2["gc_values"])

    def test_layers_are_contiguous(self):
        """layers list should be [0, 1, 2, ..., n_enc + n_dec - 1]."""
        result = gc_eval.generate_mock_gc_curve(n_encoder_layers=4, n_decoder_layers=8)
        expected = list(range(12))
        self.assertEqual(result["layers"], expected)

    def test_method_field(self):
        result = gc_eval.generate_mock_gc_curve()
        self.assertIn("method", result)
        self.assertEqual(result["method"], "mock_causal_patch")

    def test_custom_layer_counts(self):
        result = gc_eval.generate_mock_gc_curve(n_encoder_layers=2, n_decoder_layers=3)
        self.assertEqual(result["n_encoder_layers"], 2)
        self.assertEqual(result["n_decoder_layers"], 3)
        self.assertEqual(len(result["gc_values"]), 5)


class TestPrintCurve(unittest.TestCase):
    """Test the print_curve function runs without error."""

    def test_print_listen(self):
        import io
        from contextlib import redirect_stdout
        result = gc_eval.generate_mock_gc_curve(mode="listen")
        buf = io.StringIO()
        with redirect_stdout(buf):
            gc_eval.print_curve(result)
        output = buf.getvalue()
        self.assertIn("gc(k)", output)
        self.assertIn("enc", output)
        self.assertIn("dec", output)
        self.assertIn("Peak layer", output)

    def test_print_guess(self):
        import io
        from contextlib import redirect_stdout
        result = gc_eval.generate_mock_gc_curve(mode="guess")
        buf = io.StringIO()
        with redirect_stdout(buf):
            gc_eval.print_curve(result)
        output = buf.getvalue()
        self.assertIn("Mean gc", output)


class TestCLI(unittest.TestCase):
    """Test CLI invocation end-to-end (subprocess, no model)."""

    SCRIPT = str(SCRIPT_DIR / "gc_eval.py")

    def _run(self, args: list) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, self.SCRIPT] + args,
            capture_output=True, text=True, timeout=15
        )

    def test_mock_listen(self):
        result = self._run(["--mock", "--mock-mode", "listen"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("gc(k)", result.stdout)

    def test_mock_guess(self):
        result = self._run(["--mock", "--mock-mode", "guess"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("gc(k)", result.stdout)

    def test_mock_json_output(self):
        result = self._run(["--mock", "--json"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("gc_values", data)
        self.assertIn("layers", data)
        self.assertIn("n_encoder_layers", data)
        self.assertIn("n_decoder_layers", data)

    def test_missing_audio_without_mock(self):
        """Should fail gracefully when audio files not provided."""
        result = self._run(["--model-name", "openai/whisper-tiny"])
        self.assertNotEqual(result.returncode, 0)

    def test_json_values_in_range(self):
        result = self._run(["--mock", "--json"])
        data = json.loads(result.stdout)
        vals = data["gc_values"]
        for v in vals:
            self.assertGreaterEqual(v, 0.0, "gc value below 0")
            self.assertLessEqual(v, 1.0, "gc value above 1")


class TestGcCurveInterpretability(unittest.TestCase):
    """
    Interpretability properties of gc(k) curves.
    These encode assumptions about how listen/guess modes should differ —
    useful as regression tests when the method changes.
    """

    def test_listen_encoder_rising_trend(self):
        """Listen mode: gc should generally rise through encoder (first half)."""
        result = gc_eval.generate_mock_gc_curve(mode="listen", n_encoder_layers=6, seed=42)
        enc = result["gc_values"][:6]
        # First layer should be lower than last encoder layer
        self.assertLess(enc[0], enc[-1],
                        "Listen mode: gc should rise through encoder layers")

    def test_guess_decoder_falling_trend(self):
        """Guess mode: gc should collapse in decoder (model ignores audio)."""
        result = gc_eval.generate_mock_gc_curve(mode="guess", n_encoder_layers=6, n_decoder_layers=6, seed=42)
        dec = result["gc_values"][6:]
        # Decoder gc should drop: first > last
        self.assertGreater(dec[0], dec[-1],
                           "Guess mode: gc should fall through decoder layers")

    def test_gc_curve_serializable(self):
        """Result should be JSON-serializable (for pipeline integration)."""
        result = gc_eval.generate_mock_gc_curve()
        serialized = json.dumps(result)
        reloaded = json.loads(serialized)
        self.assertAlmostEqual(result["gc_values"][0], reloaded["gc_values"][0], places=6)


# ---------------------------------------------------------------------------
# AC-11 RAVEL Causal Isolation Tests
# ---------------------------------------------------------------------------

class TestAC11RavelCausalIsolation(unittest.TestCase):
    """5 unit tests for AC-11: RAVEL causal isolation check.

    AC-11 verifies that ablating listen-layer features causally reduces
    jailbreak score (RAVEL Cause criterion). Three evaluation paths:
      1. Full RAVEL scores (ravel_cause_score, optional ravel_isolate_score)
      2. Proxy check: listen mode + high encoder gc
      3. Skip: no RAVEL data, non-listen mode
    """

    def _make_result(self, mode="listen", ravel_cause=None, ravel_isolate=None,
                     n_enc=6, n_dec=6, enc_mean=0.7):
        """Build a minimal result dict for AC-11 testing."""
        # Construct gc values: flat encoder at enc_mean, flat decoder at 0.3
        enc_vals = [enc_mean] * n_enc
        dec_vals = [0.3] * n_dec
        gc_vals = enc_vals + dec_vals
        result = {
            "layers": list(range(n_enc + n_dec)),
            "gc_values": gc_vals,
            "n_encoder_layers": n_enc,
            "n_decoder_layers": n_dec,
            "method": "mock_causal_patch",
            "mode": mode,
        }
        if ravel_cause is not None:
            result["ravel_cause_score"] = ravel_cause
        if ravel_isolate is not None:
            result["ravel_isolate_score"] = ravel_isolate
        return result

    def test_ac11_passes_with_strong_ravel_cause_score(self):
        """AC-11 PASS: ravel_cause_score >= threshold (ablation has clear causal effect)."""
        result = self._make_result(ravel_cause=0.45)
        checker = gc_eval.AntiConfoundChecker()
        gc = np.array(result["gc_values"])
        check = checker._ac11_ravel_causal_isolation(result, gc)
        self.assertTrue(check.passed,
                        f"Expected AC-11 PASS with cause=0.45, got FAIL: {check.detail}")
        self.assertIn("cause=0.450", check.detail)

    def test_ac11_fails_with_low_cause_score(self):
        """AC-11 FAIL: ravel_cause_score too low (ablation has no meaningful causal effect)."""
        result = self._make_result(ravel_cause=0.05)
        checker = gc_eval.AntiConfoundChecker(min_ravel_cause=0.2)
        gc = np.array(result["gc_values"])
        check = checker._ac11_ravel_causal_isolation(result, gc)
        self.assertFalse(check.passed,
                         f"Expected AC-11 FAIL with cause=0.05, got PASS: {check.detail}")
        self.assertIn("0.050", check.detail)

    def test_ac11_fails_with_low_isolate_score(self):
        """AC-11 FAIL: cause ok but ravel_isolate_score too low (ablation not surgically specific)."""
        # cause is good (0.4 >= 0.2), but isolate is too low (0.3 < 0.5)
        result = self._make_result(ravel_cause=0.40, ravel_isolate=0.30)
        checker = gc_eval.AntiConfoundChecker(min_ravel_cause=0.2, min_ravel_isolate=0.5)
        gc = np.array(result["gc_values"])
        check = checker._ac11_ravel_causal_isolation(result, gc)
        self.assertFalse(check.passed,
                         f"Expected AC-11 FAIL with isolate=0.30, got PASS: {check.detail}")
        self.assertIn("isolate", check.detail)

    def test_ac11_proxy_pass_listen_mode_high_gc(self):
        """AC-11 proxy PASS: listen mode, no RAVEL scores, high encoder gc >= 0.45."""
        result = self._make_result(mode="listen", enc_mean=0.72)
        checker = gc_eval.AntiConfoundChecker()
        gc = np.array(result["gc_values"])
        check = checker._ac11_ravel_causal_isolation(result, gc)
        self.assertTrue(check.passed,
                        f"Expected proxy PASS with enc_mean=0.72, got FAIL: {check.detail}")
        self.assertIn("PROXY", check.detail)
        self.assertIn("necessary condition", check.detail)

    def test_ac11_skip_non_listen_mode_no_ravel(self):
        """AC-11 skip (PASS): guess mode, no RAVEL scores — cannot infer causal direction."""
        result = self._make_result(mode="guess", enc_mean=0.3)
        checker = gc_eval.AntiConfoundChecker()
        gc = np.array(result["gc_values"])
        check = checker._ac11_ravel_causal_isolation(result, gc)
        self.assertTrue(check.passed,
                        f"Expected AC-11 SKIP (pass) for guess mode with no RAVEL data: {check.detail}")
        self.assertIn("Skipped", check.detail)

    def test_ac11_integrated_in_full_checker_listen_mode(self):
        """AC-11 appears in full AntiConfoundReport (11 checks total)."""
        result = gc_eval.generate_mock_gc_curve(mode="listen", seed=42)
        checker = gc_eval.AntiConfoundChecker()
        report = checker.run(result)
        self.assertEqual(len(report.checks), 11, "Checker should now run 11 checks (AC-01..AC-11)")
        ac11 = report.checks[-1]
        self.assertEqual(ac11.name, "AC-11:ravel-causal-isolation")
        self.assertTrue(ac11.passed, f"AC-11 should pass for listen mode mock: {ac11.detail}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestGenerateMockGcCurve))
    suite.addTests(loader.loadTestsFromTestCase(TestPrintCurve))
    suite.addTests(loader.loadTestsFromTestCase(TestCLI))
    suite.addTests(loader.loadTestsFromTestCase(TestGcCurveInterpretability))
    suite.addTests(loader.loadTestsFromTestCase(TestAC11RavelCausalIsolation))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
