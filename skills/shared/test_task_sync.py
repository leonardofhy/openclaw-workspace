#!/usr/bin/env python3
"""Unit tests for skills/shared/task_sync.py

Covers:
- create_task (with and without label_id)
- do_pull (mock Todoist API responses)
- do_push (mock task-board.md content)
- Edge cases: empty board, malformed entries
- parse_task_board

Usage:
    python3 -m pytest skills/shared/test_task_sync.py -v
"""

import json
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Make the module importable regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_sync


# ── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_BOARD = textwrap.dedent("""\
    # Task Board

    ## ACTIVE

    ### M-02 | Build experiment pipeline
    - **owner**: Leo
    - **priority**: P1
    - **created**: 2026-03-01
    - **last_touched**: 2026-03-15
    - **progress**: Step 1 done
    - **next_action**: Wire up eval harness

    ### L-08 | Read diffusion paper
    - **owner**: Leo
    - **priority**: P2
    - **created**: 2026-03-10
    - **last_touched**: 2026-03-14
    - **progress**:
    - **next_action**: Summarize key results

    ## DONE

    ### S-01 | Setup repo
    - **owner**: Leo
    - **priority**: P0
    - **created**: 2026-02-01
    - **last_touched**: 2026-02-15
    - **progress**: Complete
""")


@pytest.fixture
def board_file(tmp_path):
    p = tmp_path / "task-board.md"
    p.write_text(SAMPLE_BOARD)
    return p


@pytest.fixture
def empty_board(tmp_path):
    p = tmp_path / "task-board.md"
    p.write_text("# Task Board\n\n## ACTIVE\n\n## DONE\n")
    return p


# ── parse_task_board ──────────────────────────────────────────────────────

class TestParseTaskBoard:
    def test_parses_all_tasks(self, board_file):
        tasks, raw = task_sync.parse_task_board(board_file)
        ids = [t['id'] for t in tasks]
        assert 'M-02' in ids
        assert 'L-08' in ids
        assert 'S-01' in ids
        assert len(tasks) == 3

    def test_task_fields(self, board_file):
        tasks, _ = task_sync.parse_task_board(board_file)
        m02 = next(t for t in tasks if t['id'] == 'M-02')
        assert m02['title'] == 'Build experiment pipeline'
        assert m02['status'] == 'ACTIVE'
        assert m02['priority'] == 'P1'
        assert m02['next_action'] == 'Wire up eval harness'

    def test_empty_board(self, empty_board):
        tasks, _ = task_sync.parse_task_board(empty_board)
        assert tasks == []

    def test_merge_conflict_raises(self, tmp_path):
        p = tmp_path / "task-board.md"
        p.write_text("# Board\n<<<<<<< HEAD\nstuff\n=======\nother\n>>>>>>> branch\n")
        with pytest.raises(ValueError, match="merge conflict"):
            task_sync.parse_task_board(p)

    def test_malformed_entry_skipped(self, tmp_path):
        """A ### line that doesn't match the ID pattern is silently skipped."""
        p = tmp_path / "task-board.md"
        p.write_text("# Board\n\n## ACTIVE\n\n### Not a valid task header\n- some text\n")
        tasks, _ = task_sync.parse_task_board(p)
        assert tasks == []


# ── create_task ───────────────────────────────────────────────────────────

class TestCreateTask:
    def test_dry_run_returns_none(self):
        result = task_sync.create_task("Do thing", "TB_M-02", None, 3, "fake-token", dry_run=True)
        assert result is None

    @patch.object(task_sync, 'api_post')
    def test_without_label_id(self, mock_post):
        mock_post.return_value = {'id': '123', 'content': 'Do thing'}
        result = task_sync.create_task("Do thing", "TB_M-02", None, 3, "tok", dry_run=False)

        mock_post.assert_called_once()
        payload = mock_post.call_args[0][2]
        assert payload['labels'] == ['TB_M-02']
        assert 'label_ids' not in payload
        assert result['id'] == '123'

    @patch.object(task_sync, 'api_post')
    def test_with_label_id(self, mock_post):
        mock_post.return_value = {'id': '456', 'content': 'Do thing'}
        result = task_sync.create_task("Do thing", "TB_M-02", "lbl-99", 3, "tok", dry_run=False)

        payload = mock_post.call_args[0][2]
        assert payload['labels'] == ['TB_M-02']
        assert payload['label_ids'] == ['lbl-99']
        assert result['id'] == '456'


# ── do_push ───────────────────────────────────────────────────────────────

