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
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestGenerateMockGcCurve))
    suite.addTests(loader.loadTestsFromTestCase(TestPrintCurve))
    suite.addTests(loader.loadTestsFromTestCase(TestCLI))
    suite.addTests(loader.loadTestsFromTestCase(TestGcCurveInterpretability))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
