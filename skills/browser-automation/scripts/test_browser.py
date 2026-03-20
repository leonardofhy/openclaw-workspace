#!/usr/bin/env python3
"""Tests for browser-automation skill (all mocked — no real browser needed)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(__file__))

import browser as br


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_pw_mock(html: str = "<html><body>hello</body></html>", text: str = "hello"):
    """Build a nested mock that mimics playwright's sync_playwright context."""
    page = MagicMock()
    page.content.return_value = html
    page.inner_text.return_value = text
    page.screenshot.return_value = None
    page.pdf.return_value = None
    page.goto.return_value = None
    page.fill.return_value = None
    page.click.return_value = None
    page.wait_for_selector.return_value = None
    page.wait_for_load_state.return_value = None

    ctx = MagicMock()
    ctx.new_page.return_value = page
    ctx.cookies.return_value = [{"name": "sid", "value": "abc", "domain": ".example.com"}]
    ctx.add_cookies.return_value = None

    browser = MagicMock()
    browser.new_context.return_value = ctx
    browser.close.return_value = None

    chromium = MagicMock()
    chromium.launch.return_value = browser

    pw = MagicMock()
    pw.chromium = chromium

    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=pw)
    cm.__exit__ = MagicMock(return_value=False)

    return cm, pw, browser, ctx, page


# ── Session management ────────────────────────────────────────────────────────

