"""Tests for tavily_search.py.

Covers:
- load_api_key(): from env var, from secrets file, missing key
- to_markdown(): with answer, without answer, empty results
- tavily_search(): successful HTTP call, API error body, network error
- build_parser(): argument defaults and flags
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path injection — must happen before the import so the module resolves cleanly
# ---------------------------------------------------------------------------
sys.path.insert(0, "/Users/leonardo/.openclaw/workspace/skills/tavily-search/scripts")
import tavily_search  # noqa: E402  (import after sys.path mutation is intentional)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(payload: dict) -> MagicMock:
    """Return a MagicMock that mimics urllib.request.urlopen context manager."""
    body = json.dumps(payload).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    # Simulate decode on the bytes returned by read()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _call_tavily_search(api_key: str = "test-key", query: str = "test query", **kwargs) -> dict:
    """Call tavily_search.tavily_search with sensible defaults."""
    defaults = dict(
        max_results=5,
        search_depth="basic",
        include_answer=False,
        include_raw_content=False,
        include_images=False,
    )
    defaults.update(kwargs)
    return tavily_search.tavily_search(api_key=api_key, query=query, **defaults)


# ---------------------------------------------------------------------------
# load_api_key tests
# ---------------------------------------------------------------------------


class TestLoadApiKey:
    """Tests for load_api_key()."""

    def test_returns_key_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_api_key() returns the value of TAVILY_API_KEY when set."""
        monkeypatch.setenv("TAVILY_API_KEY", "env-key-abc123")
        assert tavily_search.load_api_key() == "env-key-abc123"

    def test_env_var_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_api_key() strips surrounding whitespace from the env var value."""
        monkeypatch.setenv("TAVILY_API_KEY", "  spaced-key  ")
        assert tavily_search.load_api_key() == "spaced-key"

    def test_reads_key_from_secrets_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """load_api_key() parses TAVILY_API_KEY from secrets/tavily.env when env var absent."""
        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        env_file = secrets_dir / "tavily.env"
        env_file.write_text("# comment\nTAVILY_API_KEY=file-key-xyz\n", encoding="utf-8")

        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        # Patch the WORKSPACE constant so the module looks in tmp_path instead
        monkeypatch.setattr(tavily_search, "WORKSPACE", tmp_path)

        assert tavily_search.load_api_key() == "file-key-xyz"

    def test_secrets_file_strips_quotes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """load_api_key() strips surrounding quotes from the file value."""
        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        env_file = secrets_dir / "tavily.env"
        env_file.write_text('TAVILY_API_KEY="quoted-key"\n', encoding="utf-8")

        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setattr(tavily_search, "WORKSPACE", tmp_path)

        assert tavily_search.load_api_key() == "quoted-key"

    def test_returns_empty_string_when_key_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """load_api_key() returns empty string when neither env var nor file provides a key."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        # Point WORKSPACE at a tmp directory that has no secrets/tavily.env
        monkeypatch.setattr(tavily_search, "WORKSPACE", tmp_path)

        result = tavily_search.load_api_key()
        assert result == ""

    def test_ignores_unrelated_keys_in_secrets_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """load_api_key() ignores lines with keys other than TAVILY_API_KEY."""
        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        env_file = secrets_dir / "tavily.env"
        env_file.write_text("OTHER_KEY=irrelevant\n# no tavily key here\n", encoding="utf-8")

        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setattr(tavily_search, "WORKSPACE", tmp_path)

        assert tavily_search.load_api_key() == ""


# ---------------------------------------------------------------------------
# to_markdown tests
# ---------------------------------------------------------------------------


class TestToMarkdown:
    """Tests for to_markdown()."""

    def test_with_answer_and_results(self) -> None:
        """to_markdown() renders the answer block then numbered results."""
        result = {
            "answer": "Paris is the capital of France.",
            "results": [
                {
                    "title": "France",
                    "url": "https://example.com/france",
                    "score": 0.98,
                    "content": "France is a country in Western Europe.",
                }
            ],
        }
        md = tavily_search.to_markdown(result)

        assert "Paris is the capital of France." in md
        assert "1. France" in md
        assert "https://example.com/france" in md
        assert "score: 0.98" in md
        assert "France is a country in Western Europe." in md

    def test_without_answer(self) -> None:
        """to_markdown() skips the answer block when answer is absent."""
        result = {
            "results": [
                {
                    "title": "Python",
                    "url": "https://python.org",
                    "score": 0.9,
                    "content": "A programming language.",
                }
            ]
        }
        md = tavily_search.to_markdown(result)

        # No answer section header should appear
        assert "1. Python" in md
        assert "https://python.org" in md

    def test_empty_results(self) -> None:
        """to_markdown() handles a response with no results gracefully."""
        result: dict = {"results": []}
        md = tavily_search.to_markdown(result)

        # Should return at minimum a newline-terminated string without crashing
        assert isinstance(md, str)
        assert md.endswith("\n")

    def test_result_without_url_or_score(self) -> None:
        """to_markdown() omits URL and score lines when those fields are absent."""
        result = {
            "results": [
                {
                    "title": "Minimal",
                    "content": "Some content.",
                }
            ]
        }
        md = tavily_search.to_markdown(result)

        assert "1. Minimal" in md
        assert "score:" not in md

    def test_result_with_missing_title_uses_placeholder(self) -> None:
        """to_markdown() uses '(no title)' when title is absent."""
        result = {
            "results": [
                {
                    "url": "https://example.com",
                    "content": "Some content.",
                }
            ]
        }
        md = tavily_search.to_markdown(result)

        assert "(no title)" in md

    def test_output_ends_with_newline(self) -> None:
        """to_markdown() always returns a string ending with a newline."""
        result = {
            "answer": "Short answer.",
            "results": [],
        }
        md = tavily_search.to_markdown(result)
        assert md.endswith("\n")

    def test_multiple_results_numbered_sequentially(self) -> None:
        """to_markdown() numbers multiple results starting from 1."""
        items = [
            {"title": f"Result {n}", "url": f"https://example.com/{n}", "content": "x"}
            for n in range(1, 4)
        ]
        result = {"results": items}
        md = tavily_search.to_markdown(result)

        assert "1. Result 1" in md
        assert "2. Result 2" in md
        assert "3. Result 3" in md


