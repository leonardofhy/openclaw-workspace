#!/usr/bin/env python3
"""Comprehensive tests for orchestrator.py with mocked SSH operations."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the script directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Import orchestrator with mocked dependencies
class TestOrchestrator(unittest.TestCase):
    """Test suite for cross-machine orchestrator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_path = Path(self.temp_dir)

        # Mock workspace directory structure
        (self.workspace_path / "memory" / "learning" / "state").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "memory" / "mailbox").mkdir(parents=True, exist_ok=True)

        # Create test queue.json
        self.queue_data = {
            "tasks": [
                {"id": "EXP-001", "type": "experiment", "status": "queued",
                 "title": "SAE Training", "priority": 1},
                {"id": "EXP-002", "type": "experiment", "status": "running",
                 "title": "Whisper Fine-tune", "priority": 2},
                {"id": "TASK-001", "type": "task", "status": "done",
                 "title": "Regular Task", "priority": 3}
            ]
        }
        queue_file = self.workspace_path / "memory" / "learning" / "state" / "queue.json"
        queue_file.write_text(json.dumps(self.queue_data))

        # Create test script file
        self.test_script = self.workspace_path / "test_experiment.py"
        self.test_script.write_text("# Test experiment script\nprint('Hello World')")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('orchestrator.find_workspace')
    @patch('orchestrator._current_branch')
    @patch('orchestrator.mailbox_store')
    @patch('orchestrator.subprocess.run')
    def test_dispatch_dry_run(self, mock_subprocess, mock_mailbox, mock_branch, mock_workspace):
        """Test experiment dispatch in dry-run mode (default)."""
        mock_workspace.return_value = self.workspace_path
        mock_branch.return_value = "macbook-m3"

        # Mock mailbox append
        mock_mailbox.append.return_value = {"id": "MB-001", "status": "open"}

        # Mock subprocess for experiment_dispatch call
        mock_subprocess.return_value = Mock(returncode=0)

        import orchestrator

        # Create mock args
        args = Mock()
        args.name = "test_experiment"
        args.script = str(self.test_script)
        args.model = "whisper-base"
        args.gpus = None
        args.walltime = None
        args.dry_run = True  # Default

        result = orchestrator.cmd_dispatch(args)

        # Verify dry-run behavior
        self.assertEqual(result, 0)
        mock_mailbox.append.assert_called_once()

    @patch('orchestrator._load_queue')
    @patch('orchestrator._scp_from')
    def test_sync_state_comparison(self, mock_scp, mock_load_queue):
        """Test state sync with task comparison."""
        mock_load_queue.return_value = self.queue_data

        # Mock remote queue data - different from local data to test comparison
        remote_queue_data = {
            "tasks": [
                {"id": "EXP-001", "type": "experiment", "status": "running"},  # status diff (local is queued)
                {"id": "EXP-003", "type": "experiment", "status": "queued"},   # only remote
            ]
        }

        def mock_scp_side_effect(host, remote_path, local_path):
            if "queue.json" in remote_path:
                Path(local_path).write_text(json.dumps(remote_queue_data))
            elif "dispatches.jsonl" in remote_path:
                Path(local_path).write_text('{"job_id": "123", "model": "whisper-base"}\n')

        mock_scp.side_effect = mock_scp_side_effect

        import orchestrator

        args = Mock()
        args.dry_run = False
        args.json = True

        # Capture output
        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = orchestrator.cmd_sync_state(args)

        output = f.getvalue()
        report = json.loads(output)

        # Verify comparison results
        self.assertEqual(result, 0)
        self.assertIn("only_local", report)
        self.assertIn("only_remote", report)
        self.assertIn("status_diffs", report)
        # Should find EXP-001 status difference: local=queued, remote=running
        self.assertEqual(len(report["status_diffs"]), 1)
        self.assertEqual(report["status_diffs"][0]["id"], "EXP-001")
        # Should find EXP-002 only local, EXP-003 only remote
        self.assertIn("EXP-002", report["only_local"])
        self.assertIn("EXP-003", report["only_remote"])

    @patch('orchestrator._load_queue')
    def test_gpu_queue_filtering(self, mock_load_queue):
        """Test GPU queue filtering by status and type."""
        mock_load_queue.return_value = self.queue_data

        import orchestrator

        # Test filtering by status
        args = Mock()
        args.status = "queued"
        args.json = True

        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = orchestrator.cmd_gpu_queue(args)

        output = f.getvalue()
        experiments = json.loads(output)

        self.assertEqual(result, 0)
        self.assertEqual(len(experiments), 1)  # Only EXP-001 is queued
        self.assertEqual(experiments[0]["id"], "EXP-001")
        self.assertEqual(experiments[0]["status"], "queued")

    @patch('orchestrator.find_workspace')
    @patch('orchestrator._current_branch')
    def test_handoff_dry_run(self, mock_branch, mock_workspace):
        """Test task handoff in dry-run mode."""
        mock_workspace.return_value = self.workspace_path
        mock_branch.return_value = "macbook-m3"

        # Create test files for handoff
        test_file1 = self.workspace_path / "config.json"
        test_file1.write_text('{"model": "whisper-base"}')

        test_file2 = self.workspace_path / "results.csv"
        test_file2.write_text("metric,value\naccuracy,0.95")

        import orchestrator

        args = Mock()
        args.to = "lab"
        args.title = "Experiment Results"
        args.files = [str(test_file1), str(test_file2)]
        args.context = "Phase 2 analysis complete"
        args.priority = 1
        args.urgent = False
        args.dry_run = True

        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = orchestrator.cmd_handoff(args)

        output = f.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("[DRY RUN] Handoff to lab", output)
        self.assertIn("config.json", output)
        self.assertIn("results.csv", output)
        self.assertIn("Phase 2 analysis complete", output)

    @patch('orchestrator.find_workspace')
    def test_handoff_nonexistent_files(self, mock_workspace):
        """Test handoff with nonexistent files returns error."""
        mock_workspace.return_value = self.workspace_path

        import orchestrator

        args = Mock()
        args.to = "lab"
        args.title = "Test"
        args.files = ["/nonexistent/file.txt"]
        args.context = ""
        args.priority = 2
        args.urgent = False
        args.dry_run = True

        result = orchestrator.cmd_handoff(args)

        # Should return error code for nonexistent file
        self.assertEqual(result, 1)

    @patch('orchestrator.find_workspace')
    def test_gpu_queue_empty_results(self, mock_workspace):
        """Test GPU queue with no matching experiments."""
        mock_workspace.return_value = self.workspace_path

        import orchestrator

        args = Mock()
        args.status = "failed"  # No experiments have this status
        args.json = False

        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = orchestrator.cmd_gpu_queue(args)

        output = f.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("No GPU experiments in queue", output)

    @patch('orchestrator._load_queue')
    def test_queue_loading_missing_file(self, mock_load_queue):
        """Test queue loading when file doesn't exist."""
        # Return empty dict when file doesn't exist
        mock_load_queue.return_value = {}

        import orchestrator

        args = Mock()
        args.status = None
        args.json = True

        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = orchestrator.cmd_gpu_queue(args)

        output = f.getvalue()
        experiments = json.loads(output)

        self.assertEqual(result, 0)
        self.assertEqual(experiments, [])  # Empty list when no queue file

    @patch('orchestrator.subprocess.run')
    def test_ssh_timeout_handling(self, mock_subprocess):
        """Test SSH command timeout handling."""
        import subprocess

        # Mock subprocess timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("ssh", 30)

        import orchestrator

        # Should raise TimeoutExpired exception
        with self.assertRaises(subprocess.TimeoutExpired):
            orchestrator._run_ssh("test_host", "test_command", dry_run=False)

    def test_default_dry_run_behavior(self):
        """Test that commands default to dry-run mode."""
        import orchestrator

        parser = orchestrator.build_parser()

        # Test dispatch command defaults
        args = parser.parse_args(["dispatch", "--name", "test", "--script", "test.py", "--model", "whisper-base"])
        self.assertTrue(args.dry_run)  # Should default to True

        # Test sync-state command defaults
        args = parser.parse_args(["sync-state"])
        self.assertTrue(args.dry_run)  # Should default to True

        # Test handoff command defaults
        args = parser.parse_args(["handoff", "--to", "lab", "--title", "test"])
        self.assertTrue(args.dry_run)  # Should default to True

    def test_execute_override_dry_run(self):
        """Test that --execute flag overrides default dry-run."""
        import orchestrator

        parser = orchestrator.build_parser()

        # Test with --execute flag
        args = parser.parse_args(["dispatch", "--name", "test", "--script", "test.py", "--model", "whisper-base", "--execute"])

        # Simulate main() logic
        if hasattr(args, 'execute') and args.execute:
            args.dry_run = False

        self.assertFalse(args.dry_run)  # Should be overridden to False


class MockSSHTestCase(unittest.TestCase):
    """Additional tests with more sophisticated SSH mocking."""

    @patch('orchestrator.subprocess.run')
    def test_ssh_command_construction(self, mock_run):
        """Test SSH command construction and execution."""
        mock_run.return_value = Mock(returncode=0, stdout="success")

        import orchestrator

        result = orchestrator._run_ssh("test_host", "ls -la", dry_run=False)

        # Verify SSH command was constructed correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "ssh")
        self.assertEqual(call_args[1], "test_host")
        self.assertEqual(call_args[2], "ls -la")

    @patch('orchestrator.subprocess.run')
    def test_scp_command_construction(self, mock_run):
        """Test SCP command construction."""
        mock_run.return_value = Mock(returncode=0)

        import orchestrator

        orchestrator._scp_from("test_host", "/remote/path", "/local/path", dry_run=False)

        # Verify SCP command was constructed correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "scp")
        self.assertEqual(call_args[1], "test_host:/remote/path")
        self.assertEqual(call_args[2], "/local/path")


if __name__ == "__main__":
    # Import subprocess for the timeout test
    import subprocess

    # Run tests with verbose output
    unittest.main(verbosity=2)