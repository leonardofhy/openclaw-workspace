#!/usr/bin/env python3
"""
Unit tests for synthetic_stimuli.py
Tests with mock Whisper encoder output shapes and gc(k) harness integration.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from synthetic_stimuli import (
    PHONEME_CONTRASTS,
    StimuliConfig,
    generate_activation_pair,
    compute_mock_gc_from_stimuli,
    generate_gc_result_from_stimuli,
)


class TestStimuliConfig(unittest.TestCase):
    def test_default_config_valid(self):
        cfg = StimuliConfig()
        self.assertEqual(cfg.contrast, "vowel_consonant")
        self.assertEqual(cfg.n_encoder_layers, 6)
        self.assertEqual(cfg.n_decoder_layers, 6)

    def test_invalid_contrast_raises(self):
        with self.assertRaises(ValueError):
            StimuliConfig(contrast="nonexistent_contrast")

    def test_all_contrasts_loadable(self):
        for contrast in PHONEME_CONTRASTS:
            cfg = StimuliConfig(contrast=contrast)
            self.assertEqual(cfg.contrast, contrast)


class TestActivationPairShapes(unittest.TestCase):
    """Verify output shapes match expected Whisper-encoder-like format."""

    def setUp(self):
        self.cfg = StimuliConfig(
            n_encoder_layers=6,
            n_decoder_layers=6,
            hidden_dim=64,
            seq_len=8,
            seed=0,
        )

    def test_output_has_correct_keys(self):
        clean, noisy, meta = generate_activation_pair(self.cfg)
        total = self.cfg.n_encoder_layers + self.cfg.n_decoder_layers
        self.assertEqual(len(clean), total)
        self.assertEqual(len(noisy), total)

    def test_activation_shapes(self):
        clean, noisy, meta = generate_activation_pair(self.cfg)
        for k in range(self.cfg.n_encoder_layers + self.cfg.n_decoder_layers):
            self.assertIn(k, clean)
            self.assertIn(k, noisy)
            self.assertEqual(clean[k].shape, (self.cfg.seq_len, self.cfg.hidden_dim))
            self.assertEqual(noisy[k].shape, (self.cfg.seq_len, self.cfg.hidden_dim))

    def test_clean_noisy_differ(self):
        """Clean and noisy activations must not be identical."""
        clean, noisy, _ = generate_activation_pair(self.cfg)
        for k in clean:
            diff = np.abs(clean[k] - noisy[k]).mean()
            self.assertGreater(diff, 0.01, f"Layer {k}: clean≈noisy (diff={diff:.4f})")

    def test_deterministic_with_same_seed(self):
        cfg1 = StimuliConfig(seed=42)
        cfg2 = StimuliConfig(seed=42)
        clean1, noisy1, _ = generate_activation_pair(cfg1)
        clean2, noisy2, _ = generate_activation_pair(cfg2)
        for k in clean1:
            np.testing.assert_array_equal(clean1[k], clean2[k])

    def test_different_seeds_produce_different_output(self):
        cfg1 = StimuliConfig(seed=1)
        cfg2 = StimuliConfig(seed=2)
        clean1, _, _ = generate_activation_pair(cfg1)
        clean2, _, _ = generate_activation_pair(cfg2)
        diffs = [np.abs(clean1[k] - clean2[k]).mean() for k in clean1]
        self.assertGreater(max(diffs), 0.01)

    def test_meta_contains_expected_fields(self):
        _, _, meta = generate_activation_pair(self.cfg)
        for field in ("contrast", "n_encoder_layers", "n_decoder_layers", "hidden_dim"):
            self.assertIn(field, meta)


class TestGcComputation(unittest.TestCase):
    """Test gc(k) computation from synthetic activations."""

    def setUp(self):
        self.cfg = StimuliConfig(
            n_encoder_layers=4,
            n_decoder_layers=4,
            hidden_dim=32,
            seq_len=4,
            seed=99,
        )

    def test_gc_values_in_range(self):
        clean, noisy, _ = generate_activation_pair(self.cfg)
        result = compute_mock_gc_from_stimuli(
            clean, noisy,
            self.cfg.n_encoder_layers,
            self.cfg.n_decoder_layers,
        )
        for v in result["gc_values"]:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_gc_result_has_correct_length(self):
        clean, noisy, _ = generate_activation_pair(self.cfg)
        result = compute_mock_gc_from_stimuli(
            clean, noisy,
            self.cfg.n_encoder_layers,
            self.cfg.n_decoder_layers,
        )
        total = self.cfg.n_encoder_layers + self.cfg.n_decoder_layers
        self.assertEqual(len(result["gc_values"]), total)
        self.assertEqual(len(result["layers"]), total)

    def test_gc_result_format_compatible_with_gc_eval(self):
        """gc_eval.py print_curve expects: layers, gc_values, n_encoder_layers, n_decoder_layers."""
        clean, noisy, _ = generate_activation_pair(self.cfg)
        result = compute_mock_gc_from_stimuli(
            clean, noisy,
            self.cfg.n_encoder_layers,
            self.cfg.n_decoder_layers,
        )
        self.assertIn("layers", result)
        self.assertIn("gc_values", result)
        self.assertIn("n_encoder_layers", result)
        self.assertIn("n_decoder_layers", result)
        self.assertEqual(result["layers"], list(range(8)))


class TestAllContrastsRun(unittest.TestCase):
    """Smoke test: all contrast types should run without error."""

    def test_all_contrasts_produce_valid_gc(self):
        for contrast in PHONEME_CONTRASTS:
            cfg = StimuliConfig(contrast=contrast, n_encoder_layers=4, n_decoder_layers=4,
                                hidden_dim=16, seq_len=4, seed=7)
            result = generate_gc_result_from_stimuli(cfg)
            self.assertEqual(result["contrast"], contrast)
            gc = result["gc_values"]
            self.assertEqual(len(gc), 8)
            self.assertTrue(all(0.0 <= v <= 1.0 for v in gc),
                            f"gc out of range for {contrast}: {gc}")


class TestGcEvalIntegration(unittest.TestCase):
    """Integration test: pipe synthetic stimuli result into gc_eval print_curve."""

    def test_gc_eval_print_curve_accepts_synthetic_output(self):
        """gc_eval.print_curve should not crash on synthetic stimuli output."""
        # Import gc_eval
        import gc_eval
        import io
        from contextlib import redirect_stdout

        cfg = StimuliConfig(n_encoder_layers=6, n_decoder_layers=6,
                            hidden_dim=32, seq_len=4, seed=11)
        result = generate_gc_result_from_stimuli(cfg)

        # Capture stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            gc_eval.print_curve(result)

        output = buf.getvalue()
        self.assertIn("gc(k)", output)
        self.assertIn("enc", output)
        self.assertIn("dec", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
