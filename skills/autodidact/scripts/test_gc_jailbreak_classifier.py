#!/usr/bin/env python3
"""
Unit tests for gc_jailbreak_classifier.py — Q045
Run: python3 test_gc_jailbreak_classifier.py
"""

import sys
import json
import unittest
from pathlib import Path

# Ensure scripts directory is on path
sys.path.insert(0, str(Path(__file__).parent))

from gc_jailbreak_classifier import (
    extract_features,
    classify,
    classify_gc_curve,
    generate_mock_curve,
    THRESHOLDS,
)


class TestFeatureExtraction(unittest.TestCase):

    def test_basic_features_present(self):
        curve = generate_mock_curve("listen")
        feats = extract_features(curve)
        required = ["encoder_mean", "decoder_mean", "collapse_ratio",
                    "dec_slope", "peak_to_final", "area_ratio"]
        for key in required:
            self.assertIn(key, feats, f"Missing feature: {key}")

    def test_encoder_decoder_split(self):
        curve = generate_mock_curve("listen", n_enc=4, n_dec=8)
        feats = extract_features(curve)
        self.assertEqual(feats["n_encoder_layers"], 4)
        self.assertEqual(feats["n_decoder_layers"], 8)

    def test_collapse_ratio_range(self):
        for mode in ["listen", "guess", "jailbreak"]:
            curve = generate_mock_curve(mode)
            feats = extract_features(curve)
            self.assertGreaterEqual(feats["collapse_ratio"], 0.0)
            self.assertLessEqual(feats["collapse_ratio"], 1.0)

    def test_jailbreak_has_high_collapse_ratio(self):
        curve = generate_mock_curve("jailbreak")
        feats = extract_features(curve)
        self.assertGreater(feats["collapse_ratio"], 0.3,
                           "Jailbreak curve should have high collapse_ratio")

    def test_listen_has_low_collapse_ratio(self):
        curve = generate_mock_curve("listen")
        feats = extract_features(curve)
        self.assertLess(feats["collapse_ratio"], 0.3,
                        "Listen curve should have low collapse_ratio")


class TestClassifier(unittest.TestCase):

    def test_jailbreak_detected(self):
        curve = generate_mock_curve("jailbreak")
        result = classify_gc_curve(curve)
        self.assertEqual(result["label"], "jailbreak",
                         f"Expected jailbreak, got {result['label']} (conf={result['confidence']})")

    def test_listen_is_benign(self):
        curve = generate_mock_curve("listen")
        result = classify_gc_curve(curve)
        self.assertEqual(result["label"], "benign",
                         f"Expected benign, got {result['label']} (conf={result['confidence']})")

    def test_guess_is_benign(self):
        curve = generate_mock_curve("guess")
        result = classify_gc_curve(curve)
        self.assertEqual(result["label"], "benign",
                         f"Expected benign, got {result['label']} (conf={result['confidence']})")

    def test_confidence_range(self):
        for mode in ["listen", "guess", "jailbreak"]:
            curve = generate_mock_curve(mode)
            result = classify_gc_curve(curve)
            self.assertGreaterEqual(result["confidence"], 0.0)
            self.assertLessEqual(result["confidence"], 1.0)

    def test_result_schema(self):
        curve = generate_mock_curve("jailbreak")
        result = classify_gc_curve(curve)
        self.assertIn("label", result)
        self.assertIn("confidence", result)
        self.assertIn("features", result)
        self.assertIn("rules_triggered", result)
        self.assertIn(result["label"], ["jailbreak", "benign"])

    def test_extreme_collapse(self):
        """Flat encoder, near-zero decoder → should be high confidence jailbreak."""
        import numpy as np
        gc_values = [0.5] * 6 + [0.02, 0.01, 0.02, 0.01, 0.01, 0.02]
        curve = {
            "layers": list(range(12)),
            "gc_values": gc_values,
            "n_encoder_layers": 6,
            "n_decoder_layers": 6,
        }
        result = classify_gc_curve(curve)
        self.assertEqual(result["label"], "jailbreak")
        self.assertGreater(result["confidence"], 0.5)

    def test_uniformly_high(self):
        """Uniformly high gc(k) → clear listen mode, no collapse."""
        gc_values = [0.8] * 12
        curve = {
            "layers": list(range(12)),
            "gc_values": gc_values,
            "n_encoder_layers": 6,
            "n_decoder_layers": 6,
        }
        result = classify_gc_curve(curve)
        self.assertEqual(result["label"], "benign")
        self.assertEqual(len(result["rules_triggered"]), 0)

    def test_uniformly_low(self):
        """Uniformly low gc(k) → model always ignores audio, not collapse per se."""
        gc_values = [0.05] * 12
        curve = {
            "layers": list(range(12)),
            "gc_values": gc_values,
            "n_encoder_layers": 6,
            "n_decoder_layers": 6,
        }
        result = classify_gc_curve(curve)
        # Low overall may trigger decoder_mean rule
        # Just check no crash and valid schema
        self.assertIn(result["label"], ["jailbreak", "benign"])


class TestMultipleSeedsRobustness(unittest.TestCase):

    def test_jailbreak_robust_across_seeds(self):
        """Jailbreak should be correctly labeled across 10 different random seeds."""
        failures = []
        for seed in range(10):
            curve = generate_mock_curve("jailbreak", seed=seed)
            result = classify_gc_curve(curve)
            if result["label"] != "jailbreak":
                failures.append(seed)
        self.assertEqual(failures, [],
                         f"Jailbreak not detected for seeds: {failures}")

    def test_listen_robust_across_seeds(self):
        """Listen mode should be benign across most seeds."""
        failures = []
        for seed in range(10):
            curve = generate_mock_curve("listen", seed=seed)
            result = classify_gc_curve(curve)
            if result["label"] != "benign":
                failures.append(seed)
        # Allow ≤1 false positive (noise can trigger edge cases)
        self.assertLessEqual(len(failures), 1,
                             f"Too many false positives for seeds: {failures}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
