#!/usr/bin/env python3
"""Browser automation CLI using Playwright (Chromium).

Provides JS-rendered page fetching, form filling, screenshot/PDF output,
and cookie/session management with basic anti-detection measures.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Paths ──────────────────────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SESSION_DIR = WORKSPACE_ROOT / "memory" / "browser" / "sessions"

# ── Anti-detection pool ────────────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

_STEALTH_INIT_SCRIPT = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-TW', 'zh', 'en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
}
"""


def _random_viewport() -> dict:
    return {
        "width": random.randint(1280, 1920),
        "height": random.randint(768, 1080),
    }


def _launch_browser(playwright, headless: bool = True):
    """Launch Chromium with anti-detection args."""
    return playwright.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-extensions",
        ],
    )


def _new_context(browser, session_cookies: list | None = None):
    """Create a new browser context with stealth settings."""
    ctx = browser.new_context(
        user_agent=random.choice(_USER_AGENTS),
        viewport=_random_viewport(),
        java_script_enabled=True,
        ignore_https_errors=True,
    )
    ctx.add_init_script(_STEALTH_INIT_SCRIPT)
    if session_cookies:
        ctx.add_cookies(session_cookies)
    return ctx


# ── Session helpers ────────────────────────────────────────────────────────────

def _session_path(name: str) -> Path:
    return SESSION_DIR / f"{name}.json"


def load_session(name: str) -> list:
    """Load cookies from a named session. Returns [] if not found."""
    p = _session_path(name)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def save_session(name: str, cookies: list) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    _session_path(name).write_text(json.dumps(cookies, indent=2))


def list_sessions() -> list[str]:
    if not SESSION_DIR.exists():
        return []
    return [p.stem for p in SESSION_DIR.glob("*.json")]


def delete_session(name: str) -> bool:
    p = _session_path(name)
    if p.exists():
        p.unlink()
        return True
    return False


# ── Core operations ────────────────────────────────────────────────────────────

def fetch_page(
    url: str,
    *,
    wait_for: str | None = None,
    timeout: int = 30_000,
    text_only: bool = False,
    session: str | None = None,
) -> str:
    """Fetch a JS-rendered page and return HTML (or inner text if text_only)."""
    cookies = load_session(session) if session else None
    with sync_playwright() as p:
        browser = _launch_browser(p)
        ctx = _new_context(browser, cookies)
        page = ctx.new_page()
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        if wait_for:
            page.wait_for_selector(wait_for, timeout=timeout)
        else:
            page.wait_for_load_state("networkidle", timeout=timeout)
        result = page.inner_text("body") if text_only else page.content()
        browser.close()
    return result


def take_screenshot(
    url: str,
    output: str,
    *,
    full_page: bool = False,
    width: int = 1280,
    height: int = 800,
    wait_for: str | None = None,
    timeout: int = 30_000,
    session: str | None = None,
) -> None:
    """Take a screenshot of the given URL and save to output path."""
    cookies = load_session(session) if session else None
    with sync_playwright() as p:
        browser = _launch_browser(p)
        ctx = browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            viewport={"width": width, "height": height},
            ignore_https_errors=True,
        )
        ctx.add_init_script(_STEALTH_INIT_SCRIPT)
        if cookies:
            ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        if wait_for:
            page.wait_for_selector(wait_for, timeout=timeout)
        else:
            page.wait_for_load_state("networkidle", timeout=timeout)
        page.screenshot(path=output, full_page=full_page)
        browser.close()


def save_pdf(
    url: str,
    output: str,
    *,
    fmt: str = "A4",
    timeout: int = 30_000,
    session: str | None = None,
) -> None:
    """Save the page as PDF. Requires non-headless=False (Chromium limitation)."""
    cookies = load_session(session) if session else None
    with sync_playwright() as p:
        # PDF generation requires headless=True with new headless mode
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = _new_context(browser, cookies)
        page = ctx.new_page()
        page.goto(url, timeout=timeout, wait_until="networkidle")
        page.pdf(path=output, format=fmt)
        browser.close()


def fill_form(
    url: str,
    fields: dict[str, str],
    *,
    submit_selector: str | None = None,
    screenshot_after: str | None = None,
    timeout: int = 30_000,
    session: str | None = None,
) -> str:
    """Fill form fields by CSS selector and optionally submit.

    Returns page HTML after action.
    """
    cookies = load_session(session) if session else None
    with sync_playwright() as p:
        browser = _launch_browser(p)
        ctx = _new_context(browser, cookies)
        page = ctx.new_page()
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=timeout)

        for selector, value in fields.items():
            page.fill(selector, value)

        if submit_selector:
            page.click(submit_selector)
            page.wait_for_load_state("networkidle", timeout=timeout)

        if screenshot_after:
            page.screenshot(path=screenshot_after, full_page=True)

        html = page.content()
        browser.close()
    return html


def interactive_login(url: str, session_name: str) -> None:
    """Open browser for manual login, then save cookies as named session."""
    print(f"Opening browser at {url}")
    print("Log in manually, then PRESS ENTER in this terminal to save the session.")
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=False)
        ctx = _new_context(browser)
        page = ctx.new_page()
        page.goto(url)
        input()  # wait for user
        cookies = ctx.cookies()
        browser.close()
    save_session(session_name, cookies)
    print(f"Session '{session_name}' saved ({len(cookies)} cookies).")


