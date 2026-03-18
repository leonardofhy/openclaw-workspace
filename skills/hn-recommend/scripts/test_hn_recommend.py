#!/usr/bin/env python3
"""Comprehensive pytest test suite for hn_recommend.py."""

import io
import json
import os
import sys
import types
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: stub jsonl_store into sys.modules BEFORE importing the module
# so that the module-level `from jsonl_store import find_workspace` succeeds.
# ---------------------------------------------------------------------------

_FAKE_WS = "/tmp/fake_workspace"

_jsonl_store_stub = types.ModuleType("jsonl_store")
_jsonl_store_stub.find_workspace = lambda: _FAKE_WS
sys.modules.setdefault("jsonl_store", _jsonl_store_stub)

# Now import the module under test.
import importlib
import hn_recommend  # noqa: E402 – must come after stub registration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TZ = timezone(timedelta(hours=8))


def _make_item(
    title: str = "Test Article",
    url: str = "https://example.com/article",
    score: int = 50,
    comments: int = 10,
    item_id: str = "12345",
) -> dict:
    """Build a minimal HN item dict."""
    return {
        "id": item_id,
        "title": title,
        "url": url,
        "hn_url": f"https://news.ycombinator.com/item?id={item_id}",
        "score": score,
        "comments": comments,
        "by": "user",
        "time": 1700000000,
    }


def _minimal_profile(boost: dict = None, penalty: dict = None) -> dict:
    """Build a minimal profile for deterministic scoring."""
    return {
        "version": 1,
        "updated": None,
        "boost_keywords": boost or {},
        "penalty_keywords": penalty or {},
        "preferred_categories": [],
        "min_hn_score": 20,
    }


def _ts_recent() -> str:
    """ISO timestamp within the last hour."""
    return (datetime.now(TZ) - timedelta(hours=1)).isoformat()


def _ts_old() -> str:
    """ISO timestamp older than 7 days."""
    return (datetime.now(TZ) - timedelta(days=10)).isoformat()


# ---------------------------------------------------------------------------
# 1. score_article — keyword matching
# ---------------------------------------------------------------------------


class TestScoreArticle:
    def test_boost_keyword_in_title(self):
        item = _make_item(title="Mechanistic interpretability of GPT-4", url="")
        profile = _minimal_profile(boost={"mechanistic interpretability": 5})
        assert hn_recommend.score_article(item, profile) >= 5.0

    def test_penalty_keyword_in_title(self):
        item = _make_item(title="Crypto bitcoin NFT frenzy", url="")
        profile = _minimal_profile(penalty={"bitcoin": -5})
        assert hn_recommend.score_article(item, profile) <= -5.0

    def test_high_hn_score_bonus_500(self):
        item = _make_item(title="Boring article", score=600, comments=0)
        profile = _minimal_profile()
        score = hn_recommend.score_article(item, profile)
        assert score == 3.0  # only the HN-score bonus

    def test_high_hn_score_bonus_200(self):
        item = _make_item(title="Boring article", score=250, comments=0)
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 2.0

    def test_high_hn_score_bonus_100(self):
        item = _make_item(title="Boring article", score=150, comments=0)
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 1.0

    def test_no_hn_score_bonus_below_100(self):
        item = _make_item(title="Boring article", score=50, comments=0)
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 0.0

    def test_comment_bonus_200(self):
        item = _make_item(title="Boring article", score=0, comments=250)
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 1.5

    def test_comment_bonus_100(self):
        item = _make_item(title="Boring article", score=0, comments=120)
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 1.0

    def test_domain_boost_arxiv(self):
        item = _make_item(title="Paper", url="https://arxiv.org/abs/1234.56789", score=0, comments=0)
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 2.0

    def test_domain_boost_transformer_circuits(self):
        item = _make_item(
            title="Circuits post",
            url="https://transformer-circuits.pub/post",
            score=0,
            comments=0,
        )
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 3.0

    def test_no_matches_returns_zero(self):
        item = _make_item(title="Boring article", url="https://example.com", score=0, comments=0)
        profile = _minimal_profile()
        assert hn_recommend.score_article(item, profile) == 0.0

    def test_multiple_boost_keywords_stack(self):
        item = _make_item(
            title="Interpretability and alignment research",
            url="",
            score=0,
            comments=0,
        )
        profile = _minimal_profile(boost={"interpretability": 4, "alignment": 4})
        score = hn_recommend.score_article(item, profile)
        assert score == 8.0

    def test_case_insensitive_keyword_match(self):
        item = _make_item(title="SAE Sparse Autoencoder study", url="", score=0, comments=0)
        profile = _minimal_profile(boost={"sparse autoencoder": 5})
        assert hn_recommend.score_article(item, profile) >= 5.0

    def test_keyword_match_in_url(self):
        item = _make_item(
            title="Some title",
            url="https://anthropic.com/research/alignment",
            score=0,
            comments=0,
        )
        profile = _minimal_profile(boost={"alignment": 4})
        assert hn_recommend.score_article(item, profile) >= 4.0

    def test_only_first_domain_boost_applied(self):
        # If a URL matches multiple domain entries the loop breaks after the first hit.
        item = _make_item(
            title="Boring",
            url="https://arxiv.org/abs/1234",
            score=0,
            comments=0,
        )
        profile = _minimal_profile()
        # arxiv.org gives +2; openreview.net would also give +2 but should NOT be added.
        assert hn_recommend.score_article(item, profile) == 2.0

    def test_empty_title_and_url(self):
        item = _make_item(title="", url="", score=0, comments=0)
        profile = _minimal_profile(boost={"llm": 3}, penalty={"crypto": -5})
        assert hn_recommend.score_article(item, profile) == 0.0

    def test_result_is_rounded_to_one_decimal(self):
        # github.com gives +0.5; verify rounding
        item = _make_item(
            title="Boring",
            url="https://github.com/something",
            score=0,
            comments=0,
        )
        profile = _minimal_profile()
        result = hn_recommend.score_article(item, profile)
        assert result == round(result, 1)


