"""
Unit tests for learn.py — self-improvement CLI.

Mocking strategy
----------------
The shared package is stubbed into sys.modules *before* learn is imported so
that the module-level call to find_workspace() and the JsonlStore name-binding
both resolve to our controlled mocks.  Per-test patching is then done via
@patch("learn.JsonlStore") so each test gets a fresh MagicMock instance.
"""

import importlib
import json
import pathlib
import sys
import types
from argparse import Namespace
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: stub the shared package before learn is imported
# ---------------------------------------------------------------------------

_shared_pkg = types.ModuleType("shared")
_jsonl_mod = types.ModuleType("shared.jsonl_store")
_jsonl_mod.find_workspace = MagicMock(return_value=MagicMock())
_jsonl_mod.JsonlStore = MagicMock()

sys.modules.setdefault("shared", _shared_pkg)
sys.modules.setdefault("shared.jsonl_store", _jsonl_mod)

# Ensure the scripts directory is on the path so `import learn` resolves.
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import learn  # noqa: E402  (must come after sys.modules manipulation)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LEARNINGS_PATH = learn.LEARNINGS_PATH
ERRORS_PATH = learn.ERRORS_PATH


def _make_store(items=None, find_result=None, append_result=None):
    """Return a MagicMock that behaves like a JsonlStore instance."""
    store = MagicMock()
    store.load.return_value = items if items is not None else []
    store.find.return_value = find_result
    store.append.return_value = append_result or {"id": "LRN-001"}
    store.update.return_value = MagicMock()
    return store


def _lrn(id="LRN-001", summary="test summary", status="pending",
         recurrence=1, pattern_key="", action="", details="",
         promoted_to=None):
    return {
        "id": id,
        "summary": summary,
        "status": status,
        "recurrence": recurrence,
        "pattern_key": pattern_key,
        "action": action,
        "details": details,
        "promoted_to": promoted_to,
        "priority": "medium",
        "category": "correction",
    }


def _err(id="ERR-001", summary="an error", status="pending",
         recurrence=1, pattern_key="", fix="", prevention=""):
    return {
        "id": id,
        "summary": summary,
        "status": status,
        "recurrence": recurrence,
        "pattern_key": pattern_key,
        "fix": fix,
        "prevention": prevention,
    }


# ===========================================================================
# similarity() and find_similar()
# ===========================================================================

class TestSimilarity:
    def test_identical_strings_return_1(self):
        assert learn.similarity("hello world", "hello world") == 1.0

    def test_identical_strings_case_insensitive(self):
        assert learn.similarity("Hello", "hello") == 1.0

    def test_completely_different_strings_near_zero(self):
        ratio = learn.similarity("aaaa", "zzzz")
        assert ratio < 0.1

    def test_partial_overlap_between_0_and_1(self):
        ratio = learn.similarity("hello world", "hello there")
        assert 0.0 < ratio < 1.0


class TestFindSimilar:
    def _store_with(self, items):
        s = MagicMock()
        s.load.return_value = items
        return s

    def test_empty_store_returns_empty_list(self):
        store = self._store_with([])
        assert learn.find_similar(store, "anything") == []

    def test_returns_items_above_threshold(self):
        item = _lrn(summary="use absolute paths always")
        store = self._store_with([item])
        result = learn.find_similar(store, "use absolute paths always")
        assert item in result

    def test_does_not_return_items_below_threshold(self):
        item = _lrn(summary="aaaaaaaaaa")
        store = self._store_with([item])
        result = learn.find_similar(store, "zzzzzzzzzz")
        assert result == []

    def test_matches_exact_pattern_key_even_below_text_threshold(self):
        item = _lrn(summary="aaaaaaaaaa", pattern_key="key.match")
        store = self._store_with([item])
        result = learn.find_similar(store, "zzzzzzzzzz", pattern_key="key.match")
        assert item in result

    def test_pattern_key_match_does_not_also_add_via_similarity(self):
        """An item matching by pattern_key should not be duplicated via similarity."""
        item = _lrn(summary="exact same text", pattern_key="my.key")
        store = self._store_with([item])
        result = learn.find_similar(store, "exact same text", pattern_key="my.key")
        assert result.count(item) == 1

    def test_deduplicates_items_with_same_id(self):
        """Two entries with the same id should appear only once."""
        item1 = _lrn(id="LRN-001", summary="same summary", pattern_key="key.a")
        item2 = dict(item1)  # same id, different object
        store = self._store_with([item1, item2])
        result = learn.find_similar(store, "same summary", pattern_key="key.a")
        ids = [i["id"] for i in result]
        assert ids.count("LRN-001") == 1

    def test_threshold_boundary_at_exactly_0_6_is_included(self):
        """Items at exactly threshold are included."""
        # "abcde" vs "abcde" is 1.0, we need to find a pair that sits at ~0.6.
        # We use a pair that we know gives >=0.6 via SequenceMatcher.
        a = "hello world test"
        b = "hello world abcd"
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
        assert ratio >= 0.6
        item = _lrn(summary=b)
        store = self._store_with([item])
        result = learn.find_similar(store, a, threshold=0.6)
        assert item in result


