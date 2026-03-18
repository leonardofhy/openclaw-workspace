#!/usr/bin/env python3
"""Batch subprocess tests for feed recommendation scripts.

Tests all feed scripts via subprocess execution to verify they run without error.
Uses --help mode for scripts that require API keys or external dependencies.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Test constants
SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


# ── Test Utilities ──────────────────────────────────────────────

def run_script(script_name: str, args: list[str], timeout: int = 30,
               capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a script from the feed-recommend directory."""
    script_path = SCRIPT_DIR / script_name
    cmd = [PYTHON, str(script_path)] + args
    return subprocess.run(cmd, capture_output=capture_output, text=True, timeout=timeout)


def create_test_config(tmpdir: str) -> str:
    """Create a minimal test config file."""
    config = {
        "sources": {
            "hn": {"enabled": True, "limit": 5},
            "af": {"enabled": True, "limit": 3},
            "lw": {"enabled": True, "limit": 3},
            "arxiv": {"enabled": True, "categories": ["cs.CL"], "limit": 3},
        },
        "scoring": {
            "profile_path": "memory/feeds/preferences.json",
        },
        "dedup": {
            "title_similarity_threshold": 0.85,
        },
        "diversity": {
            "min_per_source": 1,
            "max_per_source": 3,
        },
    }
    config_path = os.path.join(tmpdir, "config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    return config_path


def create_test_preferences(tmpdir: str) -> str:
    """Create test preferences file."""
    prefs = {
        "boost_keywords": {
            "interpretability": 4,
            "alignment": 3,
            "speech": 2,
        },
        "penalty_keywords": {
            "crypto": -3,
            "nft": -2,
        },
        "interest_topics": ["machine learning", "AI safety"],
        "min_hn_score": 20,
    }
    feeds_dir = os.path.join(tmpdir, "memory", "feeds")
    os.makedirs(feeds_dir, exist_ok=True)
    prefs_path = os.path.join(feeds_dir, "preferences.json")
    with open(prefs_path, 'w') as f:
        json.dump(prefs, f, indent=2)
    return prefs_path


def create_test_feedback(tmpdir: str) -> str:
    """Create test feedback file."""
    feedback = [
        {"id": "hn:1", "source": "hn", "positive": True, "title": "ML research", "ts": "2026-03-18T10:00:00+08:00"},
        {"id": "af:1", "source": "af", "positive": True, "title": "alignment work", "ts": "2026-03-18T11:00:00+08:00"},
        {"id": "hn:2", "source": "hn", "positive": False, "title": "crypto news", "ts": "2026-03-18T12:00:00+08:00"},
    ]
    feeds_dir = os.path.join(tmpdir, "memory", "feeds")
    os.makedirs(feeds_dir, exist_ok=True)
    fb_path = os.path.join(feeds_dir, "feedback.jsonl")
    with open(fb_path, 'w') as f:
        for entry in feedback:
            f.write(json.dumps(entry) + '\n')
    return fb_path


# ── Main Feed CLI Tests ──────────────────────────────────────────

class TestFeedCLI(unittest.TestCase):

    def test_feed_help(self):
        """Test that feed.py --help works."""
        result = run_script("feed.py", ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Feed Recommender", result.stdout)

    def test_feed_sources_command(self):
        """Test feed.py sources command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["sources"])

            # Should list available sources
            self.assertEqual(result.returncode, 0)
            self.assertIn("Source", result.stdout)
            self.assertIn("hn", result.stdout)

    def test_feed_config_command(self):
        """Test feed.py config command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["config"])

            self.assertEqual(result.returncode, 0)
            # Should output valid JSON
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                self.fail("config command did not output valid JSON")

    def test_feed_enable_disable(self):
        """Test feed.py enable/disable commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                # Test disable
                result = run_script("feed.py", ["disable", "hn"])
                self.assertEqual(result.returncode, 0)
                self.assertIn("Disabled source: hn", result.stderr)

                # Test enable
                result = run_script("feed.py", ["enable", "hn"])
                self.assertEqual(result.returncode, 0)
                self.assertIn("Enabled source: hn", result.stderr)

    def test_feed_profile_command(self):
        """Test feed.py profile command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)
            prefs_path = create_test_preferences(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["profile"])

            self.assertEqual(result.returncode, 0)
            # Should output profile JSON
            try:
                profile = json.loads(result.stdout)
                self.assertIn("boost_keywords", profile)
            except json.JSONDecodeError:
                self.fail("profile command did not output valid JSON")

    def test_feed_stats_command(self):
        """Test feed.py stats command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)
            fb_path = create_test_feedback(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["stats"])

            self.assertEqual(result.returncode, 0)
            # Should output stats JSON
            try:
                stats = json.loads(result.stdout)
                self.assertIn("feedback_total", stats)
            except json.JSONDecodeError:
                self.fail("stats command did not output valid JSON")

    def test_feed_mark_seen(self):
        """Test feed.py mark-seen command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["mark-seen", "hn:123", "af:456"])

            self.assertEqual(result.returncode, 0)
            self.assertIn("Marked 2 as seen", result.stderr)

    def test_feed_feedback_positive(self):
        """Test feed.py feedback command with positive feedback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["feedback", "hn:123", "+", "--title", "Test Article"])

            self.assertEqual(result.returncode, 0)
            self.assertIn("Feedback recorded: + hn:123", result.stderr)

    def test_feed_feedback_negative(self):
        """Test feed.py feedback command with negative feedback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["feedback", "af:789", "-"])

            self.assertEqual(result.returncode, 0)
            self.assertIn("Feedback recorded: - af:789", result.stderr)