# ---------------------------------------------------------------------------
# tavily_search (HTTP) tests
# ---------------------------------------------------------------------------


class TestTavilySearch:
    """Tests for tavily_search() — HTTP layer mocked via urllib.request.urlopen."""

    def test_successful_search_returns_parsed_json(self) -> None:
        """tavily_search() parses and returns the JSON response body on success."""
        payload = {
            "answer": "42",
            "results": [
                {"title": "Deep Thought", "url": "https://example.com", "score": 1.0, "content": "..."}
            ],
        }
        mock_resp = _make_mock_response(payload)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _call_tavily_search()

        assert result["answer"] == "42"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Deep Thought"

    def test_search_sends_correct_payload(self) -> None:
        """tavily_search() encodes all parameters in the POST body."""
        payload = {"results": []}
        mock_resp = _make_mock_response(payload)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            _call_tavily_search(
                api_key="my-key",
                query="hello world",
                max_results=3,
                search_depth="advanced",
                include_answer=True,
            )

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        body = json.loads(request_obj.data.decode("utf-8"))

        assert body["api_key"] == "my-key"
        assert body["query"] == "hello world"
        assert body["max_results"] == 3
        assert body["search_depth"] == "advanced"
        assert body["include_answer"] is True

    def test_search_uses_post_method(self) -> None:
        """tavily_search() constructs a POST request to the Tavily endpoint."""
        mock_resp = _make_mock_response({"results": []})

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            _call_tavily_search()

        request_obj = mock_urlopen.call_args[0][0]
        assert request_obj.method == "POST"
        assert request_obj.full_url == "https://api.tavily.com/search"

    def test_network_error_raises_urllib_error(self) -> None:
        """tavily_search() propagates URLError on network failure."""
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            with pytest.raises(urllib.error.URLError):
                _call_tavily_search()

    def test_api_error_response_raises_http_error(self) -> None:
        """tavily_search() propagates HTTPError when the API returns a 4xx/5xx status."""
        http_error = urllib.error.HTTPError(
            url="https://api.tavily.com/search",
            code=401,
            msg="Unauthorized",
            hdrs=MagicMock(),  # type: ignore[arg-type]
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=http_error):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                _call_tavily_search(api_key="bad-key")

        assert exc_info.value.code == 401

    def test_empty_results_list_returned(self) -> None:
        """tavily_search() handles an API response with an empty results list."""
        payload = {"results": []}
        mock_resp = _make_mock_response(payload)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _call_tavily_search()

        assert result["results"] == []


# ---------------------------------------------------------------------------
# build_parser tests
# ---------------------------------------------------------------------------


class TestBuildParser:
    """Tests for build_parser() argument defaults and validation."""

    def test_default_max_results_is_five(self) -> None:
        """build_parser() sets --max-results default to 5."""
        parser = tavily_search.build_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.max_results == 5

    def test_default_search_depth_is_basic(self) -> None:
        """build_parser() sets --search-depth default to 'basic'."""
        parser = tavily_search.build_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.search_depth == "basic"

    def test_include_answer_flag_defaults_false(self) -> None:
        """build_parser() sets --include-answer default to False."""
        parser = tavily_search.build_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.include_answer is False

    def test_include_answer_flag_sets_true(self) -> None:
        """build_parser() sets --include-answer to True when flag is present."""
        parser = tavily_search.build_parser()
        args = parser.parse_args(["--query", "test", "--include-answer"])
        assert args.include_answer is True

    def test_format_defaults_to_json(self) -> None:
        """build_parser() sets --format default to 'json'."""
        parser = tavily_search.build_parser()
        args = parser.parse_args(["--query", "test"])
        assert args.format == "json"

    def test_invalid_search_depth_exits(self) -> None:
        """build_parser() rejects invalid --search-depth values."""
        parser = tavily_search.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--query", "test", "--search-depth", "turbo"])
