"""
Unit tests for search_diary.py — diary search with regex, aliases, date ranges.

Mocking strategy: patch read_diary.load_diary at the search_diary module level
so no real Google Sheets / file I/O occurs.
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Stub read_diary before importing search_diary
import types
_read_diary_mod = types.ModuleType("read_diary")
_read_diary_mod.load_diary = MagicMock(return_value=[])
sys.modules.setdefault("read_diary", _read_diary_mod)

import search_diary  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(date="2026-02-20", diary="今天去實驗室和智凱討論 AudioMatters",
           mood="4", energy="3", completed=""):
    return {
        "date": date,
        "diary": diary,
        "mood": mood,
        "energy": energy,
        "completed": completed,
    }


# ===========================================================================
# expand_keyword()
# ===========================================================================

class TestExpandKeyword:
    def test_known_alias_expands(self):
        result = search_diary.expand_keyword("凱哥")
        assert "智凱" in result
        assert "凱哥" in result

    def test_canonical_name_expands(self):
        result = search_diary.expand_keyword("智凱")
        assert "智凱哥" in result

    def test_unknown_keyword_returns_self(self):
        result = search_diary.expand_keyword("randomword")
        assert result == ["randomword"]

    def test_case_insensitive_lookup(self):
        result = search_diary.expand_keyword("ROCKY")
        assert "Rocky" in result

    def test_cjk_alias_lookup(self):
        result = search_diary.expand_keyword("老媽")
        assert "我媽" in result
        assert "媽媽" in result


# ===========================================================================
# matches_text()
# ===========================================================================

class TestMatchesText:
    def test_plain_match(self):
        hits = search_diary.matches_text("今天智凱來了", ["智凱"], False)
        assert "智凱" in hits

    def test_plain_no_match(self):
        hits = search_diary.matches_text("今天很開心", ["智凱"], False)
        assert hits == []

    def test_case_insensitive_plain(self):
        hits = search_diary.matches_text("Talked to Rocky", ["rocky"], False)
        assert "rocky" in hits

    def test_regex_match(self):
        hits = search_diary.matches_text("凌晨3點才睡", [r"凌晨[2-5]點"], True)
        assert len(hits) == 1

    def test_regex_no_match(self):
        hits = search_diary.matches_text("下午3點開會", [r"凌晨[2-5]點"], True)
        assert hits == []

    def test_multiple_patterns(self):
        text = "智凱和晨安都來了"
        hits = search_diary.matches_text(text, ["智凱", "晨安", "Rocky"], False)
        assert "智凱" in hits
        assert "晨安" in hits
        assert "Rocky" not in hits


# ===========================================================================
# extract_context()
# ===========================================================================

class TestExtractContext:
    def test_basic_context_extraction(self):
        text = "prefix " + "智凱" + " suffix"
        snippets = search_diary.extract_context(text, "智凱", context_chars=3)
        assert len(snippets) >= 1
        assert "智凱" in snippets[0]

    def test_context_with_ellipsis_prefix(self):
        text = "A" * 100 + "智凱" + "B" * 100
        snippets = search_diary.extract_context(text, "智凱", context_chars=10)
        assert snippets[0].startswith("…")

    def test_context_with_ellipsis_suffix(self):
        text = "A" * 100 + "智凱" + "B" * 100
        snippets = search_diary.extract_context(text, "智凱", context_chars=10)
        assert snippets[0].endswith("…")

    def test_regex_context_extraction(self):
        text = "凌晨3點才睡覺很累"
        snippets = search_diary.extract_context(text, r"凌晨\d點", context_chars=5, use_regex=True)
        assert len(snippets) >= 1

    def test_max_3_snippets_for_plain_search(self):
        text = "AB " * 50  # many repetitions
        snippets = search_diary.extract_context(text, "AB", context_chars=2)
        assert len(snippets) <= 3

    def test_no_match_returns_empty(self):
        snippets = search_diary.extract_context("hello world", "zzz", context_chars=5)
        assert snippets == []


# ===========================================================================
# search()
# ===========================================================================

class TestSearch:
    @patch("search_diary.load_diary")
    def test_single_keyword_match(self, mock_load):
        mock_load.return_value = [_entry()]
        results = search_diary.search(["智凱"])
        assert len(results) == 1
        assert results[0]["date"] == "2026-02-20"

    @patch("search_diary.load_diary")
    def test_no_match_returns_empty(self, mock_load):
        mock_load.return_value = [_entry()]
        results = search_diary.search(["不存在的詞"])
        assert results == []

    @patch("search_diary.load_diary")
    def test_and_mode_requires_all_keywords(self, mock_load):
        mock_load.return_value = [_entry(diary="智凱和AudioMatters")]
        # AND: both must match
        results = search_diary.search(["智凱", "AudioMatters"], use_or=False)
        assert len(results) == 1

        results = search_diary.search(["智凱", "不存在"], use_or=False)
        assert len(results) == 0

    @patch("search_diary.load_diary")
    def test_or_mode_matches_any_keyword(self, mock_load):
        mock_load.return_value = [_entry(diary="智凱今天來了")]
        results = search_diary.search(["智凱", "不存在"], use_or=True)
        assert len(results) == 1

    @patch("search_diary.load_diary")
    def test_alias_expansion(self, mock_load):
        mock_load.return_value = [_entry(diary="今天凱哥提到了")]
        # "智凱" should expand to include "凱哥"
        results = search_diary.search(["智凱"])
        assert len(results) == 1

    @patch("search_diary.load_diary")
    def test_regex_mode(self, mock_load):
        mock_load.return_value = [_entry(diary="凌晨3點才睡")]
        results = search_diary.search([r"凌晨[2-5]點"], use_regex=True)
        assert len(results) == 1

    @patch("search_diary.load_diary")
    def test_max_results_limit(self, mock_load):
        entries = [_entry(date=f"2026-02-{i:02d}", diary="智凱") for i in range(1, 20)]
        mock_load.return_value = entries
        results = search_diary.search(["智凱"], max_results=5)
        assert len(results) == 5

    @patch("search_diary.load_diary")
    def test_field_completed(self, mock_load):
        mock_load.return_value = [_entry(diary="", completed="完成了游泳訓練")]
        results = search_diary.search(["游泳"], field="completed")
        assert len(results) == 1

    @patch("search_diary.load_diary")
    def test_field_all_searches_both(self, mock_load):
        mock_load.return_value = [_entry(diary="日記內容", completed="完成了游泳")]
        results = search_diary.search(["游泳"], field="all")
        assert len(results) == 1

    @patch("search_diary.load_diary")
    def test_empty_diary_skipped(self, mock_load):
        mock_load.return_value = [_entry(diary=""), _entry(diary="   ")]
        results = search_diary.search(["智凱"])
        assert len(results) == 0

    @patch("search_diary.load_diary")
    def test_result_contains_metadata(self, mock_load):
        mock_load.return_value = [_entry()]
        results = search_diary.search(["智凱"])
        r = results[0]
        assert "mood" in r
        assert "energy" in r
        assert "matched_keywords" in r
        assert "matched_aliases" in r
        assert "snippets" in r
        assert "diary_length" in r

    @patch("search_diary.load_diary")
    def test_unicode_search(self, mock_load):
        mock_load.return_value = [_entry(diary="今天吃了螺螄粉，味道很好")]
        results = search_diary.search(["螺螄粉"])
        assert len(results) == 1


# ===========================================================================
# print_people()
# ===========================================================================

class TestPrintPeople:
    def test_print_people_lists_aliases(self, capsys):
        search_diary.print_people()
        out = capsys.readouterr().out
        assert "智凱" in out
        assert "凱哥" in out
        assert f"共 {len(search_diary.ALIASES)} 人" in out


# ===========================================================================
# main() CLI integration
# ===========================================================================

class TestMainCLI:
    @patch("search_diary.load_diary")
    def test_json_output(self, mock_load, capsys, monkeypatch):
        mock_load.return_value = [_entry()]
        monkeypatch.setattr(
            "sys.argv",
            ["search_diary.py", "智凱", "--json"],
        )
        search_diary.main()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["count"] >= 1
        assert data["mode"] == "AND"

    @patch("search_diary.load_diary")
    def test_stats_output(self, mock_load, capsys, monkeypatch):
        mock_load.return_value = [_entry()]
        monkeypatch.setattr(
            "sys.argv",
            ["search_diary.py", "智凱", "--stats"],
        )
        search_diary.main()
        out = capsys.readouterr().out
        assert "找到" in out

    def test_no_keywords_exits(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["search_diary.py"])
        with pytest.raises(SystemExit):
            search_diary.main()
