"""
Unit tests for people_db.py — personal relationship database.

Mocking strategy: patch _load_jsonl / _save_jsonl / _append_jsonl at module level
so no real files are touched. subprocess.run is patched for scan tests.
"""

import json
import sys
import types
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Stub shared module before import
_shared_pkg = types.ModuleType("shared")
_jsonl_mod = types.ModuleType("shared.jsonl_store")
_jsonl_mod.find_workspace = MagicMock(return_value=MagicMock())
_jsonl_mod.JsonlStore = MagicMock()
sys.modules.setdefault("shared", _shared_pkg)
sys.modules.setdefault("shared.jsonl_store", _jsonl_mod)

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import people_db  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _person(id="P001", name="智凱", aliases=None, trust=5, closeness=5,
            tags=None, relationship="labmate", notes="", next_steps=None):
    return {
        "id": id,
        "name": name,
        "aliases": aliases or ["智凱哥", "凱哥"],
        "relationship": relationship,
        "context": "",
        "first_met": "",
        "trust": trust,
        "closeness": closeness,
        "tags": tags or ["lab"],
        "notes": notes,
        "next_steps": next_steps or [],
        "created_at": "2026-01-01",
        "updated_at": "2026-01-01",
    }


def _event(id="E001", person_id="P001", person_name="智凱",
           date="2026-02-20", type_="meeting", summary="test event"):
    return {
        "id": id,
        "person_id": person_id,
        "person_name": person_name,
        "date": date,
        "type": type_,
        "summary": summary,
        "sentiment": "neutral",
        "tags": [],
        "source": "manual",
    }


# ===========================================================================
# find_person()
# ===========================================================================

class TestFindPerson:
    def test_find_by_exact_name(self):
        people = [_person(name="智凱")]
        assert people_db.find_person(people, "智凱") is not None

    def test_find_by_alias(self):
        people = [_person(name="智凱", aliases=["凱哥"])]
        result = people_db.find_person(people, "凱哥")
        assert result is not None
        assert result["name"] == "智凱"

    def test_case_insensitive_name(self):
        people = [_person(name="Rocky")]
        assert people_db.find_person(people, "rocky") is not None

    def test_case_insensitive_alias(self):
        people = [_person(name="David", aliases=["David哥"])]
        assert people_db.find_person(people, "david哥") is not None

    def test_returns_none_when_not_found(self):
        people = [_person(name="智凱")]
        assert people_db.find_person(people, "不存在") is None

    def test_empty_list(self):
        assert people_db.find_person([], "anyone") is None

    def test_unicode_cjk_name(self):
        people = [_person(name="陳縕儂", aliases=["縕儂"])]
        assert people_db.find_person(people, "縕儂") is not None


# ===========================================================================
# _next_id()
# ===========================================================================

class TestNextId:
    def test_empty_list_starts_at_001(self):
        assert people_db._next_id([], "P") == "P001"

    def test_increments_from_existing(self):
        items = [{"id": "P001"}, {"id": "P003"}]
        assert people_db._next_id(items, "P") == "P004"

    def test_ignores_different_prefix(self):
        items = [{"id": "E005"}, {"id": "P002"}]
        assert people_db._next_id(items, "P") == "P003"

    def test_handles_malformed_ids(self):
        items = [{"id": "Pabc"}, {"id": "P002"}]
        assert people_db._next_id(items, "P") == "P003"

    def test_missing_id_field(self):
        items = [{"name": "no id"}, {"id": "P001"}]
        assert people_db._next_id(items, "P") == "P002"


# ===========================================================================
# _validate_range()
# ===========================================================================

class TestValidateRange:
    def test_none_returns_none(self):
        assert people_db._validate_range(None, "trust", 1, 10) is None

    def test_valid_value_returns_it(self):
        assert people_db._validate_range(5, "trust", 1, 10) == 5

    def test_boundary_low(self):
        assert people_db._validate_range(1, "trust", 1, 10) == 1

    def test_boundary_high(self):
        assert people_db._validate_range(10, "trust", 1, 10) == 10

    def test_out_of_range_exits(self):
        with pytest.raises(SystemExit):
            people_db._validate_range(11, "trust", 1, 10)

    def test_zero_out_of_range_exits(self):
        with pytest.raises(SystemExit):
            people_db._validate_range(0, "trust", 1, 10)


# ===========================================================================
# _load_jsonl() / _save_jsonl()
# ===========================================================================