class TestDoPush:
    @patch.object(task_sync, 'create_task', return_value={'id': 't1'})
    @patch.object(task_sync, 'get_tasks_by_label', return_value=[])
    @patch.object(task_sync, 'get_all_labels', return_value={})
    def test_push_creates_new_task(self, mock_labels, mock_get, mock_create):
        tasks = [{'id': 'M-02', 'status': 'ACTIVE', 'next_action': 'Wire up eval', 'priority': 'P1'}]
        log = task_sync.do_push(tasks, 'tok', dry_run=False)
        assert len(log) == 1
        assert log[0]['action'] == 'created'
        mock_create.assert_called_once()

    @patch.object(task_sync, 'get_tasks_by_label', return_value=[{'id': 'x', 'content': 'Wire up eval'}])
    @patch.object(task_sync, 'get_all_labels', return_value={})
    def test_push_skips_already_synced(self, mock_labels, mock_get):
        tasks = [{'id': 'M-02', 'status': 'ACTIVE', 'next_action': 'Wire up eval', 'priority': 'P1'}]
        log = task_sync.do_push(tasks, 'tok', dry_run=False)
        assert log[0]['action'] == 'skipped'

    @patch.object(task_sync, 'get_all_labels', return_value={})
    def test_push_skips_no_next_action(self, mock_labels):
        tasks = [{'id': 'M-02', 'status': 'ACTIVE', 'next_action': '', 'priority': 'P1'}]
        log = task_sync.do_push(tasks, 'tok', dry_run=False)
        assert log == []

    @patch.object(task_sync, 'get_all_labels', return_value={})
    def test_push_ignores_non_active(self, mock_labels):
        tasks = [{'id': 'S-01', 'status': 'DONE', 'next_action': 'Something', 'priority': 'P0'}]
        log = task_sync.do_push(tasks, 'tok', dry_run=False)
        assert log == []

    @patch.object(task_sync, 'get_all_labels', return_value={})
    def test_push_empty_board(self, mock_labels):
        log = task_sync.do_push([], 'tok', dry_run=False)
        assert log == []


# ── do_pull ───────────────────────────────────────────────────────────────

class TestDoPull:
    @patch.object(task_sync, 'get_completed_tasks')
    def test_pull_updates_board(self, mock_completed, board_file):
        mock_completed.return_value = [
            {'content': 'Wire up eval harness', 'labels': ['TB_M-02'],
             'completed_at': '2026-03-18T10:00:00Z'},
        ]
        tasks, _ = task_sync.parse_task_board(board_file)
        with patch.object(task_sync, 'TASK_BOARD', board_file):
            log = task_sync.do_pull(tasks, 'tok', dry_run=False)

        assert len(log) == 1
        assert log[0]['task_id'] == 'M-02'
        assert log[0]['action'] == 'pulled'

        # Verify board was updated
        updated_tasks, _ = task_sync.parse_task_board(board_file)
        m02 = next(t for t in updated_tasks if t['id'] == 'M-02')
        assert '2026-03-18' in m02.get('last_touched', '')
        assert 'Wire up eval harness' in m02.get('progress', '')

    @patch.object(task_sync, 'get_completed_tasks', return_value=[])
    def test_pull_no_completed(self, mock_completed, board_file):
        tasks, _ = task_sync.parse_task_board(board_file)
        with patch.object(task_sync, 'TASK_BOARD', board_file):
            log = task_sync.do_pull(tasks, 'tok', dry_run=False)
        assert log == []

    @patch.object(task_sync, 'get_completed_tasks')
    def test_pull_unknown_task_id(self, mock_completed, board_file):
        mock_completed.return_value = [
            {'content': 'Mystery task', 'labels': ['TB_Z-99'], 'completed_at': '2026-03-18'},
        ]
        tasks, _ = task_sync.parse_task_board(board_file)
        with patch.object(task_sync, 'TASK_BOARD', board_file):
            log = task_sync.do_pull(tasks, 'tok', dry_run=False)
        assert log == []

    @patch.object(task_sync, 'get_completed_tasks')
    def test_pull_dry_run(self, mock_completed, board_file):
        mock_completed.return_value = [
            {'content': 'Wire up eval harness', 'labels': ['TB_M-02'],
             'completed_at': '2026-03-18T10:00:00Z'},
        ]
        tasks, _ = task_sync.parse_task_board(board_file)
        original_text = board_file.read_text()
        with patch.object(task_sync, 'TASK_BOARD', board_file):
            log = task_sync.do_pull(tasks, 'tok', dry_run=True)
        # Board should not be modified in dry-run
        assert board_file.read_text() == original_text


# ── Edge cases ────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_update_task_board_field_inserts_missing_field(self, board_file):
        tasks, _ = task_sync.parse_task_board(board_file)
        m02 = next(t for t in tasks if t['id'] == 'M-02')
        task_sync.update_task_board_field(board_file, m02, 'new_field', 'new_value', dry_run=False)
        updated_tasks, _ = task_sync.parse_task_board(board_file)
        m02_updated = next(t for t in updated_tasks if t['id'] == 'M-02')
        assert m02_updated.get('new_field') == 'new_value'

    def test_update_task_board_field_no_change(self, board_file):
        tasks, _ = task_sync.parse_task_board(board_file)
        m02 = next(t for t in tasks if t['id'] == 'M-02')
        original = board_file.read_text()
        task_sync.update_task_board_field(board_file, m02, 'priority', 'P1', dry_run=False)
        assert board_file.read_text() == original  # no-op

    def test_append_progress_deduplicates(self, board_file):
        tasks, _ = task_sync.parse_task_board(board_file)
        m02 = next(t for t in tasks if t['id'] == 'M-02')
        task_sync.append_progress(board_file, m02, 'Step 1 done', dry_run=False)
        # "Step 1 done" is already in progress, so board should not change
        updated_tasks, _ = task_sync.parse_task_board(board_file)
        m02u = next(t for t in updated_tasks if t['id'] == 'M-02')
        assert m02u['progress'] == 'Step 1 done'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