class TestSessionManagement(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig_dir = br.SESSION_DIR
        br.SESSION_DIR = Path(self.tmp.name)

    def tearDown(self):
        br.SESSION_DIR = self.orig_dir
        self.tmp.cleanup()

    def test_save_and_load(self):
        cookies = [{"name": "x", "value": "1", "domain": ".ex.com"}]
        br.save_session("test", cookies)
        loaded = br.load_session("test")
        self.assertEqual(loaded, cookies)

    def test_load_missing_returns_empty(self):
        self.assertEqual(br.load_session("nonexistent"), [])

    def test_list_sessions(self):
        br.save_session("alpha", [])
        br.save_session("beta", [])
        sessions = br.list_sessions()
        self.assertIn("alpha", sessions)
        self.assertIn("beta", sessions)

    def test_delete_session(self):
        br.save_session("del_me", [{"name": "a", "value": "b"}])
        self.assertTrue(br.delete_session("del_me"))
        self.assertEqual(br.load_session("del_me"), [])

    def test_delete_nonexistent_returns_false(self):
        self.assertFalse(br.delete_session("ghost"))


# ── fetch_page ────────────────────────────────────────────────────────────────

class TestFetchPage(unittest.TestCase):
    @patch("browser.sync_playwright")
    def test_returns_html(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock("<html>ok</html>")
        mock_sp.return_value = cm
        result = br.fetch_page("https://example.com")
        self.assertEqual(result, "<html>ok</html>")
        page.goto.assert_called_once()

    @patch("browser.sync_playwright")
    def test_text_only(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock(text="just text")
        mock_sp.return_value = cm
        result = br.fetch_page("https://example.com", text_only=True)
        self.assertEqual(result, "just text")
        page.inner_text.assert_called_once_with("body")

    @patch("browser.sync_playwright")
    def test_wait_for_selector(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        br.fetch_page("https://example.com", wait_for=".content")
        page.wait_for_selector.assert_called_once_with(".content", timeout=30_000)

    @patch("browser.sync_playwright")
    def test_no_wait_selector_calls_networkidle(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        br.fetch_page("https://example.com")
        page.wait_for_load_state.assert_called_with("networkidle", timeout=30_000)

    @patch("browser.sync_playwright")
    def test_uses_session_cookies(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        with tempfile.TemporaryDirectory() as tmp:
            orig = br.SESSION_DIR
            br.SESSION_DIR = Path(tmp)
            cookies = [{"name": "sid", "value": "xyz", "domain": ".example.com"}]
            br.save_session("mysite", cookies)
            br.fetch_page("https://example.com", session="mysite")
            br.SESSION_DIR = orig
        ctx.add_cookies.assert_called_once_with(cookies)


# ── take_screenshot ───────────────────────────────────────────────────────────

class TestTakeScreenshot(unittest.TestCase):
    @patch("browser.sync_playwright")
    def test_screenshot_called(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "shot.png")
            br.take_screenshot("https://example.com", out)
            page.screenshot.assert_called_once_with(path=out, full_page=False)

    @patch("browser.sync_playwright")
    def test_full_page(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "shot.png")
            br.take_screenshot("https://example.com", out, full_page=True)
            page.screenshot.assert_called_once_with(path=out, full_page=True)

    @patch("browser.sync_playwright")
    def test_custom_viewport(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "shot.png")
            br.take_screenshot("https://example.com", out, width=1920, height=1080)
        _, kwargs = brow.new_context.call_args
        self.assertEqual(kwargs["viewport"], {"width": 1920, "height": 1080})


# ── save_pdf ──────────────────────────────────────────────────────────────────

class TestSavePdf(unittest.TestCase):
    @patch("browser.sync_playwright")
    def test_pdf_called(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "page.pdf")
            br.save_pdf("https://example.com", out)
            page.pdf.assert_called_once_with(path=out, format="A4")

    @patch("browser.sync_playwright")
    def test_custom_format(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "page.pdf")
            br.save_pdf("https://example.com", out, fmt="Letter")
            page.pdf.assert_called_once_with(path=out, format="Letter")


# ── fill_form ─────────────────────────────────────────────────────────────────

class TestFillForm(unittest.TestCase):
    @patch("browser.sync_playwright")
    def test_fills_fields(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock("<html>form result</html>")
        mock_sp.return_value = cm
        fields = {"#name": "Leo", "#email": "leo@example.com"}
        br.fill_form("https://example.com/form", fields)
        page.fill.assert_any_call("#name", "Leo")
        page.fill.assert_any_call("#email", "leo@example.com")

    @patch("browser.sync_playwright")
    def test_submit_clicks(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        br.fill_form("https://example.com/form", {"#x": "y"}, submit_selector="#btn")
        page.click.assert_called_once_with("#btn")

    @patch("browser.sync_playwright")
    def test_no_submit_no_click(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        br.fill_form("https://example.com/form", {"#x": "y"})
        page.click.assert_not_called()

    @patch("browser.sync_playwright")
    def test_screenshot_after_submit(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        with tempfile.TemporaryDirectory() as tmp:
            shot = str(Path(tmp) / "result.png")
            br.fill_form("https://example.com/form", {"#x": "y"},
                         submit_selector="#btn", screenshot_after=shot)
            page.screenshot.assert_called_once_with(path=shot, full_page=True)

    @patch("browser.sync_playwright")
    def test_returns_html(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock("<html>done</html>")
        mock_sp.return_value = cm
        result = br.fill_form("https://example.com/form", {})
        self.assertEqual(result, "<html>done</html>")


# ── Anti-detection ────────────────────────────────────────────────────────────

class TestAntiDetection(unittest.TestCase):
    def test_random_viewport_in_range(self):
        for _ in range(20):
            vp = br._random_viewport()
            self.assertGreaterEqual(vp["width"], 1280)
            self.assertLessEqual(vp["width"], 1920)
            self.assertGreaterEqual(vp["height"], 768)
            self.assertLessEqual(vp["height"], 1080)

    def test_user_agents_are_desktop_chrome(self):
        for ua in br._USER_AGENTS:
            self.assertIn("Chrome", ua)
            self.assertNotIn("Mobile", ua)

    def test_stealth_script_hides_webdriver(self):
        self.assertIn("'webdriver'", br._STEALTH_INIT_SCRIPT)
        self.assertIn("undefined", br._STEALTH_INIT_SCRIPT)

    def test_stealth_script_adds_chrome_object(self):
        self.assertIn("window.chrome", br._STEALTH_INIT_SCRIPT)

    @patch("browser.sync_playwright")
    def test_launch_disables_automation_flag(self, mock_sp):
        cm, pw, brow, ctx, page = _make_pw_mock()
        mock_sp.return_value = cm
        br.fetch_page("https://example.com")
        _, kwargs = pw.chromium.launch.call_args
        args_list = kwargs.get("args", [])
        self.assertIn("--disable-blink-features=AutomationControlled", args_list)


# ── CLI argument parsing ──────────────────────────────────────────────────────

class TestCLIParser(unittest.TestCase):
    def setUp(self):
        self.parser = br.build_parser()

    def test_fetch_defaults(self):
        args = self.parser.parse_args(["fetch", "https://example.com"])
        self.assertEqual(args.url, "https://example.com")
        self.assertFalse(args.text)
        self.assertEqual(args.timeout, 30_000)
        self.assertIsNone(args.session)

    def test_fetch_all_flags(self):
        args = self.parser.parse_args([
            "fetch", "https://example.com",
            "--text", "--wait-for", ".main", "--timeout", "5000",
            "--session", "mysite", "--json",
        ])
        self.assertTrue(args.text)
        self.assertEqual(args.wait_for, ".main")
        self.assertEqual(args.timeout, 5000)
        self.assertEqual(args.session, "mysite")
        self.assertTrue(args.json)

    def test_screenshot_defaults(self):
        args = self.parser.parse_args(["screenshot", "https://example.com"])
        self.assertEqual(args.output, "screenshot.png")
        self.assertFalse(args.full_page)
        self.assertEqual(args.width, 1280)
        self.assertEqual(args.height, 800)

    def test_pdf_format_choices(self):
        for fmt in ["A4", "A3", "Letter", "Legal"]:
            args = self.parser.parse_args(["pdf", "https://example.com", "--format", fmt])
            self.assertEqual(args.format, fmt)

    def test_form_requires_fill(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["form", "https://example.com"])

    def test_session_list(self):
        args = self.parser.parse_args(["session", "list"])
        self.assertEqual(args.session_cmd, "list")

    def test_session_delete(self):
        args = self.parser.parse_args(["session", "delete", "--name", "mysite"])
        self.assertEqual(args.name, "mysite")


# ── cmd_session list / delete (unit) ─────────────────────────────────────────

class TestCmdSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig_dir = br.SESSION_DIR
        br.SESSION_DIR = Path(self.tmp.name)

    def tearDown(self):
        br.SESSION_DIR = self.orig_dir
        self.tmp.cleanup()

    def test_cmd_session_list_json(self, capsys=None):
        br.save_session("s1", [])
        br.save_session("s2", [])
        parser = br.build_parser()
        args = parser.parse_args(["session", "list", "--json"])
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            br.cmd_session(args)
        data = json.loads(buf.getvalue())
        self.assertIn("s1", data)
        self.assertIn("s2", data)

    def test_cmd_session_delete(self):
        br.save_session("bye", [{"name": "x"}])
        parser = br.build_parser()
        args = parser.parse_args(["session", "delete", "--name", "bye"])
        br.cmd_session(args)
        self.assertEqual(br.load_session("bye"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
