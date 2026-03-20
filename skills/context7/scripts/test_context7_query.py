"""Tests for context7_query.py.

Covers:
- cache_load / cache_save: miss, hit, expired, corrupt
- search_library / get_docs: successful HTTP, network error, HTTP error
- search_to_markdown / docs_to_markdown: various response shapes
- build_parser: defaults and required args
- cmd_search / cmd_docs: integration via main() with mocked HTTP
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import context7_query  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_urlopen(payload: dict | str) -> MagicMock:
    if isinstance(payload, str):
        body = payload.encode("utf-8")
    else:
        body = json.dumps(payload).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# cache_load / cache_save
# ---------------------------------------------------------------------------


class TestCache:
    def test_miss_on_nonexistent_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        assert context7_query.cache_load("no/such/key") is None

    def test_roundtrip_save_and_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"content": "hello docs"}
        context7_query.cache_save("lib/topic_abc", payload)
        loaded = context7_query.cache_load("lib/topic_abc")
        assert loaded == payload

    def test_expired_entry_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(context7_query, "CACHE_TTL_SECONDS", 1)
        payload = {"content": "stale"}
        context7_query.cache_save("lib/old", payload)
        # Wind time forward past TTL
        with patch("time.time", return_value=time.time() + 10):
            result = context7_query.cache_load("lib/old")
        assert result is None

    def test_corrupt_cache_file_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        path = tmp_path / "lib" / "bad.json"
        path.parent.mkdir(parents=True)
        path.write_text("not valid json", encoding="utf-8")
        assert context7_query.cache_load("lib/bad") is None

    def test_save_creates_parent_dirs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        context7_query.cache_save("deep/nested/key", {"x": 1})
        assert (tmp_path / "deep" / "nested" / "key.json").exists()


# ---------------------------------------------------------------------------
# search_library
# ---------------------------------------------------------------------------


class TestSearchLibrary:
    def test_returns_parsed_json(self) -> None:
        payload = {"results": [{"id": "/pytorch/pytorch", "name": "PyTorch"}]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)):
            result = context7_query.search_library("pytorch")
        assert result["results"][0]["id"] == "/pytorch/pytorch"

    def test_encodes_query_in_url(self) -> None:
        payload = {"results": []}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)) as mock_open:
            context7_query.search_library("my lib")
        url = mock_open.call_args[0][0].full_url
        assert "q=my+lib" in url or "q=my%20lib" in url

    def test_raises_on_network_error(self) -> None:
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            with pytest.raises(urllib.error.URLError):
                context7_query.search_library("anything")

    def test_raises_on_http_error(self) -> None:
        err = urllib.error.HTTPError("url", 404, "Not Found", MagicMock(), None)
        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(urllib.error.HTTPError):
                context7_query.search_library("missing")


# ---------------------------------------------------------------------------
# get_docs
# ---------------------------------------------------------------------------


class TestGetDocs:
    def test_returns_parsed_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"content": "# PyTorch docs"}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)):
            result = context7_query.get_docs("/pytorch/pytorch", use_cache=False)
        assert result["content"] == "# PyTorch docs"

    def test_uses_cache_on_second_call(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"content": "cached content"}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)) as mock_open:
            context7_query.get_docs("/lib/x", topic="foo", use_cache=True)
            context7_query.get_docs("/lib/x", topic="foo", use_cache=True)
        assert mock_open.call_count == 1  # second call hit cache

    def test_no_cache_bypasses_cache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"content": "fresh"}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)) as mock_open:
            context7_query.get_docs("/lib/y", use_cache=False)
            context7_query.get_docs("/lib/y", use_cache=False)
        assert mock_open.call_count == 2

    def test_includes_topic_in_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"content": "..."}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)) as mock_open:
            context7_query.get_docs("/numpy/numpy", topic="ndarray", use_cache=False)
        url = mock_open.call_args[0][0].full_url
        assert "topic=ndarray" in url

    def test_includes_tokens_in_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"content": "..."}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)) as mock_open:
            context7_query.get_docs("/lib/z", tokens=5000, use_cache=False)
        url = mock_open.call_args[0][0].full_url
        assert "tokens=5000" in url

    def test_raises_on_network_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("no route"),
        ):
            with pytest.raises(urllib.error.URLError):
                context7_query.get_docs("/lib/fail", use_cache=False)


# ---------------------------------------------------------------------------
# search_to_markdown
# ---------------------------------------------------------------------------


class TestSearchToMarkdown:
    def test_renders_library_id_and_name(self) -> None:
        data = {"results": [{"id": "/pytorch/pytorch", "name": "PyTorch", "description": "ML lib"}]}
        md = context7_query.search_to_markdown(data)
        assert "/pytorch/pytorch" in md
        assert "PyTorch" in md
        assert "ML lib" in md

    def test_empty_results(self) -> None:
        md = context7_query.search_to_markdown({"results": []})
        assert "No libraries found" in md

    def test_missing_results_key(self) -> None:
        md = context7_query.search_to_markdown({})
        assert "No libraries found" in md

    def test_version_shown_when_present(self) -> None:
        data = {"results": [{"id": "/lib/x", "name": "X", "version": "2.0.0"}]}
        md = context7_query.search_to_markdown(data)
        assert "v2.0.0" in md

    def test_multiple_results_all_rendered(self) -> None:
        data = {
            "results": [
                {"id": "/a/a", "name": "A"},
                {"id": "/b/b", "name": "B"},
                {"id": "/c/c", "name": "C"},
            ]
        }
        md = context7_query.search_to_markdown(data)
        assert "/a/a" in md
        assert "/b/b" in md
        assert "/c/c" in md


# ---------------------------------------------------------------------------
# docs_to_markdown
# ---------------------------------------------------------------------------


class TestDocsToMarkdown:
    def test_content_field(self) -> None:
        data = {"content": "# Docs\nSome text."}
        md = context7_query.docs_to_markdown(data)
        assert "# Docs" in md
        assert md.endswith("\n")

    def test_text_field_fallback(self) -> None:
        data = {"text": "plain text docs"}
        md = context7_query.docs_to_markdown(data)
        assert "plain text docs" in md

    def test_plain_string_input(self) -> None:
        md = context7_query.docs_to_markdown("raw string\n")  # type: ignore[arg-type]
        assert md == "raw string\n"

    def test_plain_string_gets_newline(self) -> None:
        md = context7_query.docs_to_markdown("no newline")  # type: ignore[arg-type]
        assert md.endswith("\n")

    def test_fallback_to_json_dump_when_no_content(self) -> None:
        data = {"something": "else"}
        md = context7_query.docs_to_markdown(data)
        assert "something" in md

    def test_output_always_ends_with_newline(self) -> None:
        for data in [
            {"content": "x"},
            {"text": "y"},
            {"other": "z"},
            "bare",  # type: ignore[list-item]
        ]:
            assert context7_query.docs_to_markdown(data).endswith("\n")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_search_requires_query(self) -> None:
        p = context7_query.build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["search"])

    def test_docs_requires_library(self) -> None:
        p = context7_query.build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["docs"])

    def test_docs_default_tokens(self) -> None:
        p = context7_query.build_parser()
        args = p.parse_args(["docs", "--library", "/x/y"])
        assert args.tokens == 10000

    def test_docs_default_format_is_md(self) -> None:
        p = context7_query.build_parser()
        args = p.parse_args(["docs", "--library", "/x/y"])
        assert args.format == "md"

    def test_docs_no_cache_flag(self) -> None:
        p = context7_query.build_parser()
        args = p.parse_args(["docs", "--library", "/x/y", "--no-cache"])
        assert args.no_cache is True

    def test_search_default_format_is_md(self) -> None:
        p = context7_query.build_parser()
        args = p.parse_args(["search", "--query", "numpy"])
        assert args.format == "md"

    def test_command_is_required(self) -> None:
        p = context7_query.build_parser()
        with pytest.raises(SystemExit):
            p.parse_args([])


# ---------------------------------------------------------------------------
# main() end-to-end
# ---------------------------------------------------------------------------


class TestMain:
    def test_search_md_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"results": [{"id": "/numpy/numpy", "name": "NumPy"}]}
        monkeypatch.setattr(sys, "argv", ["c7", "search", "--query", "numpy", "--format", "md"])
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)):
            rc = context7_query.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "numpy" in out

    def test_docs_json_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        payload = {"content": "# NumPy docs"}
        monkeypatch.setattr(
            sys, "argv",
            ["c7", "docs", "--library", "/numpy/numpy", "--format", "json", "--no-cache"],
        )
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)):
            rc = context7_query.main()
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["content"] == "# NumPy docs"

    def test_docs_network_error_returns_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(
            sys, "argv",
            ["c7", "docs", "--library", "/x/y", "--no-cache"],
        )
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            rc = context7_query.main()
        assert rc == 1

    def test_docs_invalid_tokens_returns_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(context7_query, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(
            sys, "argv",
            ["c7", "docs", "--library", "/x/y", "--tokens", "0"],
        )
        rc = context7_query.main()
        assert rc == 2
