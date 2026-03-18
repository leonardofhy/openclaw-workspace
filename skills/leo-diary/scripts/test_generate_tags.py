"""
Unit tests for generate_tags.py — tag extraction from diary entries.

Mocking strategy: patch file I/O, read_diary.load_diary (for metrics),
and the common module imports so no real filesystem or Sheets access occurs.
"""

import json
import os
import sys
import types
from unittest.mock import patch, MagicMock

import pytest

# Stub common module before import
_common_mod = types.ModuleType("common")
_common_mod.now = MagicMock(return_value=__import__("datetime").datetime(2026, 3, 18))
_common_mod.MEMORY = __import__("pathlib").Path("/fake/memory")
_common_mod.TAGS_DIR = __import__("pathlib").Path("/fake/tags")
sys.modules["common"] = _common_mod

# Stub read_diary
_read_diary_mod = types.ModuleType("read_diary")
_read_diary_mod.load_diary = MagicMock(return_value=[])
sys.modules.setdefault("read_diary", _read_diary_mod)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate_tags  # noqa: E402

# Reset the metrics cache before each module-level test
@pytest.fixture(autouse=True)
def _reset_cache():
    generate_tags._diary_metrics_cache = None
    yield
    generate_tags._diary_metrics_cache = None


# ===========================================================================
# extract_people()
# ===========================================================================

class TestExtractPeople:
    def test_finds_known_person(self):
        result = generate_tags.extract_people("今天和智凱討論論文")
        assert "智凱" in result

    def test_finds_alias(self):
        result = generate_tags.extract_people("凱哥今天來了")
        assert "智凱" in result

    def test_finds_multiple_people(self):
        result = generate_tags.extract_people("智凱和晨安一起吃飯")
        assert "智凱" in result
        assert "晨安" in result

    def test_no_people_returns_empty(self):
        result = generate_tags.extract_people("今天天氣很好")
        assert result == []

    def test_deduplicates(self):
        result = generate_tags.extract_people("智凱和智凱哥聊天")
        assert result.count("智凱") == 1

    def test_sorted_output(self):
        result = generate_tags.extract_people("Rocky和Wilson來了")
        assert result == sorted(result)

    def test_cjk_parent_aliases(self):
        result = generate_tags.extract_people("今天跟我媽視訊")
        assert "媽" in result

    def test_english_names_case_sensitive(self):
        # "Rocky" is in the text, should match
        result = generate_tags.extract_people("Talked to Rocky today")
        assert "Rocky" in result


# ===========================================================================
# extract_topics()
# ===========================================================================

class TestExtractTopics:
    def test_finds_topic_by_keyword(self):
        result = generate_tags.extract_topics("今天去游泳池游了一小時")
        assert "游泳" in result

    def test_case_insensitive_match(self):
        result = generate_tags.extract_topics("Working on AudioMatters benchmark")
        assert "AudioMatters" in result

    def test_multiple_topics(self):
        result = generate_tags.extract_topics("今天上課後去游泳，然後打LOL")
        assert "上課" in result
        assert "游泳" in result
        assert "LOL" in result

    def test_no_topics_returns_empty(self):
        result = generate_tags.extract_topics("今天發呆了一天")
        assert result == []

    def test_deduplicates(self):
        result = generate_tags.extract_topics("游泳完又去泳池")
        assert result.count("游泳") == 1

    def test_sorted_output(self):
        result = generate_tags.extract_topics("去游泳然後打LOL再上課")
        assert result == sorted(result)

    def test_openclaw_keyword(self):
        result = generate_tags.extract_topics("今天修了 openclaw 的 cron job")
        assert "OpenClaw" in result

    def test_sleep_topic(self):
        result = generate_tags.extract_topics("今天失眠了很久")
        assert "睡眠議題" in result

    def test_sick_topic(self):
        result = generate_tags.extract_topics("喉嚨痛看醫生")
        assert "生病" in result