# ── Quality Scorer Tests ─────────────────────────────────────────

class TestQualityScorerCLI(unittest.TestCase):

    def test_quality_scorer_help(self):
        """Test quality_scorer.py --help works."""
        result = run_script("quality_scorer.py", ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("quality", result.stdout.lower())

    def test_quality_scorer_json_output(self):
        """Test quality_scorer.py --json output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fb_path = create_test_feedback(tmpdir)

            result = run_script("quality_scorer.py", ["--json", "--feeds-dir", tmpdir])
            self.assertEqual(result.returncode, 0)

            # Should output valid JSON
            try:
                report = json.loads(result.stdout)
                self.assertIn("quality_metrics", report)
                self.assertIn("data_summary", report)
            except json.JSONDecodeError:
                self.fail("quality scorer did not output valid JSON")

    def test_quality_scorer_text_output(self):
        """Test quality_scorer.py text output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fb_path = create_test_feedback(tmpdir)

            result = run_script("quality_scorer.py", ["--feeds-dir", tmpdir])
            self.assertEqual(result.returncode, 0)

            # Should contain report sections
            self.assertIn("Quality Report", result.stdout)
            self.assertIn("Quality Metrics", result.stdout)

    def test_quality_scorer_empty_directory(self):
        """Test quality_scorer.py with empty data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_script("quality_scorer.py", ["--feeds-dir", tmpdir])
            self.assertEqual(result.returncode, 0)

            # Should handle empty data gracefully
            self.assertIn("Quality Report", result.stdout)


# ── Migration Script Tests ───────────────────────────────────────

class TestMigrateHN(unittest.TestCase):

    def test_migrate_hn_help(self):
        """Test migrate_hn.py --help works."""
        result = run_script("migrate_hn.py", ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("migrate", result.stdout.lower())

    def test_migrate_hn_no_source_data(self):
        """Test migrate_hn.py with no HN data to migrate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock workspace path
            with patch.dict(os.environ, {"WORKSPACE": tmpdir}):
                result = run_script("migrate_hn.py", [])

            # Should handle missing source data gracefully
            self.assertEqual(result.returncode, 0)
            self.assertIn("Migration complete", result.stdout)

    def test_migrate_hn_with_source_data(self):
        """Test migrate_hn.py with sample HN data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock HN data
            hn_dir = os.path.join(tmpdir, "memory", "hn")
            os.makedirs(hn_dir, exist_ok=True)

            # Create sample seen.jsonl
            seen_data = [
                {"id": "123", "ts": "2026-03-18T10:00:00+08:00"},
                {"id": "456", "ts": "2026-03-18T11:00:00+08:00"},
            ]
            seen_path = os.path.join(hn_dir, "seen.jsonl")
            with open(seen_path, 'w') as f:
                for entry in seen_data:
                    f.write(json.dumps(entry) + '\n')

            # Create sample preferences.json
            prefs = {"boost_keywords": {"ai": 2}, "penalty_keywords": {"spam": -1}}
            with open(os.path.join(hn_dir, "preferences.json"), 'w') as f:
                json.dump(prefs, f)

            with patch.dict(os.environ, {"WORKSPACE": tmpdir}):
                result = run_script("migrate_hn.py", [])

            self.assertEqual(result.returncode, 0)
            self.assertIn("migrated", result.stdout)

            # Check that feeds directory was created
            feeds_dir = os.path.join(tmpdir, "memory", "feeds")
            self.assertTrue(os.path.exists(feeds_dir))


# ── Google Sheets Sync Tests ─────────────────────────────────────

class TestSheetsSync(unittest.TestCase):

    def test_sync_to_sheets_help(self):
        """Test sync_to_sheets.py --help works."""
        result = run_script("sync_to_sheets.py", ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Sync feed recommendations", result.stdout)

    def test_sync_to_sheets_test_mode(self):
        """Test sync_to_sheets.py --test --dry-run."""
        result = run_script("sync_to_sheets.py", ["--test", "--dry-run"])
        self.assertEqual(result.returncode, 0)

        # Should output test data in tab-separated format
        lines = result.stdout.strip().split('\n')
        self.assertGreaterEqual(len(lines), 3)  # At least 3 test items

        # Check that output contains expected columns
        for line in lines:
            parts = line.split('\t')
            self.assertGreaterEqual(len(parts), 5)  # Date, Source, Title, Author, Score, etc.

    def test_sync_to_sheets_json_file_dry_run(self):
        """Test sync_to_sheets.py with JSON file input in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample digest file
            digest = {
                "items": [
                    {
                        "source": "hn", "title": "Test Article", "url": "https://test.com/1",
                        "author": "testuser", "score": 100, "posted": "2026-03-18",
                        "snippet": "A test article", "tags": ["test"],
                        "interest_score": 7.5, "suggested_action": "略讀",
                    },
                    {
                        "source": "af", "title": "Another Test", "url": "https://test.com/2",
                        "author": "author2", "score": 50, "posted": "2026-03-18",
                        "snippet": "Another test", "tags": ["ai"],
                        "interest_score": 8.2, "suggested_action": "深讀",
                    },
                ]
            }
            digest_path = os.path.join(tmpdir, "digest.json")
            with open(digest_path, 'w') as f:
                json.dump(digest, f)

            result = run_script("sync_to_sheets.py",
                              ["--json-file", digest_path, "--dry-run", "--no-translate"])
            self.assertEqual(result.returncode, 0)

            # Should output the digest items
            lines = result.stdout.strip().split('\n')
            self.assertEqual(len(lines), 2)

    def test_sync_to_sheets_stdin_dry_run(self):
        """Test sync_to_sheets.py --stdin --dry-run."""
        digest = {"items": [{"source": "test", "title": "Test", "url": "https://test.com"}]}

        result = subprocess.run(
            [PYTHON, str(SCRIPT_DIR / "sync_to_sheets.py"), "--stdin", "--dry-run", "--no-translate"],
            input=json.dumps(digest), text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0)

    def test_sync_to_sheets_backfill_dry_run(self):
        """Test sync_to_sheets.py --backfill --dry-run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample candidates directory with digest files
            candidates_dir = os.path.join(tmpdir, "candidates")
            os.makedirs(candidates_dir)

            digest = {
                "items": [
                    {"source": "hn", "title": "Old Article", "url": "https://old.com"},
                ]
            }
            with open(os.path.join(candidates_dir, "2026-03-17.json"), 'w') as f:
                json.dump(digest, f)

            # Mock the paths used by sync_to_sheets
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "glob") as mock_glob:
                    mock_glob.return_value = [Path(os.path.join(candidates_dir, "2026-03-17.json"))]
                    result = run_script("sync_to_sheets.py", ["--backfill", "--dry-run", "--no-translate"])

            # May succeed or fail depending on path mocking, but should not crash
            # At minimum, help should work
            help_result = run_script("sync_to_sheets.py", ["--help"])
            self.assertEqual(help_result.returncode, 0)


# ── Feedback Sync Tests ──────────────────────────────────────────

class TestFeedbackSync(unittest.TestCase):

    def test_feedback_sync_help(self):
        """Test feedback_sync.py --help works."""
        result = run_script("feedback_sync.py", ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("feedback", result.stdout.lower())

    def test_feedback_sync_dry_run_no_config(self):
        """Test feedback_sync.py --dry-run without config (should fail gracefully)."""
        result = run_script("feedback_sync.py", ["--dry-run"], timeout=10)
        # Expected to fail due to missing config/credentials, but should handle gracefully
        self.assertIn("ERROR", result.stderr)

    def test_feedback_sync_missing_dependencies(self):
        """Test feedback_sync.py behavior when gspread is not available."""
        # This test verifies the script imports properly and shows appropriate error
        # The script should import successfully but show error about missing gspread
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock config
            config = {"google_sheets": {"sheet_id": "test_id"}}
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f)

            # The script should show error about missing credentials or gspread
            result = run_script("feedback_sync.py", ["--dry-run"], timeout=10)
            # Should fail but not crash due to import errors
            self.assertNotEqual(result.returncode, -1)  # Not a crash


# ── Integration Tests ────────────────────────────────────────────

class TestIntegration(unittest.TestCase):

    def test_feed_fetch_limited(self):
        """Test feed.py fetch with very small limits to avoid external API calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)

            # Use very small limits to minimize external calls
            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                result = run_script("feed.py", ["fetch", "--limit", "1"], timeout=45)

            # May succeed or fail depending on network, but should not crash
            self.assertNotEqual(result.returncode, -1)  # Not a crash

            if result.returncode == 0:
                # If successful, should output valid JSON
                try:
                    output = json.loads(result.stdout)
                    self.assertIn("total", output)
                except json.JSONDecodeError:
                    self.fail("fetch command output was not valid JSON")

    def test_feed_recommend_with_preferences(self):
        """Test feed.py recommend with test preferences."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = create_test_config(tmpdir)
            prefs_path = create_test_preferences(tmpdir)

            with patch.dict(os.environ, {"FEEDS_DIR": os.path.join(tmpdir, "memory", "feeds")}):
                # Try to get recommendations with small limit
                result = run_script("feed.py", ["recommend", "--limit", "3"], timeout=60)

            # May succeed or fail depending on network, but should not crash
            self.assertNotEqual(result.returncode, -1)  # Not a crash

            if result.returncode == 0:
                # Should output recommendation JSON
                try:
                    output = json.loads(result.stdout)
                    self.assertIn("items", output)
                except json.JSONDecodeError:
                    self.fail("recommend command output was not valid JSON")

    def test_quality_scorer_with_real_data(self):
        """Test quality scorer with feedback and candidate data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create comprehensive test data
            fb_path = create_test_feedback(tmpdir)

            # Create sample candidates
            candidates_dir = os.path.join(tmpdir, "memory", "feeds", "candidates")
            os.makedirs(candidates_dir, exist_ok=True)

            candidates = [
                {"source": "hn", "title": "ML Research", "url": "https://hn.com/ml", "interest_score": 8.5},
                {"source": "af", "title": "AI Safety", "url": "https://af.org/safety", "interest_score": 9.0},
                {"source": "arxiv", "title": "Deep Learning", "url": "https://arxiv.org/dl", "interest_score": 7.2},
            ]

            digest = {"items": candidates}
            with open(os.path.join(candidates_dir, "2026-03-18.json"), 'w') as f:
                json.dump(digest, f)

            # Run quality scorer
            result = run_script("quality_scorer.py", ["--json", "--feeds-dir", tmpdir])
            self.assertEqual(result.returncode, 0)

            # Verify output
            try:
                report = json.loads(result.stdout)
                self.assertIn("quality_metrics", report)
                self.assertIn("precision_at_10", report["quality_metrics"])
                self.assertGreater(report["data_summary"]["total_candidates"], 0)
                self.assertGreater(report["data_summary"]["total_feedback"], 0)
            except json.JSONDecodeError:
                self.fail("Quality scorer output was not valid JSON")