class TestJsonlHelpers:
    def test_load_nonexistent_returns_empty(self, tmp_path):
        assert people_db._load_jsonl(tmp_path / "nope.jsonl") == []

    def test_load_valid_jsonl(self, tmp_path):
        f = tmp_path / "data.jsonl"
        f.write_text('{"a": 1}\n{"b": 2}\n')
        result = people_db._load_jsonl(f)
        assert len(result) == 2
        assert result[0] == {"a": 1}

    def test_load_skips_malformed_lines(self, tmp_path):
        f = tmp_path / "data.jsonl"
        f.write_text('{"ok": true}\nNOT JSON\n{"also": "ok"}\n')
        result = people_db._load_jsonl(f)
        assert len(result) == 2

    def test_load_skips_blank_lines(self, tmp_path):
        f = tmp_path / "data.jsonl"
        f.write_text('{"a": 1}\n\n\n{"b": 2}\n')
        assert len(people_db._load_jsonl(f)) == 2

    def test_save_and_reload_roundtrip(self, tmp_path):
        f = tmp_path / "data.jsonl"
        items = [{"name": "智凱", "id": "P001"}, {"name": "晨安", "id": "P002"}]
        people_db._save_jsonl(f, items)
        loaded = people_db._load_jsonl(f)
        assert loaded == items

    def test_save_creates_parent_dirs(self, tmp_path):
        f = tmp_path / "sub" / "dir" / "data.jsonl"
        people_db._save_jsonl(f, [{"x": 1}])
        assert f.exists()

    def test_append_creates_file(self, tmp_path):
        f = tmp_path / "data.jsonl"
        people_db._append_jsonl(f, {"id": "P001"})
        assert f.exists()
        loaded = people_db._load_jsonl(f)
        assert len(loaded) == 1

    def test_load_unicode_content(self, tmp_path):
        f = tmp_path / "data.jsonl"
        f.write_text('{"name": "陳縕儂", "note": "日記標籤"}\n', encoding="utf-8")
        result = people_db._load_jsonl(f)
        assert result[0]["name"] == "陳縕儂"


# ===========================================================================
# cmd_add()
# ===========================================================================

class TestCmdAdd:
    def _args(self, name="TestPerson", aliases="", rel="", context="",
              first_met="", trust=None, closeness=None, tags="", notes=""):
        return Namespace(
            name=name, aliases=aliases, rel=rel, context=context,
            first_met=first_met, trust=trust, closeness=closeness,
            tags=tags, notes=notes,
        )

    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl", return_value=[])
    def test_add_new_person(self, mock_load, mock_append, capsys):
        people_db.cmd_add(self._args(name="NewPerson", aliases="NP,小N", tags="lab,research"))
        assert mock_append.called
        person = mock_append.call_args[0][1]
        assert person["name"] == "NewPerson"
        assert person["aliases"] == ["NP", "小N"]
        assert person["tags"] == ["lab", "research"]
        assert person["id"] == "P001"
        out = capsys.readouterr().out
        assert "NewPerson" in out

    @patch("people_db._load_jsonl", return_value=[_person(name="智凱")])
    def test_add_duplicate_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_add(self._args(name="智凱"))

    def test_add_empty_name_exits(self):
        with pytest.raises(SystemExit):
            people_db.cmd_add(self._args(name=""))

    def test_add_whitespace_name_exits(self):
        with pytest.raises(SystemExit):
            people_db.cmd_add(self._args(name="   "))

    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl", return_value=[])
    def test_add_defaults_trust_closeness_to_5(self, mock_load, mock_append):
        people_db.cmd_add(self._args())
        person = mock_append.call_args[0][1]
        assert person["trust"] == 5
        assert person["closeness"] == 5

    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl", return_value=[])
    def test_add_custom_trust_closeness(self, mock_load, mock_append):
        people_db.cmd_add(self._args(trust=8, closeness=3))
        person = mock_append.call_args[0][1]
        assert person["trust"] == 8
        assert person["closeness"] == 3

    @patch("people_db._load_jsonl", return_value=[])
    def test_add_invalid_trust_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_add(self._args(trust=11))


# ===========================================================================
# cmd_update()
# ===========================================================================

class TestCmdUpdate:
    def _args(self, name="智凱", trust=None, closeness=None, notes=None,
              rel=None, context=None, aliases=None, tags=None, next_steps=None):
        return Namespace(
            name=name, trust=trust, closeness=closeness, notes=notes,
            rel=rel, context=context, aliases=aliases, tags=tags,
            next_steps=next_steps,
        )

    @patch("people_db._save_jsonl")
    @patch("people_db._load_jsonl", return_value=[_person()])
    def test_update_trust(self, mock_load, mock_save, capsys):
        people_db.cmd_update(self._args(trust=8))
        saved_people = mock_save.call_args[0][1]
        assert saved_people[0]["trust"] == 8

    @patch("people_db._save_jsonl")
    @patch("people_db._load_jsonl", return_value=[_person()])
    def test_update_next_steps(self, mock_load, mock_save):
        people_db.cmd_update(self._args(next_steps="step1;step2;step3"))
        saved = mock_save.call_args[0][1]
        assert saved[0]["next_steps"] == ["step1", "step2", "step3"]

    @patch("people_db._load_jsonl", return_value=[])
    def test_update_nonexistent_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_update(self._args(name="不存在"))


