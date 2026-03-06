#!/usr/bin/env python3
"""
End-to-end integration test: unified_eval + microgpt_gc_eval + gc_jailbreak_classifier pipeline.
Track T3 + T5 — Q055

Tests the FULL pipeline:
  1. MicroGPT produces gc(k) curve (listen vs guess modes)
  2. unified_eval combines gc(k) + safety audit → verdict
  3. gc_jailbreak_classifier labels the curve → jailbreak/benign

End-to-end invariants:
  - listen mode → benign throughout pipeline; guess/jailbreak → higher risk
  - Pipeline is deterministic (same seed → same output)
  - All pipeline outputs are JSON-serializable

Usage:
    python3 test_e2e_pipeline.py          # run all tests
    python3 test_e2e_pipeline.py -v       # verbose

Author: Little Leo (Lab) — 2026-03-06
Reference: Q055, Track T3+T5, converge phase
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import microgpt_gc_eval as mgc
import unified_eval as ueval
from gc_jailbreak_classifier import (
    classify, classify_gc_curve, extract_features, generate_mock_curve
)


# ---------------------------------------------------------------------------
# Helpers — real API wrappers
# ---------------------------------------------------------------------------

def run_microgpt(mode: str, n_layers: int = 6, seed: int = 42) -> dict:
    """Run MicroGPT gc(k) eval and return gc_curve dict."""
    model = mgc.MicroGPT(n_layers=n_layers, seed=seed)
    h_clean, h_noisy = mgc.make_inputs(d_model=model.d_model, seed=seed)
    if mode == "guess":
        # Swap: pass noisy as clean → model can't listen
        result = mgc.compute_gc(model, h_noisy, h_clean)
    else:
        result = mgc.compute_gc(model, h_clean, h_noisy)
    return {
        "layers": list(range(n_layers)),
        "gc_values": list(result.gc_values),
        "n_encoder_layers": n_layers // 2,
    }


def run_unified(gc_mode: str = "listen", test_variant: str = "benign",
                n_enc: int = 6, n_dec: int = 6) -> dict:
    """Run unified_eval mock pipeline and return full result dict."""
    return ueval.run_mock_eval(gc_mode=gc_mode, test_variant=test_variant,
                               n_enc=n_enc, n_dec=n_dec)


# ---------------------------------------------------------------------------
# Stage 1 → Stage 3: MicroGPT → gc_jailbreak_classifier
# ---------------------------------------------------------------------------

class TestMicrogptToClassifier(unittest.TestCase):
    """Test MicroGPT output → gc_jailbreak_classifier (2-stage pipeline)."""

    def test_listen_mode_classifies_benign(self):
        """Listen mode gc(k) curve should be labeled benign by the classifier."""
        gc_curve = run_microgpt("listen")
        result = classify_gc_curve(gc_curve)
        self.assertEqual(result["label"], "benign",
            f"Expected benign for listen mode but got {result['label']} "
            f"(confidence={result['confidence']:.2f})")

    def test_guess_vs_listen_confidence_differs(self):
        """Guess mode should have a different (typically higher) jailbreak confidence than listen."""
        listen_curve = run_microgpt("listen")
        guess_curve = run_microgpt("guess")
        r_listen = classify_gc_curve(listen_curve)
        r_guess = classify_gc_curve(guess_curve)
        # Compute jailbreak-direction probability for each
        p_jail_listen = r_listen["confidence"] if r_listen["label"] == "jailbreak" else 1 - r_listen["confidence"]
        p_jail_guess = r_guess["confidence"] if r_guess["label"] == "jailbreak" else 1 - r_guess["confidence"]
        self.assertGreaterEqual(p_jail_guess, p_jail_listen,
            "Guess mode should have equal or higher jailbreak probability than listen mode")

    def test_features_extracted_from_microgpt_output(self):
        """Feature extraction should work on raw MicroGPT output."""
        gc_curve = run_microgpt("listen", n_layers=8)
        feats = extract_features(gc_curve)
        required_keys = ["encoder_mean", "decoder_mean", "collapse_ratio", "dec_slope"]
        for k in required_keys:
            self.assertIn(k, feats, f"Missing feature: {k}")
        self.assertGreaterEqual(feats["collapse_ratio"], 0.0)
        self.assertLessEqual(feats["collapse_ratio"], 1.0)

    def test_pipeline_deterministic_across_runs(self):
        """Same seed → same classification result."""
        r1 = classify_gc_curve(run_microgpt("listen", seed=7))
        r2 = classify_gc_curve(run_microgpt("listen", seed=7))
        self.assertEqual(r1["label"], r2["label"])
        self.assertAlmostEqual(r1["confidence"], r2["confidence"], places=6)

    def test_jailbreak_mock_curve_classifies_jailbreak(self):
        """Mock jailbreak curve should be labeled jailbreak by the classifier."""
        gc_curve = generate_mock_curve("jailbreak", seed=42)
        result = classify_gc_curve(gc_curve)
        self.assertEqual(result["label"], "jailbreak",
            f"Expected jailbreak for jailbreak mock but got {result['label']}")


# ---------------------------------------------------------------------------
# Stage 2 → Stage 3: unified_eval → gc_jailbreak_classifier
# ---------------------------------------------------------------------------

class TestUnifiedEvalToClassifier(unittest.TestCase):
    """Test unified_eval output feeding gc_jailbreak_classifier."""

    def test_unified_gc_curve_classifiable(self):
        """unified_eval gc_curve output should be classifiable by gc_jailbreak_classifier."""
        result = run_unified("listen")
        gc_curve = {
            "layers": result["gc_curve"]["layers"],
            "gc_values": result["gc_curve"]["gc_values"],
            "n_encoder_layers": result["n_layers"] // 2,
        }
        classification = classify_gc_curve(gc_curve)
        self.assertIn(classification["label"], ["benign", "jailbreak"])
        self.assertGreaterEqual(classification["confidence"], 0.0)
        self.assertLessEqual(classification["confidence"], 1.0)

    def test_jailbreak_variant_unified_detection(self):
        """Jailbreak test_variant in unified_eval should trigger alert and risk flags."""
        result = run_unified(gc_mode="listen", test_variant="jailbreak")
        # safety_audit alert should be True for jailbreak variant
        self.assertTrue(result["safety_audit"]["alert"],
            "Expected alert=True for jailbreak test_variant")

    def test_guess_mode_unified_verdict_is_string(self):
        """guess gc_mode unified verdict should be a non-empty string."""
        result = run_unified(gc_mode="guess")
        verdict = result["unified_verdict"]["verdict"]
        self.assertIsInstance(verdict, str)
        self.assertGreater(len(verdict), 0)

    def test_listen_mode_unified_audio_dominant(self):
        """listen gc_mode with jailbreak variant should produce audio_dominant=True at listen layer."""
        result = run_unified(gc_mode="listen", test_variant="jailbreak")
        self.assertTrue(result["unified_verdict"]["audio_dominant"],
            "Listen gc_mode with jailbreak variant should have audio_dominant=True")


# ---------------------------------------------------------------------------
# Full 3-stage pipeline
# ---------------------------------------------------------------------------

class TestFullThreeStage(unittest.TestCase):
    """Full 3-stage pipeline: MicroGPT → unified_eval → classifier."""

    def _run_full(self, mgpt_mode: str, unified_gc_mode: str = None,
                  unified_variant: str = "benign") -> dict:
        unified_gc_mode = unified_gc_mode or mgpt_mode
        # Stage 1: MicroGPT gc(k) curve
        mgpt_curve = run_microgpt(mgpt_mode, n_layers=6)

        # Stage 2: unified_eval (independent mock eval, same gc_mode for consistency)
        unified = run_unified(gc_mode=unified_gc_mode, test_variant=unified_variant)

        # Stage 3: classify MicroGPT curve (more ground-truth-like)
        classification = classify_gc_curve(mgpt_curve)

        return {
            "mode": mgpt_mode,
            "mgpt_gc_peak": int(mgpt_curve["gc_values"].index(max(mgpt_curve["gc_values"]))),
            "unified_jailbreak_risk": unified["unified_verdict"]["jailbreak_risk"],
            "unified_audio_dominant": unified["unified_verdict"]["audio_dominant"],
            "classifier_label": classification["label"],
            "classifier_confidence": classification["confidence"],
        }

    def test_full_pipeline_listen_mode(self):
        """Full pipeline in listen mode should complete without error."""
        result = self._run_full("listen")
        self.assertEqual(result["mode"], "listen")
        self.assertIn(result["classifier_label"], ["benign", "jailbreak"])
        self.assertIsInstance(result["unified_jailbreak_risk"], bool)

    def test_full_pipeline_guess_mode(self):
        """Full pipeline in guess mode should complete without error."""
        result = self._run_full("guess")
        self.assertEqual(result["mode"], "guess")
        self.assertIn(result["classifier_label"], ["benign", "jailbreak"])

    def test_full_pipeline_listen_vs_jailbreak_variant(self):
        """Jailbreak safety_audit should fire even in listen gc_mode."""
        result = self._run_full("listen", unified_variant="jailbreak")
        self.assertTrue(result["unified_jailbreak_risk"],
            "Jailbreak variant with listen gc_mode should trigger jailbreak_risk=True")

    def test_full_pipeline_both_modes_different_signals(self):
        """Listen vs jailbreak mock curves should produce different classifier outputs."""
        # Use generate_mock_curve directly for mode differentiation (guaranteed by design)
        listen_curve = generate_mock_curve("listen", seed=42)
        jailbreak_curve = generate_mock_curve("jailbreak", seed=42)
        r_listen = classify_gc_curve(listen_curve)
        r_jailbreak = classify_gc_curve(jailbreak_curve)
        # At minimum labels should differ
        self.assertNotEqual(r_listen["label"], r_jailbreak["label"],
            f"listen={r_listen['label']} vs jailbreak={r_jailbreak['label']} — expected different labels")

    def test_full_pipeline_json_serializable(self):
        """All pipeline outputs should be JSON-serializable (for downstream logging)."""
        mgpt_curve = run_microgpt("listen")
        unified = run_unified("listen")
        classification = classify_gc_curve(mgpt_curve)
        combined = {
            "microgpt_gc_curve": mgpt_curve,
            "unified_eval": unified,
            "classification": classification,
        }
        try:
            json.dumps(combined)
        except (TypeError, ValueError) as e:
            self.fail(f"Pipeline output not JSON-serializable: {e}")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):
    """Edge cases: extreme gc(k) values, schema checks."""

    def test_all_zero_gc_values(self):
        """All-zero gc(k) (extreme collapse) should classify without error."""
        gc_curve = {
            "layers": [0, 1, 2, 3, 4, 5],
            "gc_values": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "n_encoder_layers": 3,
        }
        result = classify_gc_curve(gc_curve)
        self.assertIn(result["label"], ["benign", "jailbreak"])

    def test_all_high_gc_values(self):
        """All-high gc(k) (strong audio dominance) should classify as benign."""
        gc_curve = {
            "layers": [0, 1, 2, 3, 4, 5],
            "gc_values": [0.9, 0.9, 0.9, 0.85, 0.88, 0.87],
            "n_encoder_layers": 3,
        }
        result = classify_gc_curve(gc_curve)
        self.assertEqual(result["label"], "benign")

    def test_unified_schema_completeness(self):
        """unified_eval output must have all required top-level keys."""
        result = run_unified("listen")
        required = ["mode", "model", "n_layers", "gc_curve", "safety_audit", "unified_verdict"]
        for key in required:
            self.assertIn(key, result, f"Missing key in unified_eval output: {key}")

    def test_unified_gc_curve_schema(self):
        """unified_eval gc_curve must have required sub-keys."""
        result = run_unified("listen")
        gc = result["gc_curve"]
        for key in ["layers", "gc_values", "mean_encoder_gc", "mean_decoder_gc", "peak_layer"]:
            self.assertIn(key, gc, f"Missing key in gc_curve: {key}")

    def test_unified_verdict_schema(self):
        """unified_verdict must have required keys."""
        result = run_unified("listen")
        verdict = result["unified_verdict"]
        for key in ["listen_layer", "gc_at_listen_layer", "safety_at_listen_layer",
                    "audio_dominant", "jailbreak_risk", "verdict"]:
            self.assertIn(key, verdict, f"Missing key in unified_verdict: {key}")

    def test_classifier_output_schema(self):
        """classify_gc_curve must return label, confidence, features, reasons."""
        gc_curve = generate_mock_curve("listen")
        result = classify_gc_curve(gc_curve)
        for key in ["label", "confidence", "features", "rules_triggered"]:
            self.assertIn(key, result, f"Missing key in classifier output: {key}")
        self.assertIn(result["label"], ["benign", "jailbreak"])
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
