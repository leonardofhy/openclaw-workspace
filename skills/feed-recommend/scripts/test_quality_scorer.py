#!/usr/bin/env python3
"""Unit tests for quality_scorer.py.

Tests the feed recommendation quality analysis functionality including:
- Feedback metrics computation
- Diversity analysis
- Precision@K estimation
- Weight adjustment recommendations
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

# Ensure imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

import quality_scorer as qs

TZ = timezone(timedelta(hours=8))


# ── Fixtures ─────────────────────────────────────────────────────

SAMPLE_FEEDBACK = [
    {"id": "hn:1", "source": "hn", "positive": True, "title": "LLM interpretability", "ts": "2026-03-18T10:00:00+08:00"},
    {"id": "hn:2", "source": "hn", "positive": False, "title": "crypto trading bot", "ts": "2026-03-18T11:00:00+08:00"},
    {"id": "af:1", "source": "af", "positive": True, "title": "alignment research progress", "ts": "2026-03-18T12:00:00+08:00"},
    {"id": "af:2", "source": "af", "positive": True, "title": "mechanistic interpretability", "ts": "2026-03-18T13:00:00+08:00"},
    {"id": "arxiv:1", "source": "arxiv", "positive": False, "title": "blockchain scaling", "ts": "2026-03-18T14:00:00+08:00"},
]

SAMPLE_CANDIDATES = [
    {"source": "hn", "title": "Neural network advances", "url": "https://hn.com/1", "interest_score": 8.5, "uid": "hn:1"},
    {"source": "af", "title": "AI safety progress", "url": "https://af.org/1", "interest_score": 9.2, "uid": "af:1"},
    {"source": "af", "title": "Alignment forum post", "url": "https://af.org/2", "interest_score": 7.8, "uid": "af:2"},
    {"source": "arxiv", "title": "Machine learning paper", "url": "https://arxiv.org/1", "interest_score": 6.5, "uid": "arxiv:1"},
    {"source": "hn", "title": "Programming tutorial", "url": "https://hn.com/2", "interest_score": 5.2, "uid": "hn:2"},
]

SAMPLE_SEEN = [
    {"id": "hn:123", "ts": "2026-03-17T10:00:00+08:00"},
    {"id": "af:456", "ts": "2026-03-17T11:00:00+08:00"},
    {"id": "https://seen.example.com/article", "url": "https://seen.example.com/article", "ts": "2026-03-17T12:00:00+08:00"},
]


# ── Test Cases ───────────────────────────────────────────────────

class TestLoadData(unittest.TestCase):

    def test_load_feedback_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = qs.load_feedback(tmpdir)
            self.assertEqual(result, [])

    def test_load_feedback_valid_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feedback_path = os.path.join(tmpdir, "feedback.jsonl")
            with open(feedback_path, 'w') as f:
                for entry in SAMPLE_FEEDBACK:
                    f.write(json.dumps(entry) + '\n')

            result = qs.load_feedback(tmpdir)
            self.assertEqual(len(result), 5)
            self.assertEqual(result[0]["id"], "hn:1")
            self.assertTrue(result[0]["positive"])

    def test_load_feedback_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feedback_path = os.path.join(tmpdir, "feedback.jsonl")
            with open(feedback_path, 'w') as f:
                f.write('{"id": "hn:1", "positive": true}\n')
                f.write('invalid json line\n')
                f.write('{"id": "hn:2", "positive": false}\n')

            result = qs.load_feedback(tmpdir)
            self.assertEqual(len(result), 2)

    def test_load_candidates_from_json_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates_dir = os.path.join(tmpdir, "candidates")
            os.makedirs(candidates_dir)

            digest_path = os.path.join(candidates_dir, "2026-03-18.json")
            with open(digest_path, 'w') as f:
                json.dump({"items": SAMPLE_CANDIDATES}, f)

            result = qs.load_candidates(tmpdir)
            self.assertEqual(len(result), 5)
            self.assertEqual(result[0]["source"], "hn")

    def test_load_candidates_from_articles_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates_dir = os.path.join(tmpdir, "candidates")
            os.makedirs(candidates_dir)

            digest_path = os.path.join(candidates_dir, "test.json")
            with open(digest_path, 'w') as f:
                json.dump({"articles": SAMPLE_CANDIDATES[:2]}, f)

            result = qs.load_candidates(tmpdir)
            self.assertEqual(len(result), 2)

    def test_load_candidates_from_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates_dir = os.path.join(tmpdir, "candidates")
            os.makedirs(candidates_dir)

            jsonl_path = os.path.join(candidates_dir, "test.jsonl")
            with open(jsonl_path, 'w') as f:
                for item in SAMPLE_CANDIDATES[:2]:
                    f.write(json.dumps(item) + '\n')

            result = qs.load_candidates(tmpdir)
            self.assertEqual(len(result), 2)

    def test_load_seen_valid_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            seen_path = os.path.join(tmpdir, "seen.jsonl")
            with open(seen_path, 'w') as f:
                for entry in SAMPLE_SEEN:
                    f.write(json.dumps(entry) + '\n')

            result = qs.load_seen(tmpdir)
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0]["id"], "hn:123")


class TestFeedbackMetrics(unittest.TestCase):

    def test_compute_feedback_metrics_empty(self):
        result = qs.compute_feedback_metrics([])
        expected = {
            "total_feedback": 0,
            "positive_rate": 0.0,
            "negative_rate": 0.0,
            "by_source": {},
        }
        self.assertEqual(result, expected)

    def test_compute_feedback_metrics_mixed(self):
        result = qs.compute_feedback_metrics(SAMPLE_FEEDBACK)

        self.assertEqual(result["total_feedback"], 5)
        self.assertEqual(result["positive_rate"], 0.6)  # 3/5
        self.assertEqual(result["negative_rate"], 0.4)  # 2/5

        # Check source breakdown
        by_source = result["by_source"]
        self.assertIn("hn", by_source)
        self.assertIn("af", by_source)
        self.assertIn("arxiv", by_source)

        # HN: 1 positive, 1 negative
        self.assertEqual(by_source["hn"]["total"], 2)
        self.assertEqual(by_source["hn"]["positive"], 1)
        self.assertEqual(by_source["hn"]["positive_rate"], 0.5)

        # AF: 2 positive, 0 negative
        self.assertEqual(by_source["af"]["positive_rate"], 1.0)

    def test_compute_feedback_metrics_missing_source(self):
        feedback = [{"id": "test", "positive": True}]  # no source field
        result = qs.compute_feedback_metrics(feedback)

        self.assertEqual(result["total_feedback"], 1)
        self.assertIn("unknown", result["by_source"])


class TestDiversityIndex(unittest.TestCase):

    def test_compute_diversity_empty(self):
        result = qs.compute_diversity_index([])
        expected = {
            "shannon_entropy": 0.0,
            "normalized_entropy": 0.0,
            "source_distribution": {},
            "num_sources": 0,
        }
        self.assertEqual(result, expected)

    def test_compute_diversity_single_source(self):
        candidates = [{"source": "hn"}, {"source": "hn"}, {"source": "hn"}]
        result = qs.compute_diversity_index(candidates)

        self.assertEqual(result["shannon_entropy"], 0.0)  # no diversity
        self.assertEqual(result["normalized_entropy"], 0.0)
        self.assertEqual(result["num_sources"], 1)
        self.assertEqual(result["source_distribution"]["hn"]["count"], 3)
        self.assertEqual(result["source_distribution"]["hn"]["pct"], 100.0)

    def test_compute_diversity_even_distribution(self):
        candidates = [
            {"source": "hn"}, {"source": "hn"},
            {"source": "af"}, {"source": "af"},
        ]
        result = qs.compute_diversity_index(candidates)

        # With 2 sources evenly distributed, entropy should be log2(2) = 1.0
        self.assertEqual(result["shannon_entropy"], 1.0)
        self.assertEqual(result["normalized_entropy"], 1.0)
        self.assertEqual(result["num_sources"], 2)

    def test_compute_diversity_uneven_distribution(self):
        candidates = [
            {"source": "hn"}, {"source": "hn"}, {"source": "hn"},  # 75%
            {"source": "af"},  # 25%
        ]
        result = qs.compute_diversity_index(candidates)

        # Entropy should be between 0 and 1
        self.assertGreater(result["shannon_entropy"], 0.0)
        self.assertLess(result["shannon_entropy"], 1.0)
        self.assertLess(result["normalized_entropy"], 1.0)

    def test_compute_diversity_missing_source(self):
        candidates = [{"title": "test"}, {"source": "hn"}]  # one missing source
        result = qs.compute_diversity_index(candidates)

        self.assertIn("unknown", result["source_distribution"])
        self.assertIn("hn", result["source_distribution"])


class TestPrecisionAtK(unittest.TestCase):

    def test_precision_at_k_empty_inputs(self):
        self.assertEqual(qs.compute_precision_at_k([], [], k=10), 0.0)
        self.assertEqual(qs.compute_precision_at_k(SAMPLE_CANDIDATES, [], k=10), 0.0)

    def test_precision_at_k_no_scored_candidates(self):
        candidates = [{"title": "test", "url": "https://test.com"}]  # no interest_score
        feedback = [{"id": "test", "positive": True}]
        result = qs.compute_precision_at_k(candidates, feedback, k=10)
        self.assertEqual(result, 0.0)

    def test_precision_at_k_perfect_match(self):
        # Top-ranked items all have positive feedback
        candidates = [
            {"uid": "hn:1", "url": "https://hn.com/1", "interest_score": 9.0, "title": "LLM interpretability"},
            {"uid": "af:1", "url": "https://af.org/1", "interest_score": 8.0, "title": "alignment research"},
            {"uid": "other", "url": "https://other.com", "interest_score": 7.0, "title": "something else"},
        ]
        feedback = [
            {"id": "hn:1", "positive": True},
            {"id": "af:1", "positive": True},
        ]
        result = qs.compute_precision_at_k(candidates, feedback, k=2)
        self.assertEqual(result, 1.0)  # 2/2 relevant

    def test_precision_at_k_partial_match(self):
        # Mix of relevant and non-relevant in top-K
        candidates = [
            {"uid": "good", "interest_score": 9.0, "title": "good article"},
            {"uid": "bad", "interest_score": 8.0, "title": "bad article"},
            {"uid": "meh", "interest_score": 7.0, "title": "meh article"},
        ]
        feedback = [
            {"id": "good", "positive": True},
            {"id": "bad", "positive": False},
        ]
        result = qs.compute_precision_at_k(candidates, feedback, k=2)
        self.assertEqual(result, 0.5)  # 1/2 relevant

    def test_precision_at_k_title_matching(self):
        # Test fuzzy matching by title
        candidates = [
            {"url": "https://test.com", "interest_score": 9.0, "title": "LLM interpretability research"},
        ]
        feedback = [
            {"id": "different_id", "positive": True, "title": "LLM interpretability research"},
        ]
        result = qs.compute_precision_at_k(candidates, feedback, k=1)
        self.assertEqual(result, 1.0)


class TestNoveltyScore(unittest.TestCase):

    def test_novelty_score_empty_candidates(self):
        result = qs.compute_novelty_score([], SAMPLE_SEEN)
        self.assertEqual(result, 0.0)

    def test_novelty_score_all_novel(self):
        candidates = [
            {"uid": "new:1", "url": "https://new1.com"},
            {"uid": "new:2", "url": "https://new2.com"},
        ]
        result = qs.compute_novelty_score(candidates, SAMPLE_SEEN)
        self.assertEqual(result, 1.0)

    def test_novelty_score_all_seen(self):
        candidates = [
            {"uid": "hn:123", "url": "https://hn.com/123"},
            {"uid": "af:456", "url": "https://af.com/456"},
        ]
        result = qs.compute_novelty_score(candidates, SAMPLE_SEEN)
        self.assertEqual(result, 0.0)

    def test_novelty_score_mixed(self):
        candidates = [
            {"uid": "hn:123", "url": "https://hn.com/123"},  # seen
            {"uid": "new:1", "url": "https://new1.com"},     # novel
            {"uid": "new:2", "url": "https://new2.com"},     # novel
        ]
        result = qs.compute_novelty_score(candidates, SAMPLE_SEEN)
        self.assertAlmostEqual(result, 2/3, places=3)

    def test_novelty_score_url_matching(self):
        candidates = [
            {"uid": "different_id", "url": "https://seen.example.com/article"},  # URL match
        ]
        result = qs.compute_novelty_score(candidates, SAMPLE_SEEN)
        self.assertEqual(result, 0.0)


class TestImprovementAnalysis(unittest.TestCase):

    def test_identify_low_rated_sources_empty(self):
        result = qs.identify_low_rated_sources([])
        self.assertEqual(result, [])

    def test_identify_low_rated_sources_insufficient_feedback(self):
        feedback = [
            {"source": "test", "positive": True},
            {"source": "test", "positive": False},  # only 2 items, need 3+
        ]
        result = qs.identify_low_rated_sources(feedback, min_feedback=3)
        self.assertEqual(result, [])

    def test_identify_low_rated_sources_low_performance(self):
        feedback = [
            {"source": "bad_source", "positive": False},
            {"source": "bad_source", "positive": False},
            {"source": "bad_source", "positive": False},
            {"source": "bad_source", "positive": True},  # 25% positive rate
            {"source": "good_source", "positive": True},
            {"source": "good_source", "positive": True},
            {"source": "good_source", "positive": True},  # 100% positive rate
        ]
        result = qs.identify_low_rated_sources(feedback, min_feedback=3)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "bad_source")
        self.assertEqual(result[0]["positive_rate"], 0.25)
        self.assertEqual(result[0]["total_feedback"], 4)
        self.assertIn("suggestion", result[0])

    def test_identify_engaged_topics_basic(self):
        feedback = [
            {"positive": True, "title": "machine learning algorithms"},
            {"positive": True, "title": "deep learning research"},
            {"positive": False, "title": "cryptocurrency trading"},
            {"positive": False, "title": "crypto exchange news"},
        ]
        result = qs.identify_engaged_topics(feedback)

        engaged = result["engaged_keywords"]
        ignored = result["ignored_keywords"]

        # Should capture keywords from titles
        self.assertIn("machine", engaged)
        self.assertIn("learning", engaged)
        self.assertIn("crypto", ignored)
        self.assertIn("trading", ignored)

    def test_analyze_time_patterns_basic(self):
        feedback = [
            {"ts": "2026-03-18T09:00:00+08:00"},  # 9 AM, Tuesday
            {"ts": "2026-03-18T14:00:00+08:00"},  # 2 PM, Tuesday
            {"ts": "2026-03-19T09:00:00+08:00"},  # 9 AM, Wednesday
        ]
        result = qs.analyze_time_patterns(feedback)

        self.assertIn("hourly_distribution", result)
        self.assertIn("daily_distribution", result)
        self.assertIn("peak_hours", result)
        self.assertIn("peak_days", result)

        # Should identify 9 AM as peak hour
        self.assertIn(9, result["peak_hours"])

    def test_analyze_time_patterns_invalid_timestamps(self):
        feedback = [
            {"ts": "invalid-timestamp"},
            {"ts": ""},
            {"ts": "2026-03-18T09:00:00+08:00"},
        ]
        result = qs.analyze_time_patterns(feedback)

        # Should handle invalid timestamps gracefully
        self.assertIn("hourly_distribution", result)
        self.assertEqual(len(result["hourly_distribution"]), 1)  # only 1 valid timestamp


class TestWeightAdjustments(unittest.TestCase):

    def test_recommend_weight_adjustments_low_source_performance(self):
        feedback = [
            {"source": "bad_source", "positive": False},
            {"source": "bad_source", "positive": False},
            {"source": "bad_source", "positive": False},
            {"source": "bad_source", "positive": True},  # 25% positive
        ]
        candidates = SAMPLE_CANDIDATES

        result = qs.recommend_weight_adjustments(feedback, candidates)

        # Should recommend reducing weight for bad_source
        reduce_recs = [r for r in result if r["type"] == "reduce_source_weight"]
        self.assertTrue(len(reduce_recs) > 0)
        self.assertEqual(reduce_recs[0]["source"], "bad_source")

    def test_recommend_weight_adjustments_high_source_performance(self):
        feedback = [
            {"source": "good_source", "positive": True},
            {"source": "good_source", "positive": True},
            {"source": "good_source", "positive": True},
            {"source": "good_source", "positive": True},
            {"source": "good_source", "positive": True},  # 100% positive
        ]
        candidates = SAMPLE_CANDIDATES

        result = qs.recommend_weight_adjustments(feedback, candidates)

        # Should recommend increasing weight for good_source
        increase_recs = [r for r in result if r["type"] == "increase_source_weight"]
        self.assertTrue(len(increase_recs) > 0)
        self.assertEqual(increase_recs[0]["source"], "good_source")

    def test_recommend_weight_adjustments_diversity_improvement(self):
        # Create candidates heavily skewed to one source
        candidates = [
            {"source": "hn"} for _ in range(9)
        ] + [{"source": "af"}]  # 90% HN, 10% AF

        feedback = []
        result = qs.recommend_weight_adjustments(feedback, candidates)

        # Should recommend increasing diversity
        diversity_recs = [r for r in result if r["type"] == "increase_diversity"]
        self.assertTrue(len(diversity_recs) > 0)


class TestFullReport(unittest.TestCase):

    def test_generate_report_empty_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = qs.generate_report(tmpdir)

            self.assertIn("generated_at", result)
            self.assertIn("data_summary", result)
            self.assertIn("quality_metrics", result)
            self.assertIn("improvement_areas", result)
            self.assertIn("weight_adjustments", result)

            # Should handle empty data gracefully
            ds = result["data_summary"]
            self.assertEqual(ds["total_candidates"], 0)
            self.assertEqual(ds["total_feedback"], 0)
            self.assertEqual(ds["total_seen"], 0)

    def test_generate_report_with_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample data files
            feedback_path = os.path.join(tmpdir, "feedback.jsonl")
            with open(feedback_path, 'w') as f:
                for entry in SAMPLE_FEEDBACK:
                    f.write(json.dumps(entry) + '\n')

            candidates_dir = os.path.join(tmpdir, "candidates")
            os.makedirs(candidates_dir)
            with open(os.path.join(candidates_dir, "test.json"), 'w') as f:
                json.dump({"items": SAMPLE_CANDIDATES}, f)

            seen_path = os.path.join(tmpdir, "seen.jsonl")
            with open(seen_path, 'w') as f:
                for entry in SAMPLE_SEEN:
                    f.write(json.dumps(entry) + '\n')

            result = qs.generate_report(tmpdir)

            # Check data summary
            ds = result["data_summary"]
            self.assertEqual(ds["total_candidates"], 5)
            self.assertEqual(ds["total_feedback"], 5)
            self.assertEqual(ds["total_seen"], 3)

            # Check quality metrics
            qm = result["quality_metrics"]
            self.assertIn("precision_at_10", qm)
            self.assertIn("novelty_score", qm)
            self.assertIn("diversity", qm)
            self.assertIn("feedback", qm)

            # Diversity should show multiple sources
            div = qm["diversity"]
            self.assertGreater(div["num_sources"], 1)

    def test_format_text_report_basic(self):
        report = {
            "generated_at": "2026-03-19T10:00:00+08:00",
            "data_summary": {"total_candidates": 10, "total_feedback": 5, "total_seen": 3},
            "quality_metrics": {
                "precision_at_10": 0.8,
                "novelty_score": 0.9,
                "diversity": {"normalized_entropy": 0.7, "num_sources": 3, "source_distribution": {}},
                "feedback": {"positive_rate": 0.6, "by_source": {}},
            },
            "improvement_areas": {
                "low_rated_sources": [],
                "topic_engagement": {"engaged_keywords": {}, "ignored_keywords": {}},
                "time_patterns": {"peak_hours": [], "peak_days": []},
            },
            "weight_adjustments": [],
        }

        result = qs.format_text_report(report)

        self.assertIsInstance(result, str)
        self.assertIn("Feed Recommendation Quality Report", result)
        self.assertIn("Precision@10:", result)
        self.assertIn("80.0%", result)  # 0.8 formatted as percentage


class TestCLI(unittest.TestCase):

    @patch('quality_scorer.generate_report')
    def test_main_json_output(self, mock_generate):
        mock_generate.return_value = {"test": "data"}

        # Mock sys.argv
        test_args = ["quality_scorer.py", "--json"]
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout') as mock_stdout:
                qs.main()

        mock_generate.assert_called_once()
        # Would write JSON to stdout (hard to test exact output)

    @patch('quality_scorer.generate_report')
    def test_main_text_output(self, mock_generate):
        mock_generate.return_value = {
            "generated_at": "2026-03-19T10:00:00+08:00",
            "data_summary": {"total_candidates": 0, "total_feedback": 0, "total_seen": 0},
            "quality_metrics": {
                "precision_at_10": 0.0,
                "novelty_score": 0.0,
                "diversity": {"normalized_entropy": 0.0, "source_distribution": {}},
                "feedback": {"positive_rate": 0.0, "by_source": {}},
            },
            "improvement_areas": {
                "low_rated_sources": [],
                "topic_engagement": {"engaged_keywords": {}, "ignored_keywords": {}},
                "time_patterns": {"peak_hours": [], "peak_days": []},
            },
            "weight_adjustments": [],
        }

        test_args = ["quality_scorer.py"]
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.print') as mock_print:
                qs.main()

        mock_generate.assert_called_once()
        # Should have printed the text report
        self.assertTrue(mock_print.called)


if __name__ == '__main__':
    unittest.main()