# ===========================================================================
# detect_late_sleep()
# ===========================================================================

class TestDetectLateSleep:
    def test_detects_morning_hour_pattern(self):
        assert generate_tags.detect_late_sleep("凌晨3點才入睡") is True

    def test_detects_late_pattern(self):
        assert generate_tags.detect_late_sleep("熬夜寫程式") is True

    def test_detects_hour_sleep_pattern(self):
        assert generate_tags.detect_late_sleep("5點才睡") is True

    def test_no_late_sleep(self):
        assert generate_tags.detect_late_sleep("11點就睡了") is False

    def test_afternoon_hour_not_flagged(self):
        assert generate_tags.detect_late_sleep("下午3點開會") is False

    def test_empty_text(self):
        assert generate_tags.detect_late_sleep("") is False


# ===========================================================================
# extract_metrics_from_header()
# ===========================================================================

class TestExtractMetrics:
    def test_extracts_mood(self):
        content = "心情：4\n精力：3\n今天很開心"
        metrics = generate_tags.extract_metrics_from_header(content)
        assert metrics["mood"] == 4

    def test_extracts_energy(self):
        content = "心情：4\n精力：3\n今天很開心"
        metrics = generate_tags.extract_metrics_from_header(content)
        assert metrics["energy"] == 3

    def test_colon_variants(self):
        content = "心情:4\n精力:3"
        metrics = generate_tags.extract_metrics_from_header(content)
        assert metrics["mood"] == 4
        assert metrics["energy"] == 3

    def test_no_metrics_returns_empty(self):
        content = "今天沒有指標"
        metrics = generate_tags.extract_metrics_from_header(content)
        assert metrics == {}

    def test_only_searches_first_500_chars(self):
        content = "A" * 600 + "心情：4"
        metrics = generate_tags.extract_metrics_from_header(content)
        assert metrics == {}


# ===========================================================================
# generate_tag()
# ===========================================================================

class TestGenerateTag:
    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_basic_tag_structure(self, mock_metrics):
        content = "今天和智凱一起游泳"
        tag = generate_tags.generate_tag("2026-02-20", content)
        assert tag["date"] == "2026-02-20"
        assert "智凱" in tag["people"]
        assert "游泳" in tag["topics"]
        assert tag["method"] == "python-rules"
        assert tag["diary_chars"] == len(content)

    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_late_sleep_flag(self, mock_metrics):
        tag = generate_tags.generate_tag("2026-02-20", "凌晨3點才睡")
        assert tag["late_sleep"] is True

    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_no_late_sleep(self, mock_metrics):
        tag = generate_tags.generate_tag("2026-02-20", "11點就睡了很乖")
        assert tag["late_sleep"] is False

    @patch.object(generate_tags, '_load_diary_metrics',
                  return_value={"2026-02-20": {"mood": 4, "energy": 3}})
    def test_metrics_from_diary_source(self, mock_metrics):
        tag = generate_tags.generate_tag("2026-02-20", "今天還行")
        assert tag["metrics"]["mood"] == 4
        assert tag["metrics"]["energy"] == 3

    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_metrics_fallback_to_header(self, mock_metrics):
        content = "心情：4\n精力：3\n今天還行"
        tag = generate_tags.generate_tag("2026-02-20", content)
        assert tag["metrics"]["mood"] == 4

    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_no_metrics_no_key(self, mock_metrics):
        tag = generate_tags.generate_tag("2026-02-20", "今天沒有指標的日記")
        assert "metrics" not in tag


# ===========================================================================
# process_diary_file()
# ===========================================================================