# ===========================================================================
# cmd_log()
# ===========================================================================

class TestCmdLog:
    def _args(self, name="智凱", date=None, type_="interaction",
              summary="test", sentiment="neutral", tags="", source="manual"):
        return Namespace(
            name=name, date=date, type=type_, summary=summary,
            sentiment=sentiment, tags=tags, source=source,
        )

    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl")
    def test_log_event(self, mock_load, mock_append, capsys):
        mock_load.side_effect = [[_person()], []]  # people, then events
        people_db.cmd_log(self._args(summary="Lab meeting"))
        event = mock_append.call_args[0][1]
        assert event["person_id"] == "P001"
        assert event["summary"] == "Lab meeting"
        assert event["id"] == "E001"

    @patch("people_db._load_jsonl", return_value=[])
    def test_log_nonexistent_person_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_log(self._args(name="NoOne"))

    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl")
    def test_log_with_tags(self, mock_load, mock_append):
        mock_load.side_effect = [[_person()], []]
        people_db.cmd_log(self._args(tags="research,paper"))
        event = mock_append.call_args[0][1]
        assert event["tags"] == ["research", "paper"]


# ===========================================================================
# cmd_show()
# ===========================================================================

class TestCmdShow:
    @patch("people_db._load_jsonl")
    def test_show_person_with_events(self, mock_load, capsys):
        mock_load.side_effect = [
            [_person()],
            [_event(), _event(id="E002", date="2026-02-21", summary="Dinner")],
        ]
        args = Namespace(name="智凱", limit=10)
        people_db.cmd_show(args)
        out = capsys.readouterr().out
        assert "智凱" in out
        assert "P001" in out
        assert "2 筆" in out

    @patch("people_db._load_jsonl", return_value=[])
    def test_show_nonexistent_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_show(Namespace(name="NoOne", limit=10))


# ===========================================================================
# cmd_list()
# ===========================================================================

class TestCmdList:
    @patch("people_db._load_jsonl")
    def test_list_empty_db(self, mock_load, capsys):
        mock_load.side_effect = [[], []]
        people_db.cmd_list(Namespace())
        out = capsys.readouterr().out
        assert "共 0 人" in out

    @patch("people_db._load_jsonl")
    def test_list_with_people(self, mock_load, capsys):
        mock_load.side_effect = [
            [_person(), _person(id="P002", name="晨安")],
            [_event()],
        ]
        people_db.cmd_list(Namespace())
        out = capsys.readouterr().out
        assert "共 2 人" in out
        assert "智凱" in out
        assert "晨安" in out


# ===========================================================================
# cmd_delete()
# ===========================================================================

class TestCmdDelete:
    @patch("people_db._save_jsonl")
    @patch("people_db._load_jsonl", return_value=[_event(id="E001")])
    def test_delete_event_by_id(self, mock_load, mock_save, capsys):
        people_db.cmd_delete(Namespace(target="E001", confirm=True))
        saved = mock_save.call_args[0][1]
        assert len(saved) == 0
        assert "E001" in capsys.readouterr().out

    @patch("people_db._load_jsonl", return_value=[])
    def test_delete_nonexistent_event_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_delete(Namespace(target="E999", confirm=True))

    @patch("people_db._save_jsonl")
    @patch("people_db._load_jsonl")
    def test_delete_person_with_confirm(self, mock_load, mock_save, capsys):
        mock_load.side_effect = [
            [_person()],
            [_event()],
        ]
        people_db.cmd_delete(Namespace(target="智凱", confirm=True))
        out = capsys.readouterr().out
        assert "智凱" in out
        assert mock_save.call_count == 2  # people + events

    @patch("people_db._load_jsonl")
    def test_delete_person_without_confirm_warns(self, mock_load, capsys):
        mock_load.side_effect = [
            [_person()],
            [_event()],
        ]
        people_db.cmd_delete(Namespace(target="智凱", confirm=False))
        out = capsys.readouterr().out
        assert "--confirm" in out


# ===========================================================================
# cmd_scan()
# ===========================================================================

