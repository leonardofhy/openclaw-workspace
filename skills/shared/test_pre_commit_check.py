#!/usr/bin/env python3
"""Tests for skills/shared/pre_commit_check.py

Covers:
- Secret detection (catches real secrets, ignores env lookups)
- Merge conflict marker detection
- Clean files pass all checks
- is_env_file / is_shared_lib helpers
- CheckResult class

Usage:
    python3 -m pytest skills/shared/test_pre_commit_check.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pre_commit_check as pcc


class TestCheckResult(unittest.TestCase):

    def test_ok_when_no_errors(self):
        r = pcc.CheckResult()
        self.assertTrue(r.ok)

    def test_not_ok_when_error(self):
        r = pcc.CheckResult()
        r.error("bad thing")
        self.assertFalse(r.ok)

    def test_ok_with_only_warnings(self):
        r = pcc.CheckResult()
        r.warn("minor thing")
        self.assertTrue(r.ok)

    def test_errors_list(self):
        r = pcc.CheckResult()
        r.error("e1")
        r.error("e2")
        self.assertEqual(len(r.errors), 2)


class TestIsEnvFile(unittest.TestCase):

    def test_env_file(self):
        self.assertTrue(pcc.is_env_file(".env"))

    def test_env_local(self):
        self.assertTrue(pcc.is_env_file(".env.local"))

    def test_secrets_dir(self):
        self.assertTrue(pcc.is_env_file("secrets/api.json"))

    def test_normal_file(self):
        self.assertFalse(pcc.is_env_file("src/main.py"))


class TestIsSharedLib(unittest.TestCase):

    def test_shared_lib(self):
        self.assertTrue(pcc.is_shared_lib("skills/shared/utils.py"))

    def test_test_file_excluded(self):
        self.assertFalse(pcc.is_shared_lib("skills/shared/test_utils.py"))

    def test_non_python(self):
        self.assertFalse(pcc.is_shared_lib("skills/shared/readme.md"))

    def test_outside_shared_dirs(self):
        self.assertFalse(pcc.is_shared_lib("skills/leo-diary/scripts/foo.py"))


class TestCheckSecrets(unittest.TestCase):
    """check_secrets() should catch hardcoded secrets but ignore env lookups."""

    def _check(self, content: str, filename: str = "code.py") -> pcc.CheckResult:
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, filename)
            with open(fpath, "w") as f:
                f.write(content)
            result = pcc.CheckResult()
            pcc.check_secrets([filename], td, result)
            return result

    def test_catches_api_key_assignment(self):
        r = self._check('api_key = "sk-12345678abcdef"\n')
        self.assertFalse(r.ok)
        self.assertTrue(any("api_key" in e for e in r.errors))

    def test_catches_password_assignment(self):
        r = self._check('password = "supersecret"\n')
        self.assertFalse(r.ok)

    def test_catches_secret_assignment(self):
        r = self._check('secret = "my_secret_value"\n')
        self.assertFalse(r.ok)

    def test_catches_bearer_token(self):
        r = self._check('auth = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"\n')
        self.assertFalse(r.ok)

    def test_ignores_env_lookup(self):
        r = self._check('api_key = os.environ.get("API_KEY")\n')
        self.assertTrue(r.ok)

    def test_ignores_getenv(self):
        r = self._check('password = os.getenv("PASSWORD")\n')
        self.assertTrue(r.ok)

    def test_clean_file_passes(self):
        r = self._check('x = 42\nname = "hello"\n')
        self.assertTrue(r.ok)

    def test_skips_test_files(self):
        r = self._check('api_key = "fake_test_key_12345"\n', filename="test_foo.py")
        self.assertTrue(r.ok)

    def test_skips_non_py_non_md(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "data.csv")
            with open(fpath, "w") as f:
                f.write('api_key = "sk-12345678abcdef"\n')
            result = pcc.CheckResult()
            pcc.check_secrets(["data.csv"], td, result)
            self.assertTrue(result.ok)


class TestCheckMergeConflicts(unittest.TestCase):

    def _check(self, content: str) -> pcc.CheckResult:
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "file.py")
            with open(fpath, "w") as f:
                f.write(content)
            result = pcc.CheckResult()
            pcc.check_merge_conflicts(["file.py"], td, result)
            return result

    def test_catches_left_marker(self):
        r = self._check("<<<<<<< HEAD\nsome code\n")
        self.assertFalse(r.ok)

    def test_catches_right_marker(self):
        r = self._check(">>>>>>> branch\nsome code\n")
        self.assertFalse(r.ok)

    def test_catches_separator(self):
        r = self._check("======= \nsome code\n")
        self.assertFalse(r.ok)

    def test_clean_file_passes(self):
        r = self._check("def hello():\n    return 42\n")
        self.assertTrue(r.ok)


class TestCheckLineLength(unittest.TestCase):

    def _check(self, content: str) -> pcc.CheckResult:
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "file.py")
            with open(fpath, "w") as f:
                f.write(content)
            result = pcc.CheckResult()
            pcc.check_line_length(["file.py"], td, result)
            return result

    def test_short_lines_pass(self):
        r = self._check("x = 1\ny = 2\n")
        self.assertEqual(len(r.warnings), 0)

    def test_long_line_warns(self):
        r = self._check("x = " + "a" * 120 + "\n")
        self.assertEqual(len(r.warnings), 1)
        self.assertIn("[LENGTH]", r.warnings[0])


class TestCheckSyntax(unittest.TestCase):

    def _check(self, content: str) -> pcc.CheckResult:
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "file.py")
            with open(fpath, "w") as f:
                f.write(content)
            result = pcc.CheckResult()
            pcc.check_syntax(["file.py"], td, result)
            return result

    def test_valid_syntax_passes(self):
        r = self._check("x = 1\n")
        self.assertTrue(r.ok)

    def test_invalid_syntax_fails(self):
        r = self._check("def f(\n")
        self.assertFalse(r.ok)
        self.assertTrue(any("[SYNTAX]" in e for e in r.errors))


class TestFixTrailingWhitespace(unittest.TestCase):

    def test_fixes_trailing_spaces(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "file.py")
            with open(fpath, "w") as f:
                f.write("hello   \nworld  \n")
            count = pcc.fix_trailing_whitespace(["file.py"], td)
            self.assertEqual(count, 1)
            content = open(fpath).read()
            self.assertEqual(content, "hello\nworld\n")

    def test_no_fix_needed(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "file.py")
            with open(fpath, "w") as f:
                f.write("clean\nfile\n")
            count = pcc.fix_trailing_whitespace(["file.py"], td)
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