# ---------------------------------------------------------------------------
# 2. classify_action
# ---------------------------------------------------------------------------


class TestClassifyAction:
    def test_deep_read_at_boundary(self):
        assert hn_recommend.classify_action(8) == "深讀"

    def test_deep_read_above_boundary(self):
        assert hn_recommend.classify_action(12.5) == "深讀"

    def test_skim_at_boundary(self):
        assert hn_recommend.classify_action(5) == "略讀"

    def test_skim_between_5_and_8(self):
        assert hn_recommend.classify_action(6.5) == "略讀"

    def test_scan_title_below_5(self):
        assert hn_recommend.classify_action(4.9) == "掃標題"

    def test_scan_title_zero(self):
        assert hn_recommend.classify_action(0) == "掃標題"

    def test_scan_title_negative(self):
        assert hn_recommend.classify_action(-3.0) == "掃標題"


# ---------------------------------------------------------------------------
# 3. fetch_url
# ---------------------------------------------------------------------------


class TestFetchUrl:
    def test_success_returns_body(self):
        body = b"hello world"
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = body

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = hn_recommend.fetch_url("https://example.com")

        assert result == "hello world"

    def test_url_error_returns_none(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = hn_recommend.fetch_url("https://example.com")

        assert result is None

    def test_os_error_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = hn_recommend.fetch_url("https://example.com")

        assert result is None


# ---------------------------------------------------------------------------
# 4. fetch_hn_top
# ---------------------------------------------------------------------------


class TestFetchHnTop:
    def _story_json(self, sid: int, title: str = "Story", score: int = 100) -> str:
        return json.dumps(
            {
                "id": sid,
                "type": "story",
                "title": title,
                "url": f"https://example.com/{sid}",
                "score": score,
                "descendants": 10,
                "by": "testuser",
                "time": 1700000000,
            }
        )

    def test_success_returns_stories(self):
        top_ids = json.dumps([1, 2])
        story_1 = self._story_json(1, "Story One")
        story_2 = self._story_json(2, "Story Two")

        responses = [top_ids, story_1, story_2]
        idx = {"i": 0}

        def fake_fetch(url, max_bytes=500_000):
            val = responses[idx["i"]]
            idx["i"] += 1
            return val

        with patch.object(hn_recommend, "fetch_url", side_effect=fake_fetch):
            items = hn_recommend.fetch_hn_top(limit=2)

        assert len(items) == 2
        assert items[0]["id"] == "1"
        assert items[1]["id"] == "2"

    def test_api_failure_returns_empty(self):
        with patch.object(hn_recommend, "fetch_url", return_value=None):
            items = hn_recommend.fetch_hn_top()

        assert items == []

    def test_empty_response_returns_empty(self):
        with patch.object(hn_recommend, "fetch_url", return_value="invalid-json{{{"):
            items = hn_recommend.fetch_hn_top()

        assert items == []

    def test_non_story_items_filtered(self):
        top_ids = json.dumps([10, 11])
        comment_item = json.dumps({"id": 10, "type": "comment", "text": "hi"})
        story_item = self._story_json(11, "Good Story")

        responses = [top_ids, comment_item, story_item]
        idx = {"i": 0}

        def fake_fetch(url, max_bytes=500_000):
            val = responses[idx["i"]]
            idx["i"] += 1
            return val

        with patch.object(hn_recommend, "fetch_url", side_effect=fake_fetch):
            items = hn_recommend.fetch_hn_top(limit=2)

        assert len(items) == 1
        assert items[0]["id"] == "11"

    def test_item_fetch_failure_skipped(self):
        top_ids = json.dumps([20, 21])
        story_21 = self._story_json(21, "Only Story")

        call_count = {"n": 0}

        def fake_fetch(url, max_bytes=500_000):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return top_ids
            if call_count["n"] == 2:
                return None  # item 20 fails
            return story_21

        with patch.object(hn_recommend, "fetch_url", side_effect=fake_fetch):
            items = hn_recommend.fetch_hn_top(limit=2)

        assert len(items) == 1
        assert items[0]["id"] == "21"


# ---------------------------------------------------------------------------
# 5 & 6. load_profile / save_profile
# ---------------------------------------------------------------------------


class TestLoadProfile:
    def test_loads_existing_profile(self, tmp_path):
        profile_data = {"version": 2, "boost_keywords": {}, "updated": None}
        profile_file = tmp_path / "preferences.json"
        profile_file.write_text(json.dumps(profile_data))

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "PROFILE_PATH", str(profile_file)),
        ):
            result = hn_recommend.load_profile()

        assert result["version"] == 2

    def test_missing_profile_creates_default(self, tmp_path):
        profile_file = tmp_path / "preferences.json"

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "PROFILE_PATH", str(profile_file)),
        ):
            result = hn_recommend.load_profile()

        assert result["version"] == 1
        assert profile_file.exists()

    def test_corrupt_json_falls_back_to_default(self, tmp_path):
        profile_file = tmp_path / "preferences.json"
        profile_file.write_text("{bad json{{")

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "PROFILE_PATH", str(profile_file)),
        ):
            result = hn_recommend.load_profile()

        assert result["version"] == 1