# ── CLI ────────────────────────────────────────────────────────────────────────

def cmd_fetch(args: argparse.Namespace) -> None:
    result = fetch_page(
        args.url,
        wait_for=args.wait_for,
        timeout=args.timeout,
        text_only=args.text,
        session=args.session,
    )
    if args.json:
        print(json.dumps({"url": args.url, "content": result}))
    elif args.output:
        Path(args.output).write_text(result)
        print(f"Saved to {args.output}")
    else:
        print(result)


def cmd_screenshot(args: argparse.Namespace) -> None:
    take_screenshot(
        args.url,
        args.output,
        full_page=args.full_page,
        width=args.width,
        height=args.height,
        wait_for=args.wait_for,
        timeout=args.timeout,
        session=args.session,
    )
    print(f"Screenshot saved to {args.output}")


def cmd_pdf(args: argparse.Namespace) -> None:
    save_pdf(
        args.url,
        args.output,
        fmt=args.format,
        timeout=args.timeout,
        session=args.session,
    )
    print(f"PDF saved to {args.output}")


def cmd_form(args: argparse.Namespace) -> None:
    fields = json.loads(args.fill)
    html = fill_form(
        args.url,
        fields,
        submit_selector=args.submit,
        screenshot_after=args.screenshot,
        timeout=args.timeout,
        session=args.session,
    )
    if args.json:
        print(json.dumps({"url": args.url, "content": html}))
    elif args.output:
        Path(args.output).write_text(html)
        print(f"Result saved to {args.output}")
    else:
        print(html)


def cmd_session(args: argparse.Namespace) -> None:
    sub = args.session_cmd
    if sub == "save":
        interactive_login(args.url, args.name)
    elif sub == "list":
        sessions = list_sessions()
        if args.json:
            print(json.dumps(sessions))
        else:
            if sessions:
                for s in sessions:
                    print(s)
            else:
                print("(no sessions saved)")
    elif sub == "delete":
        if delete_session(args.name):
            print(f"Deleted session '{args.name}'")
        else:
            print(f"Session '{args.name}' not found", file=sys.stderr)
            sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="browser",
        description="Playwright browser automation — fetch, screenshot, pdf, form, session",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── fetch ──
    p_fetch = sub.add_parser("fetch", help="Fetch JS-rendered page content")
    p_fetch.add_argument("url")
    p_fetch.add_argument("--text", action="store_true", help="Return inner text only")
    p_fetch.add_argument("--wait-for", metavar="SELECTOR", help="Wait for CSS selector")
    p_fetch.add_argument("--timeout", type=int, default=30_000)
    p_fetch.add_argument("--session", help="Named cookie session to use")
    p_fetch.add_argument("--output", "-o", help="Write to file instead of stdout")
    p_fetch.add_argument("--json", action="store_true", help="JSON output")

    # ── screenshot ──
    p_ss = sub.add_parser("screenshot", help="Take a screenshot")
    p_ss.add_argument("url")
    p_ss.add_argument("--output", "-o", default="screenshot.png")
    p_ss.add_argument("--full-page", action="store_true")
    p_ss.add_argument("--width", type=int, default=1280)
    p_ss.add_argument("--height", type=int, default=800)
    p_ss.add_argument("--wait-for", metavar="SELECTOR")
    p_ss.add_argument("--timeout", type=int, default=30_000)
    p_ss.add_argument("--session")

    # ── pdf ──
    p_pdf = sub.add_parser("pdf", help="Save page as PDF")
    p_pdf.add_argument("url")
    p_pdf.add_argument("--output", "-o", default="page.pdf")
    p_pdf.add_argument("--format", default="A4", choices=["A4", "A3", "Letter", "Legal"])
    p_pdf.add_argument("--timeout", type=int, default=30_000)
    p_pdf.add_argument("--session")

    # ── form ──
    p_form = sub.add_parser("form", help="Fill and optionally submit a form")
    p_form.add_argument("url")
    p_form.add_argument("--fill", required=True, metavar="JSON",
                        help='JSON map of CSS selector → value, e.g. \'{"#name":"Leo"}\'')
    p_form.add_argument("--submit", metavar="SELECTOR", help="Click this selector after filling")
    p_form.add_argument("--screenshot", metavar="FILE", help="Screenshot after submit")
    p_form.add_argument("--timeout", type=int, default=30_000)
    p_form.add_argument("--session")
    p_form.add_argument("--output", "-o")
    p_form.add_argument("--json", action="store_true")

    # ── session ──
    p_sess = sub.add_parser("session", help="Manage cookie sessions")
    sess_sub = p_sess.add_subparsers(dest="session_cmd", required=True)

    p_sess_save = sess_sub.add_parser("save", help="Interactive login + save cookies")
    p_sess_save.add_argument("--name", required=True)
    p_sess_save.add_argument("--url", required=True)

    p_sess_list = sess_sub.add_parser("list", help="List saved sessions")
    p_sess_list.add_argument("--json", action="store_true")

    p_sess_del = sess_sub.add_parser("delete", help="Delete a saved session")
    p_sess_del.add_argument("--name", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "fetch": cmd_fetch,
        "screenshot": cmd_screenshot,
        "pdf": cmd_pdf,
        "form": cmd_form,
        "session": cmd_session,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