class TestProcessDiaryFile:
    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_valid_file(self, mock_metrics, tmp_path):
        f = tmp_path / "2026-02-20.md"
        f.write_text("今天和智凱一起游泳，晚上打了LOL" + "x" * 50, encoding="utf-8")
        result = generate_tags.process_diary_file(str(f))
        assert result is not None
        date, tag = result
        assert date == "2026-02-20"
        assert "智凱" in tag["people"]

    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_too_short_content_returns_none(self, mock_metrics, tmp_path):
        f = tmp_path / "2026-02-20.md"
        f.write_text("短", encoding="utf-8")
        result = generate_tags.process_diary_file(str(f))
        assert result is None

    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_non_date_filename_returns_none(self, mock_metrics, tmp_path):
        f = tmp_path / "notes.md"
        f.write_text("Some content here that is long enough" * 5, encoding="utf-8")
        result = generate_tags.process_diary_file(str(f))
        assert result is None


# ===========================================================================
# _load_diary_metrics()
# ===========================================================================

class TestLoadDiaryMetrics:
    def test_caches_after_first_call(self):
        generate_tags._diary_metrics_cache = None
        mock_ld = MagicMock(return_value=[
            {"date": "2026-02-20", "mood": "4", "energy": "3"},
        ])
        # Patch at the read_diary module level since generate_tags imports it inside the function
        with patch.dict("sys.modules", {"read_diary": MagicMock(load_diary=mock_ld)}):
            result1 = generate_tags._load_diary_metrics()
            result2 = generate_tags._load_diary_metrics()
            # Should only call load_diary once due to caching
            assert mock_ld.call_count == 1

    def test_handles_load_failure(self):
        generate_tags._diary_metrics_cache = None
        mock_ld = MagicMock(side_effect=Exception("API error"))
        with patch.dict("sys.modules", {"read_diary": MagicMock(load_diary=mock_ld)}):
            result = generate_tags._load_diary_metrics()
            assert result == {}

    def test_filters_invalid_mood_energy(self):
        generate_tags._diary_metrics_cache = None
        mock_ld = MagicMock(return_value=[
            {"date": "2026-02-20", "mood": "0", "energy": "6"},
        ])
        with patch.dict("sys.modules", {"read_diary": MagicMock(load_diary=mock_ld)}):
            result = generate_tags._load_diary_metrics()
            # mood=0 out of range, energy=6 out of range — both filtered
            assert result == {}

    def test_valid_metrics_stored(self):
        generate_tags._diary_metrics_cache = None
        mock_ld = MagicMock(return_value=[
            {"date": "2026-02-20", "mood": "4", "energy": "3"},
        ])
        with patch.dict("sys.modules", {"read_diary": MagicMock(load_diary=mock_ld)}):
            result = generate_tags._load_diary_metrics()
            assert result["2026-02-20"]["mood"] == 4
            assert result["2026-02-20"]["energy"] == 3


# ===========================================================================
# main() — integration-level smoke test
# ===========================================================================

class TestMain:
    @patch("generate_tags.os.path.exists", return_value=True)
    @patch("generate_tags.os.makedirs")
    @patch("generate_tags.glob.glob", return_value=[])
    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_main_no_files(self, mock_metrics, mock_glob, mock_mkdir, mock_exists,
                           capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["generate_tags.py", "--dry-run"])
        generate_tags.main()
        out = capsys.readouterr().out
        assert "處理：0 筆" in out

    @patch("generate_tags.os.makedirs")
    @patch("generate_tags.os.path.exists")
    @patch("generate_tags.glob.glob")
    @patch.object(generate_tags, '_load_diary_metrics', return_value={})
    def test_main_processes_file(self, mock_metrics, mock_glob, mock_exists,
                                 mock_mkdir, capsys, monkeypatch, tmp_path):
        # Create a real file
        diary_file = tmp_path / "2026-02-20.md"
        diary_file.write_text("今天和智凱游泳很開心" + "x" * 60, encoding="utf-8")

        mock_glob.return_value = [str(diary_file)]
        mock_exists.return_value = False  # no existing tag file

        monkeypatch.setattr("sys.argv", ["generate_tags.py", "--dry-run"])
        generate_tags.main()
        out = capsys.readouterr().out
        assert "處理：1 筆" in out
