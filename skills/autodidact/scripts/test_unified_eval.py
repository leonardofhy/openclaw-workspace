#!/usr/bin/env python3
"""Unit tests for unified_eval.py (Tier 0 — mock mode only)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from unified_eval import run_mock_eval, SAFETY_THRESHOLD, AUDIO_DOMINANT_THRESHOLD


class TestUnifiedEvalStructure(unittest.TestCase):
    """Test output JSON schema is correct."""

    def setUp(self):
        self.result = run_mock_eval(gc_mode="listen", test_variant="jailbreak")

    def test_top_level_keys(self):
        for key in ("mode", "model", "n_layers", "gc_curve", "safety_audit", "unified_verdict"):
            self.assertIn(key, self.result, f"Missing key: {key}")

    def test_mode_is_mock(self):
        self.assertEqual(self.result["mode"], "mock")

    def test_n_layers(self):
        self.assertEqual(self.result["n_layers"], 12)  # 6 enc + 6 dec

    def test_gc_curve_keys(self):
        gc = self.result["gc_curve"]
        for k in ("layers", "gc_values", "mean_encoder_gc", "mean_decoder_gc", "peak_layer"):
            self.assertIn(k, gc)

    def test_gc_values_range(self):
        for v in self.result["gc_curve"]["gc_values"]:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_gc_layers_count(self):
        gc = self.result["gc_curve"]
        self.assertEqual(len(gc["layers"]), self.result["n_layers"])
        self.assertEqual(len(gc["gc_values"]), self.result["n_layers"])

    def test_safety_audit_keys(self):
        audit = self.result["safety_audit"]
        for k in ("layers", "listen_layer_candidate", "alert", "safety_threshold", "summary"):
            self.assertIn(k, audit)

    def test_safety_scores_range(self):
        for data in self.result["safety_audit"]["layers"].values():
            self.assertGreaterEqual(data["safety_score"], 0.0)
            self.assertLessEqual(data["safety_score"], 1.0)

    def test_safety_layers_have_gc_k(self):
        for k_str, data in self.result["safety_audit"]["layers"].items():
            self.assertIn("gc_k", data, f"Missing gc_k at layer {k_str}")

    def test_unified_verdict_keys(self):
        uv = self.result["unified_verdict"]
        for k in ("listen_layer", "gc_at_listen_layer", "safety_at_listen_layer",
                  "audio_dominant", "jailbreak_risk", "verdict"):
            self.assertIn(k, uv)

    def test_audio_dominant_flag(self):
        uv = self.result["unified_verdict"]
        gc = uv["gc_at_listen_layer"]
        expected = gc > AUDIO_DOMINANT_THRESHOLD
        self.assertEqual(uv["audio_dominant"], expected)

    def test_jailbreak_risk_logic(self):
        uv = self.result["unified_verdict"]
        audit = self.result["safety_audit"]
        self.assertEqual(uv["jailbreak_risk"], uv["audio_dominant"] and audit["alert"])

    def test_verdict_is_string(self):
        self.assertIsInstance(self.result["unified_verdict"]["verdict"], str)
        self.assertGreater(len(self.result["unified_verdict"]["verdict"]), 10)


class TestUnifiedEvalModes(unittest.TestCase):
    """Test different gc modes and test variants."""

    def test_guess_mode_lower_gc(self):
        listen = run_mock_eval(gc_mode="listen")
        guess = run_mock_eval(gc_mode="guess")
        self.assertGreater(
            listen["gc_curve"]["mean_decoder_gc"],
            guess["gc_curve"]["mean_decoder_gc"],
            "listen mode should have higher decoder gc than guess mode"
        )

    def test_benign_higher_safety(self):
        jb = run_mock_eval(test_variant="jailbreak")
        benign = run_mock_eval(test_variant="benign")
        # Benign should have higher average safety score
        def avg_safety(r):
            scores = [d["safety_score"] for d in r["safety_audit"]["layers"].values()]
            return sum(scores) / len(scores)
        self.assertGreater(avg_safety(benign), avg_safety(jb))

    def test_deterministic(self):
        r1 = run_mock_eval(seed=123)
        r2 = run_mock_eval(seed=123)
        self.assertEqual(r1["gc_curve"]["gc_values"], r2["gc_curve"]["gc_values"])
        self.assertEqual(r1["safety_audit"]["listen_layer_candidate"],
                         r2["safety_audit"]["listen_layer_candidate"])

    def test_custom_layer_count(self):
        result = run_mock_eval(n_enc=4, n_dec=4)
        self.assertEqual(result["n_layers"], 8)
        self.assertEqual(len(result["gc_curve"]["layers"]), 8)
        self.assertEqual(len(result["safety_audit"]["layers"]), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