# ===========================================================================
# cmd_log()
# ===========================================================================

class TestCmdLog:
    def _args(self, summary="a new learning", category="correction",
              priority="medium", details="", action="", pattern_key="",
              force=False):
        return Namespace(
            summary=summary, category=category, priority=priority,
            details=details, action=action, pattern_key=pattern_key,
            force=force,
        )

    @patch("learn.JsonlStore")
    def test_new_entry_calls_append_with_correct_shape(self, MockStore, capsys):
        store = _make_store(items=[], append_result={"id": "LRN-001"})
        MockStore.return_value = store

        args = self._args(summary="use absolute paths", details="always", action="fix it")
        learn.cmd_log(args)

        assert store.append.called
        appended = store.append.call_args[0][0]
        assert appended["summary"] == "use absolute paths"
        assert appended["category"] == "correction"
        assert appended["priority"] == "medium"
        assert appended["status"] == "pending"
        assert appended["details"] == "always"
        assert appended["action"] == "fix it"
        assert appended["recurrence"] == 1
        assert appended["see_also"] == []
        assert appended["promoted_to"] is None

    @patch("learn.JsonlStore")
    def test_new_entry_prints_success(self, MockStore, capsys):
        store = _make_store(items=[], append_result={"id": "LRN-042"})
        MockStore.return_value = store

        learn.cmd_log(self._args(summary="my learning"))

        out = capsys.readouterr().out
        assert "LRN-042" in out
        assert "my learning" in out

    @patch("learn.JsonlStore")
    def test_dedup_similar_entry_calls_update_not_append(self, MockStore, capsys):
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        args = self._args(summary="use absolute paths always")
        learn.cmd_log(args)

        assert store.update.called
        assert not store.append.called

    @patch("learn.JsonlStore")
    def test_dedup_bumps_recurrence(self, MockStore, capsys):
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_log(self._args(summary="use absolute paths always"))

        updates = store.update.call_args[0][1]
        assert updates["recurrence"] == 2

    @patch("learn.JsonlStore")
    def test_dedup_prints_bump_message(self, MockStore, capsys):
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_log(self._args(summary="use absolute paths always"))

        out = capsys.readouterr().out
        assert "LRN-001" in out
        assert "2x" in out

    @patch("learn.JsonlStore")
    def test_dedup_recurrence_reaches_threshold_prints_promotion_notice(
        self, MockStore, capsys
    ):
        # recurrence=2 → bumped to 3 → equals PROMOTION_THRESHOLD
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=2)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_log(self._args(summary="use absolute paths always"))

        out = capsys.readouterr().out
        assert "PROMOTION READY" in out
        assert "LRN-001" in out

    @patch("learn.JsonlStore")
    def test_dedup_below_threshold_no_promotion_notice(self, MockStore, capsys):
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_log(self._args(summary="use absolute paths always"))

        out = capsys.readouterr().out
        assert "PROMOTION READY" not in out

    @patch("learn.JsonlStore")
    def test_force_flag_always_appends_even_when_similar_exists(
        self, MockStore, capsys
    ):
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=1)
        store = _make_store(items=[existing], append_result={"id": "LRN-002"})
        MockStore.return_value = store

        args = self._args(summary="use absolute paths always", force=True)
        learn.cmd_log(args)

        assert store.append.called
        assert not store.update.called

    @patch("learn.JsonlStore")
    def test_dedup_pattern_key_match_triggers_bump(self, MockStore, capsys):
        existing = _lrn(id="LRN-001", summary="totally different text",
                        pattern_key="path.absolute", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        args = self._args(summary="something else entirely", pattern_key="path.absolute")
        learn.cmd_log(args)

        assert store.update.called
        assert not store.append.called

    @patch("learn.JsonlStore")
    def test_dedup_details_and_action_included_in_updates_when_provided(
        self, MockStore, capsys
    ):
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        args = self._args(
            summary="use absolute paths always",
            details="new details here",
            action="new action here",
        )
        learn.cmd_log(args)

        updates = store.update.call_args[0][1]
        assert updates["details"] == "new details here"
        assert updates["action"] == "new action here"

    @patch("learn.JsonlStore")
    def test_dedup_details_and_action_absent_from_updates_when_not_provided(
        self, MockStore, capsys
    ):
        existing = _lrn(id="LRN-001", summary="use absolute paths always", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        args = self._args(summary="use absolute paths always", details="", action="")
        learn.cmd_log(args)

        updates = store.update.call_args[0][1]
        assert "details" not in updates
        assert "action" not in updates

    @patch("learn.JsonlStore")
    def test_jsonlstore_constructed_with_learnings_path_and_lrn_prefix(
        self, MockStore, capsys
    ):
        store = _make_store(items=[], append_result={"id": "LRN-001"})
        MockStore.return_value = store

        learn.cmd_log(self._args())

        MockStore.assert_called_once_with(LEARNINGS_PATH, prefix="LRN")


# ===========================================================================
# cmd_error()
# ===========================================================================

class TestCmdError:
    def _args(self, summary="an error occurred", error="traceback here",
              fix="", prevention="", pattern_key="", force=False):
        return Namespace(
            summary=summary, error=error, fix=fix,
            prevention=prevention, pattern_key=pattern_key, force=force,
        )

    @patch("learn.JsonlStore")
    def test_new_entry_without_fix_has_status_pending(self, MockStore, capsys):
        store = _make_store(items=[], append_result={"id": "ERR-001"})
        MockStore.return_value = store

        learn.cmd_error(self._args(fix=""))

        appended = store.append.call_args[0][0]
        assert appended["status"] == "pending"

    @patch("learn.JsonlStore")
    def test_new_entry_with_fix_has_status_resolved(self, MockStore, capsys):
        store = _make_store(items=[], append_result={"id": "ERR-001"})
        MockStore.return_value = store

        learn.cmd_error(self._args(fix="the fix description"))

        appended = store.append.call_args[0][0]
        assert appended["status"] == "resolved"

    @patch("learn.JsonlStore")
    def test_new_entry_prints_success_pending(self, MockStore, capsys):
        store = _make_store(items=[], append_result={"id": "ERR-007"})
        MockStore.return_value = store

        learn.cmd_error(self._args(summary="crash on startup", fix=""))

        out = capsys.readouterr().out
        assert "ERR-007" in out
        assert "pending" in out

    @patch("learn.JsonlStore")
    def test_new_entry_prints_success_resolved(self, MockStore, capsys):
        store = _make_store(items=[], append_result={"id": "ERR-007"})
        MockStore.return_value = store

        learn.cmd_error(self._args(summary="crash on startup", fix="patched"))

        out = capsys.readouterr().out
        assert "resolved" in out

    @patch("learn.JsonlStore")
    def test_dedup_similar_error_bumps_recurrence(self, MockStore, capsys):
        existing = _err(id="ERR-001", summary="crash on startup", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_error(self._args(summary="crash on startup"))

        assert store.update.called
        updates = store.update.call_args[0][1]
        assert updates["recurrence"] == 2

    @patch("learn.JsonlStore")
    def test_dedup_prints_bump_message(self, MockStore, capsys):
        existing = _err(id="ERR-001", summary="crash on startup", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_error(self._args(summary="crash on startup"))

        out = capsys.readouterr().out
        assert "ERR-001" in out
        assert "2x" in out

    @patch("learn.JsonlStore")
    def test_dedup_with_fix_adds_resolved_status_to_updates(self, MockStore, capsys):
        existing = _err(id="ERR-001", summary="crash on startup", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_error(self._args(summary="crash on startup", fix="apply the patch"))

        updates = store.update.call_args[0][1]
        assert updates["status"] == "resolved"
        assert updates["fix"] == "apply the patch"

    @patch("learn.JsonlStore")
    def test_dedup_without_fix_does_not_include_status_in_updates(
        self, MockStore, capsys
    ):
        existing = _err(id="ERR-001", summary="crash on startup", recurrence=1)
        store = _make_store(items=[existing])
        MockStore.return_value = store

        learn.cmd_error(self._args(summary="crash on startup", fix=""))

        updates = store.update.call_args[0][1]
        assert "status" not in updates

    @patch("learn.JsonlStore")
    def test_force_always_appends(self, MockStore, capsys):
        existing = _err(id="ERR-001", summary="crash on startup", recurrence=1)
        store = _make_store(items=[existing], append_result={"id": "ERR-002"})
        MockStore.return_value = store

        learn.cmd_error(self._args(summary="crash on startup", force=True))

        assert store.append.called
        assert not store.update.called

    @patch("learn.JsonlStore")
    def test_jsonlstore_constructed_with_errors_path_and_err_prefix(
        self, MockStore, capsys
    ):
        store = _make_store(items=[], append_result={"id": "ERR-001"})
        MockStore.return_value = store

        learn.cmd_error(self._args())

        MockStore.assert_called_once_with(ERRORS_PATH, prefix="ERR")


# ===========================================================================
# cmd_resolve()
# ===========================================================================

class TestCmdResolve:
    def _args(self, entry_id, notes=""):
        return Namespace(entry_id=entry_id, notes=notes)

    @patch("learn.JsonlStore")
    def test_lrn_prefix_uses_learnings_store(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("LRN-001"))

        MockStore.assert_called_once_with(LEARNINGS_PATH, prefix="LRN")

    @patch("learn.JsonlStore")
    def test_err_prefix_uses_errors_store(self, MockStore, capsys):
        item = _err(id="ERR-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("ERR-001"))

        MockStore.assert_called_once_with(ERRORS_PATH, prefix="ERR")

    @patch("learn.JsonlStore")
    def test_unknown_prefix_exits_with_error(self, MockStore, capsys):
        store = _make_store()
        MockStore.return_value = store

        with pytest.raises(SystemExit) as exc_info:
            learn.cmd_resolve(self._args("XYZ-001"))

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Unknown ID prefix" in err

    @patch("learn.JsonlStore")
    def test_item_not_found_exits_with_error(self, MockStore, capsys):
        store = _make_store(find_result=None)
        MockStore.return_value = store

        with pytest.raises(SystemExit) as exc_info:
            learn.cmd_resolve(self._args("LRN-999"))

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "not found" in err

    @patch("learn.JsonlStore")
    def test_already_resolved_prints_warning_no_update(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="resolved")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("LRN-001"))

        assert not store.update.called
        out = capsys.readouterr().out
        assert "already resolved" in out

    @patch("learn.JsonlStore")
    def test_resolve_lrn_with_notes_sets_action(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("LRN-001", notes="fixed by doing X"))

        updates = store.update.call_args[0][1]
        assert updates["action"] == "fixed by doing X"
        assert "fix" not in updates

    @patch("learn.JsonlStore")
    def test_resolve_err_with_notes_sets_fix(self, MockStore, capsys):
        item = _err(id="ERR-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("ERR-001", notes="applied the patch"))

        updates = store.update.call_args[0][1]
        assert updates["fix"] == "applied the patch"
        assert "action" not in updates

    @patch("learn.JsonlStore")
    def test_resolve_without_notes_does_not_include_notes_key(
        self, MockStore, capsys
    ):
        item = _lrn(id="LRN-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("LRN-001", notes=""))

        updates = store.update.call_args[0][1]
        assert "action" not in updates
        assert "fix" not in updates

    @patch("learn.JsonlStore")
    def test_resolve_sets_status_resolved_in_updates(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("LRN-001"))

        updates = store.update.call_args[0][1]
        assert updates["status"] == "resolved"

    @patch("learn.JsonlStore")
    def test_resolve_prints_success_message(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_resolve(self._args("LRN-001"))

        out = capsys.readouterr().out
        assert "LRN-001" in out
        assert "resolved" in out

    @patch("learn.JsonlStore")
    def test_entry_id_is_uppercased_before_lookup(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        # Pass lowercase; should still resolve correctly
        learn.cmd_resolve(self._args("lrn-001"))

        store.find.assert_called_once_with("LRN-001")


# ===========================================================================
# cmd_review()
# ===========================================================================

class TestCmdReview:
    def _args(self, json_out=False, promote_ready=False):
        return Namespace(json=json_out, promote_ready=promote_ready)

    def _two_stores(self, MockStore, learnings, errors):
        """Configure MockStore so first call returns lrn store, second returns err store."""
        lrn_store = _make_store(items=learnings)
        err_store = _make_store(items=errors)
        MockStore.side_effect = [lrn_store, err_store]
        return lrn_store, err_store

    @patch("learn.JsonlStore")
    def test_json_output_counts_pending_learnings(self, MockStore, capsys):
        learnings = [
            _lrn(id="LRN-001", status="pending"),
            _lrn(id="LRN-002", status="resolved"),
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        assert data["pending_learnings"] == 1

    @patch("learn.JsonlStore")
    def test_json_output_counts_pending_errors(self, MockStore, capsys):
        errors = [
            _err(id="ERR-001", status="pending"),
            _err(id="ERR-002", status="resolved"),
            _err(id="ERR-003", status="pending"),
        ]
        self._two_stores(MockStore, [], errors)

        learn.cmd_review(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        assert data["pending_errors"] == 2

    @patch("learn.JsonlStore")
    def test_json_output_promote_ready_excludes_already_promoted(
        self, MockStore, capsys
    ):
        learnings = [
            _lrn(id="LRN-001", status="pending", recurrence=3),
            _lrn(id="LRN-002", status="promoted", recurrence=4),  # excluded
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        assert data["promote_ready"] == 1

    @patch("learn.JsonlStore")
    def test_json_promote_candidates_contains_correct_items(
        self, MockStore, capsys
    ):
        learnings = [
            _lrn(id="LRN-001", summary="learn alpha", status="pending", recurrence=3),
            _lrn(id="LRN-002", summary="learn beta", status="pending", recurrence=1),
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        ids = [c["id"] for c in data["promote_candidates"]]
        assert "LRN-001" in ids
        assert "LRN-002" not in ids

    @patch("learn.JsonlStore")
    def test_promote_ready_flag_no_candidates_prints_message(
        self, MockStore, capsys
    ):
        self._two_stores(MockStore, [], [])

        learn.cmd_review(self._args(promote_ready=True))

        out = capsys.readouterr().out
        assert "No learnings ready for promotion" in out

    @patch("learn.JsonlStore")
    def test_promote_ready_flag_with_candidates_prints_them(
        self, MockStore, capsys
    ):
        learnings = [
            _lrn(id="LRN-001", summary="important pattern", status="pending", recurrence=3),
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args(promote_ready=True))

        out = capsys.readouterr().out
        assert "LRN-001" in out
        assert "important pattern" in out

    @patch("learn.JsonlStore")
    def test_promote_ready_flag_excludes_already_promoted_items(
        self, MockStore, capsys
    ):
        learnings = [
            _lrn(id="LRN-001", summary="already done", status="promoted", recurrence=5),
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args(promote_ready=True))

        out = capsys.readouterr().out
        assert "No learnings ready for promotion" in out

    @patch("learn.JsonlStore")
    def test_plain_review_no_pending_prints_all_clear(self, MockStore, capsys):
        learnings = [_lrn(id="LRN-001", status="resolved")]
        errors = [_err(id="ERR-001", status="resolved")]
        self._two_stores(MockStore, learnings, errors)

        learn.cmd_review(self._args())

        out = capsys.readouterr().out
        assert "All clear" in out

    @patch("learn.JsonlStore")
    def test_plain_review_shows_pending_learnings(self, MockStore, capsys):
        learnings = [_lrn(id="LRN-001", summary="learn something", status="pending")]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args())

        out = capsys.readouterr().out
        assert "LRN-001" in out
        assert "learn something" in out

    @patch("learn.JsonlStore")
    def test_plain_review_shows_pending_errors(self, MockStore, capsys):
        errors = [_err(id="ERR-001", summary="something broke", status="pending")]
        self._two_stores(MockStore, [], errors)

        learn.cmd_review(self._args())

        out = capsys.readouterr().out
        assert "ERR-001" in out
        assert "something broke" in out

    @patch("learn.JsonlStore")
    def test_plain_review_items_with_recurrence_gte_threshold_get_promote_flag(
        self, MockStore, capsys
    ):
        learnings = [
            _lrn(id="LRN-001", summary="important", status="pending",
                 recurrence=learn.PROMOTION_THRESHOLD),
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args())

        out = capsys.readouterr().out
        assert "PROMOTE" in out

    @patch("learn.JsonlStore")
    def test_plain_review_items_below_threshold_no_promote_flag(
        self, MockStore, capsys
    ):
        learnings = [
            _lrn(id="LRN-001", summary="normal", status="pending", recurrence=1),
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_review(self._args())

        out = capsys.readouterr().out
        assert "PROMOTE" not in out


# ===========================================================================
# cmd_promote()
# ===========================================================================

class TestCmdPromote:
    def _args(self, entry_id, to="TOOLS.md"):
        return Namespace(entry_id=entry_id, to=to)

    @patch("learn.JsonlStore")
    def test_lrn_item_store_updated_with_promoted_status(self, MockStore, capsys):
        item = _lrn(id="LRN-001", summary="a learning", status="pending", action="do X")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_promote(self._args("LRN-001", to="TOOLS.md"))

        assert store.update.called
        updates = store.update.call_args[0][1]
        assert updates["status"] == "promoted"
        assert updates["promoted_to"] == "TOOLS.md"

    @patch("learn.JsonlStore")
    def test_err_item_uses_prevention_for_promotion_text(self, MockStore, capsys):
        item = _err(id="ERR-001", summary="dangerous cmd",
                    status="pending", prevention="never do that", fix="")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_promote(self._args("ERR-001", to="AGENTS.md"))

        out = capsys.readouterr().out
        assert "dangerous cmd" in out
        assert "never do that" in out

    @patch("learn.JsonlStore")
    def test_err_item_falls_back_to_fix_when_prevention_empty(
        self, MockStore, capsys
    ):
        item = _err(id="ERR-001", summary="dangerous cmd",
                    status="pending", prevention="", fix="use safe cmd")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_promote(self._args("ERR-001", to="AGENTS.md"))

        out = capsys.readouterr().out
        assert "use safe cmd" in out

    @patch("learn.JsonlStore")
    def test_lrn_item_uses_action_for_promotion_text(self, MockStore, capsys):
        item = _lrn(id="LRN-001", summary="good pattern",
                    status="pending", action="always do this", details="")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_promote(self._args("LRN-001", to="SOUL.md"))

        out = capsys.readouterr().out
        assert "good pattern" in out
        assert "always do this" in out

    @patch("learn.JsonlStore")
    def test_lrn_item_falls_back_to_details_when_action_empty(
        self, MockStore, capsys
    ):
        item = _lrn(id="LRN-001", summary="good pattern",
                    status="pending", action="", details="background context")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_promote(self._args("LRN-001", to="SOUL.md"))

        out = capsys.readouterr().out
        assert "background context" in out

    @patch("learn.JsonlStore")
    def test_already_promoted_prints_warning_no_update(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="promoted", promoted_to="SOUL.md")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        learn.cmd_promote(self._args("LRN-001", to="TOOLS.md"))

        assert not store.update.called
        out = capsys.readouterr().out
        assert "already promoted" in out

    @patch("learn.JsonlStore")
    def test_item_not_found_exits_with_error(self, MockStore, capsys):
        store = _make_store(find_result=None)
        MockStore.return_value = store

        with pytest.raises(SystemExit) as exc_info:
            learn.cmd_promote(self._args("LRN-999", to="TOOLS.md"))

        assert exc_info.value.code == 1

    @patch("learn.JsonlStore")
    def test_invalid_target_exits_with_error(self, MockStore, capsys):
        item = _lrn(id="LRN-001", status="pending")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        with pytest.raises(SystemExit) as exc_info:
            learn.cmd_promote(self._args("LRN-001", to="README.md"))

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Invalid target" in err

    @patch("learn.JsonlStore")
    def test_unknown_id_prefix_exits_with_error(self, MockStore, capsys):
        store = _make_store()
        MockStore.return_value = store

        with pytest.raises(SystemExit) as exc_info:
            learn.cmd_promote(self._args("XYZ-001", to="TOOLS.md"))

        assert exc_info.value.code == 1

    @pytest.mark.parametrize("target", [
        "AGENTS.md",
        "SOUL.md",
        "TOOLS.md",
        "MEMORY.md",
        "PROACTIVE.md",
        "HEARTBEAT.md",
        "SESSION-STATE.md",
    ])
    @patch("learn.JsonlStore")
    def test_all_valid_targets_are_accepted(self, MockStore, target, capsys):
        item = _lrn(id="LRN-001", status="pending", action="do it")
        store = _make_store(find_result=item)
        MockStore.return_value = store

        # Should not raise
        learn.cmd_promote(self._args("LRN-001", to=target))

        updates = store.update.call_args[0][1]
        assert updates["promoted_to"] == target


# ===========================================================================
# cmd_stats()
# ===========================================================================

class TestCmdStats:
    def _args(self, json_out=False):
        return Namespace(json=json_out)

    def _two_stores(self, MockStore, learnings, errors):
        lrn_store = _make_store(items=learnings)
        err_store = _make_store(items=errors)
        MockStore.side_effect = [lrn_store, err_store]

    @patch("learn.JsonlStore")
    def test_json_output_correct_structure(self, MockStore, capsys):
        learnings = [
            _lrn(id="LRN-001", status="pending"),
            _lrn(id="LRN-002", status="resolved"),
        ]
        errors = [_err(id="ERR-001", status="pending")]
        self._two_stores(MockStore, learnings, errors)

        learn.cmd_stats(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        assert data["learnings"]["total"] == 2
        assert data["errors"]["total"] == 1
        assert "by_status" in data["learnings"]
        assert "by_status" in data["errors"]
        assert "promote_ready" in data

    @patch("learn.JsonlStore")
    def test_json_by_status_counts_correctly(self, MockStore, capsys):
        learnings = [
            _lrn(id="LRN-001", status="pending"),
            _lrn(id="LRN-002", status="pending"),
            _lrn(id="LRN-003", status="resolved"),
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_stats(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        assert data["learnings"]["by_status"]["pending"] == 2
        assert data["learnings"]["by_status"]["resolved"] == 1

    @patch("learn.JsonlStore")
    def test_promote_ready_counts_only_non_promoted_with_recurrence_gte_threshold(
        self, MockStore, capsys
    ):
        learnings = [
            _lrn(id="LRN-001", status="pending", recurrence=3),    # counts
            _lrn(id="LRN-002", status="promoted", recurrence=5),   # excluded: promoted
            _lrn(id="LRN-003", status="pending", recurrence=2),    # excluded: below threshold
            _lrn(id="LRN-004", status="resolved", recurrence=4),   # counts (not promoted)
        ]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_stats(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        assert data["promote_ready"] == 2

    @patch("learn.JsonlStore")
    def test_empty_stores_produce_zero_counts(self, MockStore, capsys):
        self._two_stores(MockStore, [], [])

        learn.cmd_stats(self._args(json_out=True))

        data = json.loads(capsys.readouterr().out)
        assert data["learnings"]["total"] == 0
        assert data["errors"]["total"] == 0
        assert data["promote_ready"] == 0

    @patch("learn.JsonlStore")
    def test_plain_text_output_printed(self, MockStore, capsys):
        learnings = [_lrn(id="LRN-001", status="pending")]
        errors = [_err(id="ERR-001", status="resolved")]
        self._two_stores(MockStore, learnings, errors)

        learn.cmd_stats(self._args(json_out=False))

        out = capsys.readouterr().out
        assert "Stats" in out
        assert "Learnings" in out
        assert "Errors" in out

    @patch("learn.JsonlStore")
    def test_plain_text_shows_promote_ready_when_nonzero(self, MockStore, capsys):
        learnings = [_lrn(id="LRN-001", status="pending", recurrence=3)]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_stats(self._args(json_out=False))

        out = capsys.readouterr().out
        assert "promotion" in out.lower() or "PROMOTE" in out or "promote" in out.lower()

    @patch("learn.JsonlStore")
    def test_plain_text_does_not_show_promote_line_when_zero(
        self, MockStore, capsys
    ):
        learnings = [_lrn(id="LRN-001", status="pending", recurrence=1)]
        self._two_stores(MockStore, learnings, [])

        learn.cmd_stats(self._args(json_out=False))

        out = capsys.readouterr().out
        assert "ready for promotion" not in out