class TestSaveProfile:
    def test_writes_json_atomically(self, tmp_path):
        profile_file = tmp_path / "preferences.json"
        profile = {"version": 1, "boost_keywords": {}, "updated": None}

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "PROFILE_PATH", str(profile_file)),
        ):
            hn_recommend.save_profile(profile)

        assert profile_file.exists()
        saved = json.loads(profile_file.read_text())
        assert saved["version"] == 1
        assert saved["updated"] is not None
        # Temp file must not remain after atomic replace
        assert not (tmp_path / "preferences.json.tmp").exists()


# ---------------------------------------------------------------------------
# 7. load_seen
# ---------------------------------------------------------------------------


class TestLoadSeen:
    def test_empty_file_returns_empty_set(self, tmp_path):
        seen_file = tmp_path / "seen.jsonl"
        seen_file.write_text("")

        with patch.object(hn_recommend, "SEEN_PATH", str(seen_file)):
            result = hn_recommend.load_seen()

        assert result == set()

    def test_missing_file_returns_empty_set(self, tmp_path):
        seen_file = tmp_path / "nonexistent.jsonl"

        with patch.object(hn_recommend, "SEEN_PATH", str(seen_file)):
            result = hn_recommend.load_seen()

        assert result == set()

    def test_entries_within_window_returned(self, tmp_path):
        seen_file = tmp_path / "seen.jsonl"
        entries = [
            json.dumps({"id": "100", "ts": _ts_recent()}),
            json.dumps({"id": "101", "ts": _ts_recent()}),
        ]
        seen_file.write_text("\n".join(entries) + "\n")

        with patch.object(hn_recommend, "SEEN_PATH", str(seen_file)):
            result = hn_recommend.load_seen(max_age_days=7)

        assert "100" in result
        assert "101" in result

    def test_old_entries_filtered_out(self, tmp_path):
        seen_file = tmp_path / "seen.jsonl"
        entries = [
            json.dumps({"id": "200", "ts": _ts_old()}),
            json.dumps({"id": "201", "ts": _ts_recent()}),
        ]
        seen_file.write_text("\n".join(entries) + "\n")

        with patch.object(hn_recommend, "SEEN_PATH", str(seen_file)):
            result = hn_recommend.load_seen(max_age_days=7)

        assert "200" not in result
        assert "201" in result

    def test_malformed_lines_skipped(self, tmp_path):
        seen_file = tmp_path / "seen.jsonl"
        content = (
            "{bad json\n"
            + json.dumps({"id": "999", "ts": _ts_recent()})
            + "\n"
        )
        seen_file.write_text(content)

        with patch.object(hn_recommend, "SEEN_PATH", str(seen_file)):
            result = hn_recommend.load_seen(max_age_days=7)

        assert "999" in result