class TestCmdScan:
    @patch("people_db.subprocess.run")
    @patch("people_db._load_jsonl", return_value=[_person()])
    def test_scan_success(self, mock_load, mock_run, capsys, tmp_path):
        scan_results = {
            "results": [{
                "date": "2026-02-20",
                "mood": "4",
                "energy": "3",
                "snippets": ["智凱提到 AudioMatters 的進度"],
                "diary_length": 500,
            }]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(scan_results), returncode=0,
        )
        out_file = str(tmp_path / "scan.json")
        args = Namespace(name="智凱", start=None, end=None, max=100,
                         context=120, output=out_file)
        people_db.cmd_scan(args)
        out = capsys.readouterr().out
        assert "1 天" in out

    @patch("people_db.subprocess.run")
    @patch("people_db._load_jsonl", return_value=[_person()])
    def test_scan_failure_prints_error(self, mock_load, mock_run, capsys):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="test", timeout=30)
        args = Namespace(name="智凱", start=None, end=None, max=100,
                         context=120, output=None)
        people_db.cmd_scan(args)
        err = capsys.readouterr().err
        assert "失敗" in err


# ===========================================================================
# cmd_import_scan()
# ===========================================================================

class TestCmdImportScan:
    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl")
    def test_import_scan_basic(self, mock_load, mock_append, capsys, tmp_path):
        scan_file = tmp_path / "scan.json"
        scan_data = {
            "entries": [
                {"date": "2026-02-20", "summary": "Lab meeting about AudioMatters",
                 "snippets": ["snippet1"]},
            ]
        }
        scan_file.write_text(json.dumps(scan_data))
        mock_load.side_effect = [[_person()], []]  # people, events

        args = Namespace(name="智凱", file=str(scan_file))
        people_db.cmd_import_scan(args)
        out = capsys.readouterr().out
        assert "匯入 1 筆" in out

    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl")
    def test_import_dedup_skips_existing(self, mock_load, mock_append, capsys, tmp_path):
        scan_file = tmp_path / "scan.json"
        scan_data = {
            "entries": [
                {"date": "2026-02-20", "summary": "Lab meeting about AudioMatters"},
            ]
        }
        scan_file.write_text(json.dumps(scan_data))
        existing_event = _event(summary="Lab meeting about AudioMatters",
                                date="2026-02-20")
        mock_load.side_effect = [[_person()], [existing_event]]

        args = Namespace(name="智凱", file=str(scan_file))
        people_db.cmd_import_scan(args)
        out = capsys.readouterr().out
        assert "跳過 1 筆" in out

    @patch("people_db._load_jsonl")
    def test_import_scan_no_entries(self, mock_load, capsys, tmp_path):
        scan_file = tmp_path / "scan.json"
        scan_file.write_text('{"entries": []}')
        mock_load.side_effect = [[_person()], []]

        args = Namespace(name="智凱", file=str(scan_file))
        people_db.cmd_import_scan(args)
        out = capsys.readouterr().out
        assert "沒有可匯入" in out

    @patch("people_db._load_jsonl", return_value=[])
    def test_import_scan_person_not_found_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_import_scan(Namespace(name="NoOne", file="/tmp/x.json"))

    @patch("people_db._load_jsonl", return_value=[_person()])
    def test_import_scan_file_not_found_exits(self, mock_load):
        with pytest.raises(SystemExit):
            people_db.cmd_import_scan(Namespace(name="智凱", file="/nonexistent/path.json"))

    @patch("people_db._append_jsonl")
    @patch("people_db._load_jsonl")
    def test_import_auto_summary_from_snippet(self, mock_load, mock_append, capsys, tmp_path):
        """Entries without summary but with snippets get auto-generated summary."""
        scan_file = tmp_path / "scan.json"
        scan_data = {
            "entries": [
                {"date": "2026-02-20", "snippets": ["This is a snippet about something"]},
            ]
        }
        scan_file.write_text(json.dumps(scan_data))
        mock_load.side_effect = [[_person()], []]

        args = Namespace(name="智凱", file=str(scan_file))
        people_db.cmd_import_scan(args)
        assert mock_append.called
        event = mock_append.call_args[0][1]
        assert event["summary"].startswith("This is a snippet")


# ===========================================================================
# cmd_stats()
# ===========================================================================

class TestCmdStats:
    @patch("people_db._load_jsonl")
    def test_stats_empty(self, mock_load, capsys):
        mock_load.side_effect = [[], []]
        people_db.cmd_stats(Namespace())
        out = capsys.readouterr().out
        assert "人數: 0" in out
        assert "事件: 0" in out

    @patch("people_db._load_jsonl")
    def test_stats_with_data(self, mock_load, capsys):
        mock_load.side_effect = [
            [_person(), _person(id="P002", name="晨安")],
            [_event(), _event(id="E002", person_id="P002", person_name="晨安")],
        ]
        people_db.cmd_stats(Namespace())
        out = capsys.readouterr().out
        assert "人數: 2" in out
        assert "事件: 2" in out
