#!/usr/bin/env python3
"""
gc(k) Regression Suite — Acoustic Feature Drift (Tier 0)
Track T3: Listen vs Guess (Paper A)

Tests whether the listen-layer boundary (the gc(k) peak / inflection point
separating "audio-driven" encoder layers from "prior-driven" decoder layers)
remains stable under parameterised acoustic perturbations applied to the
mock gc(k) curve.

Perturbations model common real-world drift risks:
  - additive noise (measurement noise in activation patching)
  - SNR scaling (weak audio signal → listen-layer should shift or collapse)
  - encoder layer count variation (architecture sensitivity)
  - decoder layer count variation
  - temperature/randomness in curve generation

Assertions check:
  1. Listen-layer BOUNDARY STABILITY — the encoder peak index doesn't jump by
     more than ±2 layers across perturbation levels
  2. LISTEN/GUESS SEPARABILITY — mean encoder gc(listen) > mean encoder gc(guess)
     even after perturbation
  3. VALUE RANGE — all gc values remain in [0, 1] after perturbation
  4. NON-DEGENERATE CURVE — gc std > 0.02 (curve not flat)
  5. ENCODER DOMINANCE (listen mode) — mean encoder gc > mean decoder gc

Usage:
    python3 gc_regression_test.py
    python3 -m pytest gc_regression_test.py -v

All tests run on CPU with mock data (no model weights required). CI-ready.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import gc_eval  # noqa: E402


# ---------------------------------------------------------------------------
# Perturbation helpers
# ---------------------------------------------------------------------------

def apply_additive_noise(gc_values: list[float], std: float, seed: int = 0) -> list[float]:
    """Add Gaussian noise to gc(k) curve (models patching measurement noise)."""
    rng = np.random.default_rng(seed)
    arr = np.array(gc_values) + rng.normal(0, std, len(gc_values))
    return np.clip(arr, 0.0, 1.0).tolist()


def apply_snr_scaling(gc_values: list[float], snr_scale: float) -> list[float]:
    """Scale gc values by snr_scale (models weak audio signal → lower gc)."""
    arr = np.clip(np.array(gc_values) * snr_scale, 0.0, 1.0)
    return arr.tolist()


def listen_layer_boundary(gc_values: list[float], n_encoder_layers: int) -> int:
    """
    Return the index of the peak gc(k) within the encoder block.
    The 'listen layer' is where audio evidence is most causally active.
    """
    encoder_gc = np.array(gc_values[:n_encoder_layers])
    return int(np.argmax(encoder_gc))


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestGcRegressionAdditivNoise(unittest.TestCase):
    """
    Boundary stability under increasing additive noise levels.
    The listen-layer peak should not shift by more than ±2 layers.
    """

    NOISE_LEVELS = [0.01, 0.03, 0.05, 0.08, 0.10]
    N_ENC = 6
    N_DEC = 6

    def _baseline_boundary(self) -> int:
        base = gc_eval.generate_mock_gc_curve(
            n_encoder_layers=self.N_ENC,
            n_decoder_layers=self.N_DEC,
            mode="listen",
            seed=0,
        )
        return listen_layer_boundary(base["gc_values"], self.N_ENC)

    def test_boundary_stability_under_noise(self):
        """Peak listen-layer index must not drift >2 positions at any noise level."""
        baseline = self._baseline_boundary()
        for noise_std in self.NOISE_LEVELS:
            for trial in range(5):
                base = gc_eval.generate_mock_gc_curve(
                    n_encoder_layers=self.N_ENC,
                    n_decoder_layers=self.N_DEC,
                    mode="listen",
                    seed=trial,
                )
                perturbed = apply_additive_noise(base["gc_values"], std=noise_std, seed=trial + 100)
                boundary = listen_layer_boundary(perturbed, self.N_ENC)
                self.assertLessEqual(
                    abs(boundary - baseline), 2,
                    msg=f"noise_std={noise_std} trial={trial}: boundary shifted from "
                        f"{baseline} to {boundary} (drift={abs(boundary - baseline)})",
                )

    def test_values_in_range_after_noise(self):
        """gc values must remain in [0, 1] after noise application."""
        for noise_std in self.NOISE_LEVELS:
            base = gc_eval.generate_mock_gc_curve(mode="listen", seed=7)
            perturbed = apply_additive_noise(base["gc_values"], std=noise_std, seed=77)
            for i, v in enumerate(perturbed):
                self.assertGreaterEqual(v, 0.0, msg=f"noise_std={noise_std} layer {i}: gc={v} < 0")
                self.assertLessEqual(v, 1.0, msg=f"noise_std={noise_std} layer {i}: gc={v} > 1")

    def test_non_degenerate_curve_after_noise(self):
        """Curve must remain non-flat (std > 0.02) even after noise."""
        base = gc_eval.generate_mock_gc_curve(mode="listen", seed=3)
        perturbed = apply_additive_noise(base["gc_values"], std=0.10, seed=33)
        std = np.std(perturbed)
        self.assertGreater(std, 0.02, msg=f"gc curve is near-flat after noise: std={std:.4f}")


class TestGcRegressionSnrScaling(unittest.TestCase):
    """
    Listen/guess separability under SNR scaling.
    Even with signal degradation, listen mode must stay above guess mode.
    """

    SNR_SCALES = [1.0, 0.8, 0.6, 0.5]  # 0.5 = 6 dB loss
    N_ENC = 6
    N_DEC = 6

    def test_listen_guess_separability_under_snr(self):
        """mean encoder gc(listen) > mean encoder gc(guess) at all SNR scales."""
        for scale in self.SNR_SCALES:
            listen = gc_eval.generate_mock_gc_curve(
                n_encoder_layers=self.N_ENC, n_decoder_layers=self.N_DEC,
                mode="listen", seed=42,
            )
            guess = gc_eval.generate_mock_gc_curve(
                n_encoder_layers=self.N_ENC, n_decoder_layers=self.N_DEC,
                mode="guess", seed=42,
            )
            listen_enc = np.mean(apply_snr_scaling(listen["gc_values"][:self.N_ENC], scale))
            guess_enc = np.mean(apply_snr_scaling(guess["gc_values"][:self.N_ENC], scale))
            self.assertGreater(
                listen_enc, guess_enc,
                msg=f"snr_scale={scale}: listen_enc={listen_enc:.3f} <= guess_enc={guess_enc:.3f}",
            )

    def test_decoder_elevation_listen_vs_guess_after_snr(self):
        """
        In listen mode, decoder gc stays elevated (no collapse) vs guess mode
        where decoder collapses. Even after SNR scaling, listen decoder gc
        must exceed guess decoder gc — this is the key 'listen-layer' signal.
        """
        for scale in self.SNR_SCALES:
            listen = gc_eval.generate_mock_gc_curve(
                n_encoder_layers=self.N_ENC, n_decoder_layers=self.N_DEC,
                mode="listen", seed=5,
            )
            guess = gc_eval.generate_mock_gc_curve(
                n_encoder_layers=self.N_ENC, n_decoder_layers=self.N_DEC,
                mode="guess", seed=5,
            )
            listen_dec = np.mean(apply_snr_scaling(listen["gc_values"][self.N_ENC:], scale))
            guess_dec = np.mean(apply_snr_scaling(guess["gc_values"][self.N_ENC:], scale))
            self.assertGreater(
                listen_dec, guess_dec,
                msg=f"snr_scale={scale}: listen decoder gc ({listen_dec:.3f}) should exceed "
                    f"guess decoder gc ({guess_dec:.3f}) — listen mode must not collapse in decoder",
            )

    def test_values_in_range_after_snr(self):
        """gc values must remain in [0, 1] after SNR scaling."""
        for scale in self.SNR_SCALES:
            base = gc_eval.generate_mock_gc_curve(mode="listen", seed=9)
            perturbed = apply_snr_scaling(base["gc_values"], scale)
            for i, v in enumerate(perturbed):
                self.assertGreaterEqual(v, 0.0, msg=f"scale={scale} layer {i}: gc={v} < 0")
                self.assertLessEqual(v, 1.0, msg=f"scale={scale} layer {i}: gc={v} > 1")


class TestGcRegressionArchitectureVariation(unittest.TestCase):
    """
    Boundary stability across different encoder/decoder sizes.
    Tests that gc(k) harness is robust to architecture parameter changes.
    """

    CONFIGS = [
        (4, 4),   # whisper-tiny-like
        (6, 6),   # default mock
        (12, 4),  # encoder-heavy
        (4, 12),  # decoder-heavy
        (8, 8),   # medium
    ]

    def test_listen_guess_separability_across_architectures(self):
        """Listen/guess separability must hold for all architecture configs."""
        for (n_enc, n_dec) in self.CONFIGS:
            listen = gc_eval.generate_mock_gc_curve(
                n_encoder_layers=n_enc, n_decoder_layers=n_dec,
                mode="listen", seed=42,
            )
            guess = gc_eval.generate_mock_gc_curve(
                n_encoder_layers=n_enc, n_decoder_layers=n_dec,
                mode="guess", seed=42,
            )
            listen_enc = np.mean(listen["gc_values"][:n_enc])
            guess_enc = np.mean(guess["gc_values"][:n_enc])
            self.assertGreater(
                listen_enc, guess_enc,
                msg=f"n_enc={n_enc} n_dec={n_dec}: listen_enc={listen_enc:.3f} "
                    f"<= guess_enc={guess_enc:.3f}",
            )

    def test_value_range_across_architectures(self):
        """gc values must always be in [0, 1] regardless of architecture."""
        for (n_enc, n_dec) in self.CONFIGS:
            for mode in ["listen", "guess"]:
                result = gc_eval.generate_mock_gc_curve(
                    n_encoder_layers=n_enc, n_decoder_layers=n_dec,
                    mode=mode, seed=0,
                )
                vals = result["gc_values"]
                self.assertEqual(len(vals), n_enc + n_dec,
                    msg=f"wrong curve length for n_enc={n_enc} n_dec={n_dec}")
                for v in vals:
                    self.assertGreaterEqual(v, 0.0)
                    self.assertLessEqual(v, 1.0)

    def test_boundary_within_encoder_block(self):
        """Listen-layer boundary index must lie within the encoder block (< n_enc)."""
        for (n_enc, n_dec) in self.CONFIGS:
            base = gc_eval.generate_mock_gc_curve(
                n_encoder_layers=n_enc, n_decoder_layers=n_dec,
                mode="listen", seed=42,
            )
            boundary = listen_layer_boundary(base["gc_values"], n_enc)
            self.assertGreaterEqual(boundary, 0, msg=f"boundary < 0 for n_enc={n_enc}")
            self.assertLess(boundary, n_enc, msg=f"boundary {boundary} >= n_enc={n_enc}")


class TestGcRegressionCombined(unittest.TestCase):
    """
    Combined perturbation: noise + SNR scaling simultaneously.
    Stress test for robustness under multiple degradation sources.
    """

    def test_combined_noise_and_snr(self):
        """
        After noise + SNR scaling, listen/guess separability must hold
        and all values must be in [0, 1].
        """
        n_enc, n_dec = 6, 6
        for noise_std in [0.03, 0.07]:
            for snr_scale in [0.8, 0.6]:
                for seed in range(5):
                    listen = gc_eval.generate_mock_gc_curve(
                        n_encoder_layers=n_enc, n_decoder_layers=n_dec,
                        mode="listen", seed=seed,
                    )
                    guess = gc_eval.generate_mock_gc_curve(
                        n_encoder_layers=n_enc, n_decoder_layers=n_dec,
                        mode="guess", seed=seed,
                    )
                    listen_perturbed = apply_snr_scaling(
                        apply_additive_noise(listen["gc_values"], noise_std, seed),
                        snr_scale,
                    )
                    guess_perturbed = apply_snr_scaling(
                        apply_additive_noise(guess["gc_values"], noise_std, seed),
                        snr_scale,
                    )
                    listen_enc = np.mean(listen_perturbed[:n_enc])
                    guess_enc = np.mean(guess_perturbed[:n_enc])
                    self.assertGreater(
                        listen_enc, guess_enc,
                        msg=f"noise={noise_std} snr={snr_scale} seed={seed}: separability lost "
                            f"(listen_enc={listen_enc:.3f}, guess_enc={guess_enc:.3f})",
                    )
                    for v in listen_perturbed + guess_perturbed:
                        self.assertGreaterEqual(v, 0.0)
                        self.assertLessEqual(v, 1.0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
