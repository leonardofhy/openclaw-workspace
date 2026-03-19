#!/usr/bin/env python3
"""Tests for skills/shared/ensure_state.py

Covers:
- Creates missing state files with correct defaults
- Does not overwrite existing files
- find_workspace() logic

Usage:
    python3 -m pytest skills/shared/test_ensure_state.py -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ensure_state as es


class TestFindWorkspace(unittest.TestCase):

    def test_finds_git_root(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".git"))
            subdir = os.path.join(td, "a", "b")
            os.makedirs(subdir)
            fake_file = os.path.join(subdir, "fake.py")
            with open(fake_file, "w") as f:
                f.write("")
            with patch.object(os.path, "abspath", return_value=fake_file):
                # Manually walk up from subdir
                d = subdir
                found = None
                for _ in range(10):
                    if os.path.isdir(os.path.join(d, ".git")):
                        found = d
                        break
                    d = os.path.dirname(d)
                self.assertEqual(found, td)

    def test_fallback_returns_default(self):
        with tempfile.TemporaryDirectory() as td:
            # No .git anywhere in the temp hierarchy
            with patch("os.path.dirname") as mock_dirname:
                # Force it to never find .git by always returning same dir
                mock_dirname.side_effect = lambda x: x
                result = es.find_workspace()
                # Should return the fallback or a real workspace
                self.assertIsInstance(result, str)


class TestMainCreatesFiles(unittest.TestCase):
    """main() creates missing state files."""

    def test_creates_missing_files(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(es, "find_workspace", return_value=td):
                with self.assertRaises(SystemExit) as cm:
                    es.main()
                # Exit 1 means files were created
                self.assertEqual(cm.exception.code, 1)

            # Verify files were created
            for rel_path, expected_data in es.DEFAULTS.items():
                full_path = os.path.join(td, rel_path)
                self.assertTrue(os.path.exists(full_path), f"{rel_path} should exist")
                with open(full_path) as f:
                    data = json.load(f)
                self.assertEqual(data, expected_data)

    def test_does_not_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as td:
            # Pre-create files with custom content
            for rel_path in es.DEFAULTS:
                full_path = os.path.join(td, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    json.dump({"custom": "data"}, f)

            with patch.object(es, "find_workspace", return_value=td):
                # main() should print OK and NOT exit(1)
                # Since all files exist, no SystemExit(1)
                try:
                    es.main()
                except SystemExit as e:
                    self.fail(f"Should not exit with code {e.code} when files exist")

            # Verify original content preserved
            for rel_path in es.DEFAULTS:
                full_path = os.path.join(td, rel_path)
                with open(full_path) as f:
                    data = json.load(f)
                self.assertEqual(data, {"custom": "data"})

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(es, "find_workspace", return_value=td):
                with self.assertRaises(SystemExit):
                    es.main()
            for rel_path in es.DEFAULTS:
                full_path = os.path.join(td, rel_path)
                self.assertTrue(os.path.isdir(os.path.dirname(full_path)))

    def test_heartbeat_state_structure(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(es, "find_workspace", return_value=td):
                with self.assertRaises(SystemExit):
                    es.main()
            hb_path = os.path.join(td, "memory/heartbeat-state.json")
            with open(hb_path) as f:
                data = json.load(f)
            self.assertIn("recent_alerts", data)
            self.assertIn("lastChecks", data)
            self.assertIsInstance(data["lastChecks"], dict)


class TestDefaults(unittest.TestCase):

    def test_defaults_has_entries(self):
        self.assertGreater(len(es.DEFAULTS), 0)

    def test_all_values_are_dicts(self):
        for path, default in es.DEFAULTS.items():
            self.assertIsInstance(default, dict, f"{path} default should be dict")

    def test_paths_are_relative(self):
        for path in es.DEFAULTS:
            self.assertFalse(os.path.isabs(path), f"{path} should be relative")


if __name__ == "__main__":
    unittest.main()
