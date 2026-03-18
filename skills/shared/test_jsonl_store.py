#!/usr/bin/env python3
"""
Unit tests for skills/shared/jsonl_store.py

Covers:
- find_workspace() — git-based discovery and fallback path
- JsonlStore.load() — empty file, valid JSONL, corrupt lines, missing file
- JsonlStore.append() — auto ID assignment, multi-append ordering
- JsonlStore.next_id() — sequencing, items without valid IDs, empty store
- JsonlStore.update() — found / not-found, atomic rewrite integrity
- JsonlStore.find() — existing and missing IDs
- JsonlStore.filter() — single field, multiple fields, no match
- JsonlStore._atomic_rewrite() — temp-file-then-rename strategy

Usage:
    python3 -m pytest skills/shared/test_jsonl_store.py -v
    python3 skills/shared/test_jsonl_store.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Make the module importable regardless of cwd
# (Force-load from this directory to avoid stale sys.modules stubs.)
# ---------------------------------------------------------------------------
SHARED_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SHARED_DIR))

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("jsonl_store", SHARED_DIR / "jsonl_store.py")
jsonl_store = importlib.util.module_from_spec(_spec)
sys.modules["jsonl_store"] = jsonl_store
_spec.loader.exec_module(jsonl_store)
from jsonl_store import JsonlStore, find_workspace  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(tmp_dir: Path, rel_path: str = "data/items.jsonl",
                prefix: str = "IT") -> JsonlStore:
    """
    Return a JsonlStore whose WORKSPACE is pinned to tmp_dir so every
    test runs in complete isolation from the real workspace.
    """
    store = JsonlStore.__new__(JsonlStore)
    store.path = tmp_dir / rel_path
    store.prefix = prefix
    return store


# ---------------------------------------------------------------------------
# Tests: find_workspace()
# ---------------------------------------------------------------------------

class TestFindWorkspace(unittest.TestCase):
    """find_workspace() resolves via git and falls back gracefully."""

    def test_returns_path_object(self):
        result = find_workspace()
        self.assertIsInstance(result, Path)

    def test_git_success_returns_stripped_path(self):
        with patch("jsonl_store.subprocess.check_output") as mock_co:
            mock_co.return_value = "/home/user/myrepo\n"
            result = find_workspace()
        self.assertEqual(result, Path("/home/user/myrepo"))

    def test_called_process_error_falls_back(self):
        import subprocess
        with patch("jsonl_store.subprocess.check_output",
                   side_effect=subprocess.CalledProcessError(128, "git")):
            result = find_workspace()
        self.assertEqual(result, Path.home() / ".openclaw" / "workspace")

    def test_file_not_found_falls_back(self):
        with patch("jsonl_store.subprocess.check_output",
                   side_effect=FileNotFoundError("git not found")):
            result = find_workspace()
        self.assertEqual(result, Path.home() / ".openclaw" / "workspace")

    def test_git_path_has_no_trailing_whitespace(self):
        with patch("jsonl_store.subprocess.check_output") as mock_co:
            mock_co.return_value = "  /opt/workspace  \n"
            result = find_workspace()
        self.assertEqual(result, Path("/opt/workspace"))


# ---------------------------------------------------------------------------
# Tests: JsonlStore.load()
# ---------------------------------------------------------------------------

class TestJsonlStoreLoad(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_load_missing_file_returns_empty_list(self):
        store = _make_store(self.tmp)
        self.assertEqual(store.load(), [])

    def test_load_empty_file_returns_empty_list(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text("")
        self.assertEqual(store.load(), [])

    def test_load_single_valid_line(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps({"id": "IT-001", "name": "alpha"}) + "\n")
        items = store.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "IT-001")
        self.assertEqual(items[0]["name"], "alpha")

    def test_load_multiple_valid_lines(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps({"id": "IT-001", "val": 1}),
            json.dumps({"id": "IT-002", "val": 2}),
            json.dumps({"id": "IT-003", "val": 3}),
        ]
        store.path.write_text("\n".join(lines) + "\n")
        items = store.load()
        self.assertEqual(len(items), 3)
        self.assertEqual([i["id"] for i in items], ["IT-001", "IT-002", "IT-003"])

    def test_load_skips_corrupt_lines(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            json.dumps({"id": "IT-001"}) + "\n" +
            "this is not json\n" +
            json.dumps({"id": "IT-002"}) + "\n"
        )
        store.path.write_text(content)
        items = store.load()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["id"], "IT-001")
        self.assertEqual(items[1]["id"], "IT-002")

    def test_load_corrupt_line_prints_to_stderr(self):
        import io
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text("not-json\n")
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            store.load()
        self.assertIn("malformed", buf.getvalue())

    def test_load_blank_lines_are_skipped(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(
            json.dumps({"id": "IT-001"}) + "\n\n   \n"
            + json.dumps({"id": "IT-002"}) + "\n"
        )
        items = store.load()
        self.assertEqual(len(items), 2)

    def test_load_preserves_unicode(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(
            json.dumps({"id": "IT-001", "note": "你好世界"}, ensure_ascii=False) + "\n"
        )
        items = store.load()
        self.assertEqual(items[0]["note"], "你好世界")

    def test_load_all_corrupt_returns_empty_list(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text("bad1\nbad2\nbad3\n")
        items = store.load()
        self.assertEqual(items, [])


# ---------------------------------------------------------------------------
# Tests: JsonlStore.next_id()
# ---------------------------------------------------------------------------

class TestJsonlStoreNextId(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_next_id_empty_store(self):
        store = _make_store(self.tmp, prefix="EXP")
        self.assertEqual(store.next_id([]), "EXP-001")

    def test_next_id_after_one_item(self):
        store = _make_store(self.tmp, prefix="EXP")
        self.assertEqual(store.next_id([{"id": "EXP-001"}]), "EXP-002")

    def test_next_id_sequential(self):
        store = _make_store(self.tmp, prefix="EXP")
        items = [{"id": f"EXP-{n:03d}"} for n in range(1, 6)]
        self.assertEqual(store.next_id(items), "EXP-006")

    def test_next_id_skips_gaps(self):
        store = _make_store(self.tmp, prefix="EXP")
        items = [{"id": "EXP-001"}, {"id": "EXP-005"}]
        self.assertEqual(store.next_id(items), "EXP-006")

    def test_next_id_ignores_missing_id_field(self):
        store = _make_store(self.tmp, prefix="EXP")
        items = [{"name": "no id here"}, {"id": "EXP-003"}]
        self.assertEqual(store.next_id(items), "EXP-004")

    def test_next_id_ignores_malformed_id(self):
        store = _make_store(self.tmp, prefix="EXP")
        items = [{"id": "NOTANUMBER"}, {"id": "EXP-002"}]
        self.assertEqual(store.next_id(items), "EXP-003")

    def test_next_id_uses_custom_prefix(self):
        store = _make_store(self.tmp, prefix="TASK")
        self.assertEqual(store.next_id([]), "TASK-001")

    def test_next_id_none_loads_from_file(self):
        store = _make_store(self.tmp, prefix="IT")
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps({"id": "IT-007"}) + "\n")
        self.assertEqual(store.next_id(None), "IT-008")

    def test_next_id_three_digit_padding(self):
        store = _make_store(self.tmp, prefix="X")
        items = [{"id": "X-009"}]
        nid = store.next_id(items)
        self.assertEqual(nid, "X-010")
        # Verify zero-padding for numbers < 100
        self.assertEqual(len(nid.split("-")[1]), 3)


# ---------------------------------------------------------------------------
# Tests: JsonlStore.append()
# ---------------------------------------------------------------------------

class TestJsonlStoreAppend(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_append_creates_parent_dirs(self):
        store = _make_store(self.tmp, rel_path="deep/nested/items.jsonl")
        store.append({"name": "test"})
        self.assertTrue(store.path.exists())

    def test_append_assigns_id_automatically(self):
        store = _make_store(self.tmp, prefix="IT")
        item = store.append({"name": "first"})
        self.assertEqual(item["id"], "IT-001")

    def test_append_second_item_increments_id(self):
        store = _make_store(self.tmp, prefix="IT")
        store.append({"name": "first"})
        item2 = store.append({"name": "second"})
        self.assertEqual(item2["id"], "IT-002")

    def test_append_preserves_explicit_id(self):
        store = _make_store(self.tmp, prefix="IT")
        item = store.append({"id": "CUSTOM-99", "name": "explicit"})
        self.assertEqual(item["id"], "CUSTOM-99")

    def test_append_returns_item_with_id(self):
        store = _make_store(self.tmp, prefix="IT")
        result = store.append({"val": 42})
        self.assertIn("id", result)
        self.assertEqual(result["val"], 42)

    def test_append_persists_to_disk(self):
        store = _make_store(self.tmp, prefix="IT")
        store.append({"name": "persisted"})
        items = store.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "persisted")

    def test_append_multiple_items_all_present(self):
        store = _make_store(self.tmp, prefix="IT")
        for i in range(5):
            store.append({"seq": i})
        items = store.load()
        self.assertEqual(len(items), 5)
        self.assertEqual([x["seq"] for x in items], list(range(5)))

    def test_append_preserves_unicode(self):
        store = _make_store(self.tmp, prefix="IT")
        store.append({"note": "台灣 🇹🇼"})
        items = store.load()
        self.assertEqual(items[0]["note"], "台灣 🇹🇼")

    def test_append_mutates_item_in_place(self):
        store = _make_store(self.tmp, prefix="IT")
        original = {"name": "mut"}
        returned = store.append(original)
        self.assertIs(returned, original)
        self.assertIn("id", original)


# ---------------------------------------------------------------------------
# Tests: JsonlStore.update()
# ---------------------------------------------------------------------------

class TestJsonlStoreUpdate(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.store = _make_store(self.tmp, prefix="IT")
        self.store.append({"name": "alpha", "status": "pending"})
        self.store.append({"name": "beta",  "status": "pending"})
        self.store.append({"name": "gamma", "status": "pending"})

    def tearDown(self):
        self._td.cleanup()

    def test_update_existing_item_returns_updated_dict(self):
        result = self.store.update("IT-002", {"status": "done"})
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["name"], "beta")

    def test_update_missing_id_returns_none(self):
        result = self.store.update("IT-999", {"status": "done"})
        self.assertIsNone(result)

    def test_update_persisted_after_reload(self):
        self.store.update("IT-001", {"status": "archived"})
        items = self.store.load()
        item1 = next(i for i in items if i["id"] == "IT-001")
        self.assertEqual(item1["status"], "archived")

    def test_update_does_not_affect_other_items(self):
        self.store.update("IT-002", {"status": "done"})
        items = self.store.load()
        others = [i for i in items if i["id"] != "IT-002"]
        for item in others:
            self.assertEqual(item["status"], "pending")

    def test_update_all_items_count_unchanged(self):
        self.store.update("IT-001", {"extra": "field"})
        self.assertEqual(len(self.store.load()), 3)

    def test_update_can_add_new_fields(self):
        self.store.update("IT-003", {"score": 99, "reviewed": True})
        result = self.store.find("IT-003")
        self.assertEqual(result["score"], 99)
        self.assertTrue(result["reviewed"])

    def test_update_overwrites_existing_field(self):
        self.store.update("IT-001", {"name": "ALPHA_UPDATED"})
        result = self.store.find("IT-001")
        self.assertEqual(result["name"], "ALPHA_UPDATED")


# ---------------------------------------------------------------------------
# Tests: JsonlStore.find()
# ---------------------------------------------------------------------------

class TestJsonlStoreFind(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.store = _make_store(self.tmp, prefix="IT")
        self.store.append({"name": "alpha"})
        self.store.append({"name": "beta"})

    def tearDown(self):
        self._td.cleanup()

    def test_find_existing_id(self):
        item = self.store.find("IT-001")
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], "alpha")

    def test_find_missing_id_returns_none(self):
        self.assertIsNone(self.store.find("IT-999"))

    def test_find_returns_correct_item(self):
        item = self.store.find("IT-002")
        self.assertEqual(item["name"], "beta")


# ---------------------------------------------------------------------------
# Tests: JsonlStore.filter()
# ---------------------------------------------------------------------------

class TestJsonlStoreFilter(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.store = _make_store(self.tmp, prefix="IT")
        self.store.append({"name": "a", "status": "open",   "priority": "high"})
        self.store.append({"name": "b", "status": "closed", "priority": "low"})
        self.store.append({"name": "c", "status": "open",   "priority": "low"})
        self.store.append({"name": "d", "status": "open",   "priority": "high"})

    def tearDown(self):
        self._td.cleanup()

    def test_filter_single_field(self):
        results = self.store.filter(status="open")
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r["status"] == "open" for r in results))

    def test_filter_no_match_returns_empty(self):
        results = self.store.filter(status="nonexistent")
        self.assertEqual(results, [])

    def test_filter_multiple_fields(self):
        results = self.store.filter(status="open", priority="high")
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r["status"], "open")
            self.assertEqual(r["priority"], "high")

    def test_filter_all_match(self):
        # Every item has a name field; filtering by a unique name gives 1 result
        results = self.store.filter(name="b")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "closed")


# ---------------------------------------------------------------------------
# Tests: JsonlStore._atomic_rewrite()
# ---------------------------------------------------------------------------

class TestJsonlStoreAtomicRewrite(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_atomic_rewrite_creates_file(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        items = [{"id": "IT-001", "val": 1}, {"id": "IT-002", "val": 2}]
        store._atomic_rewrite(items)
        self.assertTrue(store.path.exists())

    def test_atomic_rewrite_content_matches(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        items = [{"id": "IT-001", "val": "x"}, {"id": "IT-002", "val": "y"}]
        store._atomic_rewrite(items)
        loaded = store.load()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["val"], "x")
        self.assertEqual(loaded[1]["val"], "y")

    def test_atomic_rewrite_overwrites_existing(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps({"id": "OLD-001"}) + "\n")
        store._atomic_rewrite([{"id": "NEW-001"}])
        items = store.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "NEW-001")

    def test_atomic_rewrite_leaves_no_temp_files(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store._atomic_rewrite([{"id": "IT-001"}])
        tmp_files = list(store.path.parent.glob("*.tmp"))
        self.assertEqual(tmp_files, [], msg=f"Temp files left behind: {tmp_files}")

    def test_atomic_rewrite_empty_list_clears_file(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps({"id": "IT-001"}) + "\n")
        store._atomic_rewrite([])
        items = store.load()
        self.assertEqual(items, [])

    def test_atomic_rewrite_preserves_unicode(self):
        store = _make_store(self.tmp)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store._atomic_rewrite([{"id": "IT-001", "text": "日本語テスト"}])
        items = store.load()
        self.assertEqual(items[0]["text"], "日本語テスト")


# ---------------------------------------------------------------------------
# Integration: combined append + update + reload round-trip
# ---------------------------------------------------------------------------

class TestJsonlStoreRoundTrip(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_append_update_find_round_trip(self):
        store = _make_store(self.tmp, prefix="RT")
        store.append({"task": "write tests", "done": False})
        store.append({"task": "run tests",   "done": False})
        store.update("RT-001", {"done": True})
        item = store.find("RT-001")
        self.assertTrue(item["done"])
        item2 = store.find("RT-002")
        self.assertFalse(item2["done"])

    def test_load_after_append_reflects_all_items(self):
        store = _make_store(self.tmp, prefix="LT")
        for i in range(10):
            store.append({"seq": i})
        items = store.load()
        self.assertEqual(len(items), 10)
        self.assertEqual([x["seq"] for x in items], list(range(10)))

    def test_concurrent_style_separate_stores_same_file(self):
        """
        Two store handles pointing at the same file should each see
        the other's writes after a reload — simulating sequential access
        from two processes that share the file path.
        """
        store_a = _make_store(self.tmp, rel_path="shared.jsonl", prefix="S")
        store_b = _make_store(self.tmp, rel_path="shared.jsonl", prefix="S")

        store_a.append({"writer": "A", "val": 1})
        store_b.append({"writer": "B", "val": 2})

        items_via_a = store_a.load()
        items_via_b = store_b.load()

        self.assertEqual(len(items_via_a), 2)
        self.assertEqual(items_via_a, items_via_b)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (
        TestFindWorkspace,
        TestJsonlStoreLoad,
        TestJsonlStoreNextId,
        TestJsonlStoreAppend,
        TestJsonlStoreUpdate,
        TestJsonlStoreFind,
        TestJsonlStoreFilter,
        TestJsonlStoreAtomicRewrite,
        TestJsonlStoreRoundTrip,
    ):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
