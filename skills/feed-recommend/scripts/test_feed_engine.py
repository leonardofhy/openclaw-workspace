"""Tests for feed_engine.py.

Imports the module directly via sys.path insertion so no package install is needed.
All tests are self-contained: they create Article fixtures inline and never make
real network calls.
"""

import json
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: make feed_engine importable
# ---------------------------------------------------------------------------
_SCRIPTS = "/Users/leonardo/.openclaw/workspace/skills/feed-recommend/scripts"
# feed-recommend's own shared lives under skills/shared (not workspace/shared)
_SHARED  = "/Users/leonardo/.openclaw/workspace/skills/shared"

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

# jsonl_store must be importable before the patch target can be resolved.
import jsonl_store  # noqa: E402

# feed_engine runs find_workspace() at import time; patch it before the first
# import so the module does not need a live workspace.
with patch.object(jsonl_store, "find_workspace", return_value="/tmp/fake_workspace"):
    import feed_engine

from feed_engine import (
    Article,
    ScoredArticle,
    score_article,
    classify_action,
    _title_similarity,
    dedup,
    recommend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_article(
    source: str = "hn",
    title: str = "Test Article",
    url: str = "https://example.com/test",
    score: int = 0,
    comments: int = 0,
    posted: str = "",
    snippet: str = "",
    tags: list[str] | None = None,
    source_id: str = "",
) -> Article:
    return Article(
        source=source,
        title=title,
        url=url,
        score=score,
        comments=comments,
        posted=posted,
        snippet=snippet,
        tags=tags or [],
        source_id=source_id,
    )


_EMPTY_PROFILE: dict = {}

_FULL_PROFILE: dict = {
    "boost_keywords": {"transformer": 2.0, "llm": 1.5},
    "penalty_keywords": {"nft": -3.0},
    "interest_topics": ["machine learning", "alignment"],
}


# ===========================================================================
# score_article
# ===========================================================================

class TestScoreArticle:
    def test_boost_keyword_in_title(self):
        article = make_article(title="A new transformer architecture")
        score = score_article(article, _FULL_PROFILE)
        # "transformer" keyword boost (+2) should be included
        assert score >= 2.0

    def test_penalty_keyword_in_title(self):
        article = make_article(title="Buy NFT tokens now")
        score = score_article(article, _FULL_PROFILE)
        # penalty_keywords weight is already negative in the profile
        assert score <= 0.0

    def test_hn_score_500_adds_3(self):
        article = make_article(score=500)
        base = score_article(article, _EMPTY_PROFILE)
        assert base >= 3.0

    def test_hn_score_200_adds_2(self):
        article = make_article(score=200)
        base = score_article(article, _EMPTY_PROFILE)
        assert base >= 2.0

    def test_hn_score_100_adds_1(self):
        article = make_article(score=100)
        base = score_article(article, _EMPTY_PROFILE)
        assert base >= 1.0

    def test_hn_score_below_100_adds_nothing(self):
        article = make_article(score=99)
        base = score_article(article, _EMPTY_PROFILE)
        assert base < 1.0

    def test_comments_200_adds_1_5(self):
        article = make_article(comments=200)
        base = score_article(article, _EMPTY_PROFILE)
        assert base >= 1.5

    def test_comments_100_adds_1(self):
        article = make_article(comments=100)
        base = score_article(article, _EMPTY_PROFILE)
        assert base >= 1.0

    def test_arxiv_domain_boost(self):
        article = make_article(url="https://arxiv.org/abs/2401.00001")
        base_no_domain = score_article(make_article(), _EMPTY_PROFILE)
        base_arxiv = score_article(article, _EMPTY_PROFILE)
        assert base_arxiv - base_no_domain == pytest.approx(2.0, abs=0.05)

    def test_transformer_circuits_domain_boost(self):
        article = make_article(url="https://transformer-circuits.pub/2024/paper")
        s = score_article(article, _EMPTY_PROFILE)
        assert s >= 3.0

    def test_recency_within_24h_adds_2(self):
        recent = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        article = make_article(posted=recent)
        s = score_article(article, _EMPTY_PROFILE)
        assert s >= 2.0

    def test_recency_between_24_48h_adds_1(self):
        mid = (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat()
        article = make_article(posted=mid)
        s = score_article(article, _EMPTY_PROFILE)
        assert s >= 1.0
        assert s < 2.0

    def test_recency_older_than_48h_no_bonus(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        article = make_article(posted=old)
        s = score_article(article, _EMPTY_PROFILE)
        # No recency bonus; score should still be 0.0 with empty profile & no domain
        assert s == pytest.approx(0.0, abs=0.05)

    def test_source_reputation_arxiv(self):
        article = make_article(source="arxiv")
        s = score_article(article, _EMPTY_PROFILE)
        assert s == pytest.approx(1.0, abs=0.05)

    def test_source_reputation_af(self):
        article = make_article(source="af")
        s = score_article(article, _EMPTY_PROFILE)
        assert s == pytest.approx(1.5, abs=0.05)

    def test_source_reputation_lw(self):
        article = make_article(source="lw")
        s = score_article(article, _EMPTY_PROFILE)
        assert s == pytest.approx(0.5, abs=0.05)

    def test_tag_matching_boost_keywords(self):
        article = make_article(tags=["transformer", "llm"])
        profile = {"boost_keywords": {"transformer": 2.0, "llm": 1.5}}
        s = score_article(article, profile)
        # +2 each matching tag; both "transformer" and "llm" appear in tags
        assert s >= 2.0

    def test_tag_matching_interest_topics(self):
        article = make_article(tags=["alignment"])
        profile = {"interest_topics": ["alignment"]}
        s = score_article(article, profile)
        # +2 per interest_topics tag match
        assert s >= 2.0

    def test_combined_scoring(self):
        article = make_article(
            title="transformer alignment research",
            url="https://arxiv.org/abs/2401.00001",
            score=500,
            comments=200,
        )
        s = score_article(article, _FULL_PROFILE)
        # Boost keywords: transformer (+2) → +2
        # HN score >=500 → +3
        # Comments >=200 → +1.5
        # arxiv domain → +2
        # Total (without recency/source rep): at least 8.5
        assert s >= 8.5


# ===========================================================================
# classify_action
# ===========================================================================

class TestClassifyAction:
    def test_score_8_returns_deep_read(self):
        assert classify_action(8.0) == "深讀"

    def test_score_above_8_returns_deep_read(self):
        assert classify_action(12.5) == "深讀"

    def test_score_5_returns_skim(self):
        assert classify_action(5.0) == "略讀"

    def test_score_between_5_and_8_returns_skim(self):
        assert classify_action(6.9) == "略讀"

    def test_score_below_5_returns_scan_headline(self):
        assert classify_action(4.9) == "掃標題"

    def test_score_zero_returns_scan_headline(self):
        assert classify_action(0.0) == "掃標題"

    def test_negative_score_returns_scan_headline(self):
        assert classify_action(-2.0) == "掃標題"


# ===========================================================================
# _title_similarity
# ===========================================================================

class TestTitleSimilarity:
    def test_identical_titles(self):
        sim = _title_similarity("deep learning for NLP", "deep learning for NLP")
        assert sim == pytest.approx(1.0)

    def test_no_overlap(self):
        sim = _title_similarity("quantum computing", "renaissance painting")
        assert sim == pytest.approx(0.0)

    def test_partial_overlap(self):
        sim = _title_similarity("deep learning models", "deep learning for NLP")
        # Intersection: {deep, learning} = 2; union: {deep, learning, models, for, nlp} = 5
        assert 0.0 < sim < 1.0
        assert sim == pytest.approx(2 / 5, abs=1e-6)

    def test_empty_string_returns_zero(self):
        assert _title_similarity("", "some title") == pytest.approx(0.0)
        assert _title_similarity("some title", "") == pytest.approx(0.0)

    def test_case_insensitive(self):
        sim_lower = _title_similarity("neural network", "neural network")
        sim_mixed = _title_similarity("Neural Network", "neural network")
        assert sim_lower == pytest.approx(sim_mixed)

    def test_subset_is_not_full_similarity(self):
        # "deep learning" is a strict subset of "deep learning transformers"
        sim = _title_similarity("deep learning", "deep learning transformers")
        assert sim < 1.0
        assert sim > 0.5


# ===========================================================================
# dedup
# ===========================================================================

class TestDedup:
    def test_removes_duplicate_url(self):
        a1 = make_article(url="https://example.com/1", source_id="id1")
        a2 = make_article(url="https://example.com/1", source_id="id2")  # same URL
        result = dedup([a1, a2])
        assert len(result) == 1
        assert result[0].url == "https://example.com/1"

    def test_removes_duplicate_uid(self):
        a1 = make_article(source="hn", source_id="12345", url="https://x.com/a")
        a2 = make_article(source="hn", source_id="12345", url="https://x.com/b")
        # Different URLs but same UID (source:source_id)
        result = dedup([a1, a2])
        assert len(result) == 1

    def test_removes_near_duplicate_title(self):
        a1 = make_article(
            title="Understanding transformer attention mechanisms",
            url="https://example.com/1",
        )
        a2 = make_article(
            title="Understanding transformer attention mechanisms today",
            url="https://example.com/2",
        )
        # Jaccard similarity is high; default threshold 0.85
        result = dedup([a1, a2], title_threshold=0.7)
        assert len(result) == 1

    def test_keeps_distinct_articles(self):
        articles = [
            make_article(title="Quantum computing advances", url="https://a.com/1"),
            make_article(title="Renaissance painting restored", url="https://a.com/2"),
            make_article(title="Deep sea exploration", url="https://a.com/3"),
        ]
        result = dedup(articles)
        assert len(result) == 3

    def test_respects_seen_file(self, tmp_path: Path):
        seen_path = str(tmp_path / "seen.jsonl")
        now_iso = datetime.now(timezone(timedelta(hours=8))).isoformat()
        entry = json.dumps({"id": "hn:https://seen.com/article", "ts": now_iso})
        Path(seen_path).write_text(entry + "\n")

        article = make_article(source="hn", url="https://seen.com/article")
        result = dedup([article], seen_path=seen_path)
        assert len(result) == 0

    def test_empty_list(self):
        assert dedup([]) == []

    def test_custom_title_threshold(self):
        a1 = make_article(
            title="Deep learning for NLP tasks",
            url="https://example.com/1",
        )
        a2 = make_article(
            title="Deep learning for NLP research",
            url="https://example.com/2",
        )
        # At very high threshold (1.0), titles are not identical so both kept
        result_strict = dedup([a1, a2], title_threshold=1.0)
        assert len(result_strict) == 2

        # At lower threshold they may be considered duplicates
        result_loose = dedup([a1, a2], title_threshold=0.5)
        assert len(result_loose) == 1


# ===========================================================================
# recommend
# ===========================================================================

class TestRecommend:
    def _make_pool(self) -> list[Article]:
        """Create 9 articles across 3 sources (3 each) with varying scores."""
        pool = []
        for i in range(3):
            pool.append(make_article(
                source="hn",
                title=f"HN article {i}",
                url=f"https://hn.com/{i}",
                score=300 - i * 50,  # 300, 250, 200
                source_id=f"hn{i}",
            ))
        for i in range(3):
            pool.append(make_article(
                source="arxiv",
                title=f"Arxiv paper {i}",
                url=f"https://arxiv.org/{i}",
                score=100 - i * 10,
                source_id=f"ax{i}",
            ))
        for i in range(3):
            pool.append(make_article(
                source="lw",
                title=f"LessWrong post {i}",
                url=f"https://lesswrong.com/{i}",
                score=50 - i * 5,
                source_id=f"lw{i}",
            ))
        return pool

    def test_min_per_source_guarantees_representation(self, tmp_path: Path):
        pool = self._make_pool()
        result = recommend(pool, _EMPTY_PROFILE, limit=6, min_per_source=1,
                           seen_path=str(tmp_path / "seen.jsonl"))
        sources = {sa.article.source for sa in result}
        # All 3 sources must appear
        assert "hn" in sources
        assert "arxiv" in sources
        assert "lw" in sources

    def test_max_per_source_caps_each_source(self, tmp_path: Path):
        pool = self._make_pool()
        result = recommend(pool, _EMPTY_PROFILE, limit=9, min_per_source=1,
                           max_per_source=2,
                           seen_path=str(tmp_path / "seen.jsonl"))
        from collections import Counter
        counts = Counter(sa.article.source for sa in result)
        for cnt in counts.values():
            assert cnt <= 2

    def test_result_sorted_by_score_descending(self, tmp_path: Path):
        pool = self._make_pool()
        result = recommend(pool, _EMPTY_PROFILE, limit=9,
                           seen_path=str(tmp_path / "seen.jsonl"))
        scores = [sa.interest_score for sa in result]
        assert scores == sorted(scores, reverse=True)

    def test_limit_respected(self, tmp_path: Path):
        pool = self._make_pool()
        result = recommend(pool, _EMPTY_PROFILE, limit=4,
                           min_per_source=0, max_per_source=0,
                           seen_path=str(tmp_path / "seen.jsonl"))
        assert len(result) <= 4

    def test_scored_articles_have_suggested_action(self, tmp_path: Path):
        pool = self._make_pool()
        result = recommend(pool, _EMPTY_PROFILE, limit=9,
                           seen_path=str(tmp_path / "seen.jsonl"))
        for sa in result:
            assert sa.suggested_action in {"深讀", "略讀", "掃標題"}

    def test_empty_input_returns_empty(self, tmp_path: Path):
        result = recommend([], _EMPTY_PROFILE,
                           seen_path=str(tmp_path / "seen.jsonl"))
        assert result == []

    def test_recommend_excludes_seen_articles(self, tmp_path: Path):
        seen_path = tmp_path / "seen.jsonl"
        tz8 = timezone(timedelta(hours=8))
        now_iso = datetime.now(tz8).isoformat()
        # Mark hn:hn0 as seen
        seen_path.write_text(
            json.dumps({"id": "hn:hn0", "ts": now_iso}) + "\n"
        )
        pool = self._make_pool()
        result = recommend(pool, _EMPTY_PROFILE, limit=10,
                           seen_path=str(seen_path))
        uids = {sa.article.uid() for sa in result}
        assert "hn:hn0" not in uids

    def test_min_per_source_2_with_enough_candidates(self, tmp_path: Path):
        pool = self._make_pool()
        result = recommend(pool, _EMPTY_PROFILE, limit=9, min_per_source=2,
                           seen_path=str(tmp_path / "seen.jsonl"))
        from collections import Counter
        counts = Counter(sa.article.source for sa in result)
        # Each source has 3 candidates; guarantee 2 each
        for src in ("hn", "arxiv", "lw"):
            assert counts[src] >= 2