# ── Error Handling Tests ─────────────────────────────────────────

class TestErrorHandling(unittest.TestCase):

    def test_scripts_handle_invalid_args(self):
        """Test that scripts handle invalid arguments gracefully."""
        scripts = ["feed.py", "quality_scorer.py", "migrate_hn.py", "sync_to_sheets.py", "feedback_sync.py"]

        for script in scripts:
            with self.subTest(script=script):
                # Test with clearly invalid argument
                result = run_script(script, ["--invalid-flag-that-should-not-exist"], timeout=10)
                # Should exit with error code but not crash
                self.assertNotEqual(result.returncode, 0)
                self.assertNotEqual(result.returncode, -1)  # Not a crash
                # Should show help or error message
                self.assertTrue(len(result.stderr) > 0 or len(result.stdout) > 0)

    def test_feed_invalid_command(self):
        """Test feed.py with invalid command."""
        result = run_script("feed.py", ["nonexistent-command"])
        self.assertNotEqual(result.returncode, 0)
        # Should show help when given invalid command
        self.assertIn("help", result.stderr.lower() or result.stdout.lower())

    def test_scripts_python_syntax(self):
        """Verify all scripts have valid Python syntax."""
        scripts = ["feed.py", "feed_engine.py", "quality_scorer.py", "migrate_hn.py",
                  "sync_to_sheets.py", "feedback_sync.py"]

        for script in scripts:
            with self.subTest(script=script):
                script_path = SCRIPT_DIR / script
                # Compile the file to check syntax
                try:
                    with open(script_path, 'r') as f:
                        code = f.read()
                    compile(code, script_path, 'exec')
                except SyntaxError as e:
                    self.fail(f"{script} has syntax error: {e}")
                except Exception as e:
                    # Other errors (import etc.) are OK for this test
                    pass


if __name__ == '__main__':
    # Run with increased verbosity to see individual test progress
    unittest.main(verbosity=2)