# ---------------------------------------------------------------------------
# 8. mark_seen
# ---------------------------------------------------------------------------


class TestMarkSeen:
    def test_appends_ids_to_file(self, tmp_path):
        seen_file = tmp_path / "seen.jsonl"

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "SEEN_PATH", str(seen_file)),
        ):
            hn_recommend.mark_seen(["42", "43"])

        lines = [json.loads(l) for l in seen_file.read_text().strip().splitlines()]
        ids = {entry["id"] for entry in lines}
        assert ids == {"42", "43"}
        for entry in lines:
            assert "ts" in entry

    def test_appends_to_existing_file(self, tmp_path):
        seen_file = tmp_path / "seen.jsonl"
        seen_file.write_text(json.dumps({"id": "1", "ts": _ts_recent()}) + "\n")

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "SEEN_PATH", str(seen_file)),
        ):
            hn_recommend.mark_seen(["2"])

        lines = seen_file.read_text().strip().splitlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# 9. record_feedback
# ---------------------------------------------------------------------------


class TestRecordFeedback:
    def test_positive_feedback_written(self, tmp_path):
        fb_file = tmp_path / "feedback.jsonl"

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "FEEDBACK_PATH", str(fb_file)),
        ):
            hn_recommend.record_feedback("777", positive=True, title="Great ML paper")

        entry = json.loads(fb_file.read_text().strip())
        assert entry["id"] == "777"
        assert entry["positive"] is True
        assert entry["title"] == "Great ML paper"
        assert "ts" in entry

    def test_negative_feedback_written(self, tmp_path):
        fb_file = tmp_path / "feedback.jsonl"

        with (
            patch.object(hn_recommend, "DATA_DIR", str(tmp_path)),
            patch.object(hn_recommend, "FEEDBACK_PATH", str(fb_file)),
        ):
            hn_recommend.record_feedback("888", positive=False, title="Crypto stuff")

        entry = json.loads(fb_file.read_text().strip())
        assert entry["positive"] is False


# ---------------------------------------------------------------------------
# 10. get_feedback_stats
# ---------------------------------------------------------------------------


class TestGetFeedbackStats:
    def test_no_file_returns_zeros(self, tmp_path):
        fb_file = tmp_path / "feedback.jsonl"

        with patch.object(hn_recommend, "FEEDBACK_PATH", str(fb_file)):
            stats = hn_recommend.get_feedback_stats()

        assert stats["total"] == 0
        assert stats["positive"] == 0
        assert stats["negative"] == 0

    def test_mixed_feedback_counted_correctly(self, tmp_path):
        fb_file = tmp_path / "feedback.jsonl"
        entries = [
            json.dumps({"id": "1", "positive": True, "title": "alignment research", "ts": _ts_recent()}),
            json.dumps({"id": "2", "positive": True, "title": "interpretability paper", "ts": _ts_recent()}),
            json.dumps({"id": "3", "positive": False, "title": "crypto article", "ts": _ts_recent()}),
        ]
        fb_file.write_text("\n".join(entries) + "\n")

        with patch.object(hn_recommend, "FEEDBACK_PATH", str(fb_file)):
            stats = hn_recommend.get_feedback_stats()

        assert stats["total"] == 3
        assert stats["positive"] == 2
        assert stats["negative"] == 1
        assert "top_keywords" in stats

    def test_malformed_lines_skipped(self, tmp_path):
        fb_file = tmp_path / "feedback.jsonl"
        content = (
            "not valid json\n"
            + json.dumps({"id": "5", "positive": True, "title": "good stuff", "ts": _ts_recent()})
            + "\n"
        )
        fb_file.write_text(content)

        with patch.object(hn_recommend, "FEEDBACK_PATH", str(fb_file)):
            stats = hn_recommend.get_feedback_stats()

        assert stats["total"] == 1
        assert stats["positive"] == 1

    def test_top_keywords_extracted_from_positive_titles(self, tmp_path):
        fb_file = tmp_path / "feedback.jsonl"
        entries = [
            json.dumps({"id": str(i), "positive": True, "title": "interpretability research", "ts": _ts_recent()})
            for i in range(5)
        ]
        fb_file.write_text("\n".join(entries) + "\n")

        with patch.object(hn_recommend, "FEEDBACK_PATH", str(fb_file)):
            stats = hn_recommend.get_feedback_stats()

        top_kw_words = [kw for kw, _ in stats["top_keywords"]]
        # "interpretability" and "research" are both > 3 chars
        assert "interpretability" in top_kw_words or "research" in top_kw_words
