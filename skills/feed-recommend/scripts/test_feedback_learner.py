"""Tests for feedback_learner.py"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from feedback_learner import (
    _extract_keywords,
    _extract_bigrams,
    analyze_feedback,
    apply_feedback_score,
)


class TestKeywordExtraction:
    def test_basic_extraction(self):
        kws = _extract_keywords("Mechanistic Interpretability of LLMs")
        assert "mechanistic" in kws
        assert "interpretability" in kws
        assert "llms" in kws

    def test_stopwords_removed(self):
        kws = _extract_keywords("The best way to use AI for this task")
        assert "the" not in kws
        assert "way" in kws

    def test_short_words_filtered(self):
        kws = _extract_keywords("An AI ML DL paper on SAE")
        # 2-char words filtered
        assert "ai" not in kws
        assert "paper" in kws
        assert "sae" in kws

    def test_bigrams(self):
        bgs = _extract_bigrams("Sparse Autoencoder for LLM Interpretability")
        assert "sparse autoencoder" in bgs
        assert "autoencoder llm" in bgs


class TestAnalyzeFeedback:
    def test_empty_feedback(self):
        result = analyze_feedback([])
        assert result["total_positive"] == 0
        assert result["total_negative"] == 0
        assert result["keyword_scores"] == {}

    def test_positive_feedback_boosts_keywords(self):
        entries = [
            {"title": "SAE interpretability paper", "source": "arxiv", "positive": True},
            {"title": "SAE circuit analysis", "source": "arxiv", "positive": True},
            {"title": "SAE probing results", "source": "af", "positive": True},
        ]
        result = analyze_feedback(entries)
        assert result["keyword_scores"].get("sae", 0) > 0

    def test_negative_feedback_penalizes(self):
        entries = [
            {"title": "Crypto trading bot", "source": "hn", "positive": False},
            {"title": "Crypto market update", "source": "hn", "positive": False},
            {"title": "Crypto NFT news", "source": "hn", "positive": False},
        ]
        result = analyze_feedback(entries)
        assert result["keyword_scores"].get("crypto", 0) < 0

    def test_mixed_feedback(self):
        entries = [
            {"title": "AI safety paper", "source": "af", "positive": True},
            {"title": "AI safety paper", "source": "af", "positive": True},
            {"title": "AI trading bot", "source": "hn", "positive": False},
            {"title": "AI trading bot", "source": "hn", "positive": False},
        ]
        result = analyze_feedback(entries)
        # "trading" should be negative, "safety" positive
        assert result["keyword_scores"].get("trading", 0) < 0
        assert result["keyword_scores"].get("safety", 0) > 0

    def test_source_bias(self):
        entries = [
            {"title": "Paper A", "source": "af", "positive": True},
            {"title": "Paper B", "source": "af", "positive": True},
            {"title": "News C", "source": "hn", "positive": False},
            {"title": "News D", "source": "hn", "positive": False},
        ]
        result = analyze_feedback(entries)
        assert result["source_bias"].get("af", 0) > 0
        assert result["source_bias"].get("hn", 0) < 0

    def test_score_capped(self):
        # Many positive entries for same keyword shouldn't exceed cap
        entries = [
            {"title": f"AI safety paper {i}", "source": "af", "positive": True}
            for i in range(20)
        ]
        result = analyze_feedback(entries)
        for v in result["keyword_scores"].values():
            assert -3.0 <= v <= 3.0


class TestApplyFeedbackScore:
    def test_no_adjustments(self):
        # Pass explicit empty dict (None would load from disk)
        score = apply_feedback_score("Test article", "hn", {})
        assert score == 0.0

    def test_empty_adjustments(self):
        score = apply_feedback_score("Test article", "hn", {"keyword_scores": {}, "source_bias": {}})
        assert score == 0.0

    def test_keyword_boost(self):
        adj = {"keyword_scores": {"safety": 2.0}, "source_bias": {}}
        score = apply_feedback_score("AI Safety Research", "af", adj)
        assert score == 2.0

    def test_source_bias_applied(self):
        adj = {"keyword_scores": {}, "source_bias": {"af": 1.5}}
        score = apply_feedback_score("Some article", "af", adj)
        assert score == 1.5

    def test_combined(self):
        adj = {"keyword_scores": {"safety": 1.0}, "source_bias": {"af": 0.5}}
        score = apply_feedback_score("AI Safety Paper", "af", adj)
        assert score == 1.5
