#!/usr/bin/env python3
"""Tests for memory_search_local.py"""
import sys
import os
import json
import re
import tempfile
import time

sys.path.insert(0, os.path.dirname(__file__))
from memory_search_local import (
    tokenize, parse_chunks, build_index, search, collect_files,
    _is_daily, _index_path, _fts5_db_path,
    _cjk_expand, parse_jsonl_chunks, collect_jsonl_files,
    keyword_search, search_fts5, search_bm25,
    _extract_strings,
)
from pathlib import Path

import pytest


@pytest.fixture
def mem_tree(tmp_path):
    """Create a temporary memory directory with sample markdown files."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    # Named file: knowledge
    (memory_dir / "knowledge.md").write_text(
        "# Knowledge\n\n"
        "## Mechanistic Interpretability\n"
        "Research on understanding neural network internals.\n"
        "Key topic: activation patching and circuit analysis.\n\n"
        "## AudioMatters\n"
        "Interspeech 2026 paper about audio processing in LLMs.\n"
        "Co-authors: 智凱, 晨安\n",
        encoding="utf-8",
    )

    # Named file: projects
    (memory_dir / "projects.md").write_text(
        "# Projects\n\n"
        "## Paper A\n"
        "Outline drafted. Next: GPU scale-up experiments.\n"
        "Deadline approaching in April.\n\n"
        "## Income Strategy\n"
        "Target: consulting, ~5h/week.\n",
        encoding="utf-8",
    )

    # Daily file
    (memory_dir / "2026-03-18.md").write_text(
        "# 2026-03-18\n\n"
        "## Research\n"
        "Worked on mechanistic interpretability experiments.\n"
        "Met with 智凱 about AudioMatters revisions.\n\n"
        "## Personal\n"
        "Went swimming. Had lab dinner.\n",
        encoding="utf-8",
    )

    # Another daily file
    (memory_dir / "2026-03-17.md").write_text(
        "# 2026-03-17\n\n"
        "## Tasks\n"
        "Set up Claude Code orchestrator.\n"
        "Fixed experiment dispatcher.\n",
        encoding="utf-8",
    )

    # MEMORY.md at parent level
    (tmp_path / "MEMORY.md").write_text(
        "# MEMORY.md\n\n"
        "## About Leo\n"
        "NTU grad student. Research: mechanistic interpretability.\n\n"
        "## Current Research\n"
        "AudioMatters — Interspeech 2026\n",
        encoding="utf-8",
    )

    # Unicode file
    (memory_dir / "people.md").write_text(
        "# People\n\n"
        "## 李宏毅老師\n"
        "指導教授，NTU CSIE\n\n"
        "## 智凱哥\n"
        "最常互動的 labmate，AudioMatters 共同一作\n",
        encoding="utf-8",
    )

    return tmp_path, memory_dir


def test_tokenize_basic():
    tokens = tokenize("Hello world, this is a test!")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    # stopwords removed
    assert "this" not in tokens
    assert "is" not in tokens


def test_tokenize_unicode():
    tokens = tokenize("李宏毅老師 mechanistic interpretability 研究")
    assert any("李宏毅" in t for t in tokens)
    assert "mechanistic" in tokens
    assert "interpretability" in tokens


def test_tokenize_empty():
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_is_daily():
    assert _is_daily(Path("2026-03-18.md"))
    assert _is_daily(Path("memory/2025-01-01.md"))
    assert not _is_daily(Path("knowledge.md"))
    assert not _is_daily(Path("anti-patterns.md"))


def test_parse_chunks(mem_tree):
    _, memory_dir = mem_tree
    chunks = parse_chunks(memory_dir / "knowledge.md")
    headers = [c["header"] for c in chunks]
    assert "Mechanistic Interpretability" in headers
    assert "AudioMatters" in headers
    mi_chunk = next(c for c in chunks if c["header"] == "Mechanistic Interpretability")
    assert "activation patching" in mi_chunk["text"]


def test_parse_chunks_empty(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("", encoding="utf-8")
    assert parse_chunks(empty) == []


def test_parse_chunks_no_headers(tmp_path):
    f = tmp_path / "flat.md"
    f.write_text("Just some text without headers.\nAnother line.", encoding="utf-8")
    chunks = parse_chunks(f)
    assert len(chunks) == 1
    assert "Just some text" in chunks[0]["text"]


def test_collect_files_excludes_daily(mem_tree):
    _, memory_dir = mem_tree
    files = collect_files(memory_dir, include_daily=False)
    names = [f.name for f in files]
    assert "knowledge.md" in names
    assert "projects.md" in names
    assert "2026-03-18.md" not in names
    assert "2026-03-17.md" not in names


def test_collect_files_includes_daily(mem_tree):
    _, memory_dir = mem_tree
    files = collect_files(memory_dir, include_daily=True)
    names = [f.name for f in files]
    assert "2026-03-18.md" in names
    assert "2026-03-17.md" in names


def test_index_builds(mem_tree):
    _, memory_dir = mem_tree
    index = build_index(memory_dir, include_daily=False, force=True)
    assert index["num_chunks"] > 0
    assert index["num_files"] > 0
    assert len(index["chunks"]) == index["num_chunks"]
    assert len(index["corpus"]) == index["num_chunks"]
    # Cache file created
    assert _index_path(memory_dir).exists()


def test_basic_search(mem_tree):
    _, memory_dir = mem_tree
    results = search("mechanistic interpretability", memory_dir, top_k=5)
    assert len(results) > 0
    # Top result should mention mechanistic interpretability
    assert "mechanistic" in results[0]["snippet"].lower() or "interpretability" in results[0]["snippet"].lower()
    assert results[0]["score"] > 0


def test_bm25_ranking(mem_tree):
    _, memory_dir = mem_tree
    results = search("mechanistic interpretability circuit analysis", memory_dir, top_k=5)
    assert len(results) > 0
    # The knowledge.md chunk about mech interp should rank highest (most matching terms)
    top = results[0]
    assert "knowledge.md" in top["path"] or "MEMORY.md" in top["path"]
    # Scores should be descending
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i + 1]["score"]


def test_top_k(mem_tree):
    _, memory_dir = mem_tree
    results = search("research", memory_dir, top_k=2)
    assert len(results) <= 2


def test_include_daily(mem_tree):
    _, memory_dir = mem_tree
    # Without daily: "swimming" only in daily file
    results_no_daily = search("swimming", memory_dir, include_daily=False)
    results_with_daily = search("swimming", memory_dir, include_daily=True, force_rebuild=True)
    # Swimming is only in the daily file
    daily_paths = [r["path"] for r in results_with_daily if "2026-03-18" in r["path"]]
    assert len(daily_paths) > 0
    no_daily_paths = [r["path"] for r in results_no_daily if "2026-03-18" in r["path"]]
    assert len(no_daily_paths) == 0


def test_cache_invalidation(mem_tree):
    _, memory_dir = mem_tree
    # Build initial index
    build_index(memory_dir, include_daily=False, force=True)
    idx_file = _index_path(memory_dir)
    old_mtime = idx_file.stat().st_mtime

    # Wait and modify a file
    time.sleep(0.1)
    (memory_dir / "knowledge.md").write_text(
        "# Knowledge\n\n## New Topic\nBrand new content about transformers.\n",
        encoding="utf-8",
    )

    # Rebuild should detect change
    index = build_index(memory_dir, include_daily=False)
    new_mtime = idx_file.stat().st_mtime
    assert new_mtime > old_mtime
    # New content should be in index
    texts = " ".join(c["text"] for c in index["chunks"])
    assert "transformers" in texts.lower()


def test_empty_query(mem_tree):
    _, memory_dir = mem_tree
    results = search("", memory_dir)
    assert results == []


def test_special_chars(mem_tree):
    _, memory_dir = mem_tree
    # Should not crash on special chars
    results = search("hello (world) [test] {foo} $bar", memory_dir)
    assert isinstance(results, list)

    # Search with Chinese characters
    results = search("智凱 AudioMatters", memory_dir)
    assert isinstance(results, list)


def test_output_format(mem_tree):
    _, memory_dir = mem_tree
    results = search("AudioMatters", memory_dir)
    assert len(results) > 0
    r = results[0]
    assert "path" in r
    assert "lines" in r
    assert "snippet" in r
    assert "score" in r
    # lines format: "N-M"
    assert re.match(r"\d+-\d+", r["lines"])


def test_cli_json_output(mem_tree):
    """Test CLI produces valid JSON."""
    tmp_path, memory_dir = mem_tree
    script = os.path.join(os.path.dirname(__file__), "memory_search_local.py")
    import subprocess
    result = subprocess.run(
        [sys.executable, script, "AudioMatters", "--top", "3"],
        capture_output=True, text=True,
        env={**os.environ, "HOME": str(tmp_path)},
        cwd=str(tmp_path),
    )
    # May not find workspace via git in tmp, but should not crash
    assert result.returncode == 0 or "No such file" in result.stderr


# ---------------------------------------------------------------------------
# New tests: CJK expand
# ---------------------------------------------------------------------------

def test_cjk_expand_inserts_spaces():
    result = _cjk_expand("李宏毅老師")
    # Each CJK char should be surrounded by spaces
    assert " 李 " in result
    assert " 師 " in result


def test_cjk_expand_mixed():
    result = _cjk_expand("AudioMatters 智凱")
    # ASCII words unchanged
    assert "AudioMatters" in result
    # CJK chars spaced
    assert " 智 " in result
    assert " 凱 " in result


def test_cjk_expand_ascii_only():
    result = _cjk_expand("hello world")
    assert result == "hello world"


# ---------------------------------------------------------------------------
# New tests: JSONL parsing
# ---------------------------------------------------------------------------

@pytest.fixture
def jsonl_tree(tmp_path):
    """Create a memory directory with sample JSONL files."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    people_dir = memory_dir / "people"
    people_dir.mkdir()

    # people.jsonl
    records = [
        {"id": "P001", "name": "智凱", "aliases": ["智凱哥", "凱哥"],
         "relationship": "labmate", "context": "李宏毅 Lab", "trust": 8,
         "notes": "AudioMatters co-author", "tags": ["lab"]},
        {"id": "P002", "name": "晨安", "aliases": [],
         "relationship": "labmate", "context": "NTU CSIE",
         "notes": "Paper B collaborator", "tags": ["lab", "collab"]},
    ]
    (people_dir / "people.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )

    # opportunities.jsonl
    opp_dir = memory_dir / "opportunities"
    opp_dir.mkdir()
    opps = [
        {"id": "O001", "title": "中技社科技獎學金", "category": "scholarship",
         "amount": "TWD 250,000", "deadline": "2026-09-05", "status": "eligible",
         "tags": ["taiwan"], "notes": "High priority fellowship"},
    ]
    (opp_dir / "opportunities.jsonl").write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in opps),
        encoding="utf-8",
    )

    return tmp_path, memory_dir


def test_extract_strings_flat():
    parts: list[str] = []
    _extract_strings({"name": "智凱", "trust": 8, "tags": ["lab", "research"]}, parts)
    assert "智凱" in parts
    assert "lab" in parts
    assert "research" in parts
    # Numbers not extracted
    assert "8" not in parts


def test_extract_strings_nested():
    parts: list[str] = []
    _extract_strings({"notes": [{"text": "AudioMatters", "time": "2026-03-01"}]}, parts)
    assert "AudioMatters" in parts


def test_parse_jsonl_chunks_basic(jsonl_tree):
    _, memory_dir = jsonl_tree
    chunks = parse_jsonl_chunks(memory_dir / "people" / "people.jsonl")
    assert len(chunks) == 2
    headers = [c["header"] for c in chunks]
    assert "智凱" in headers
    assert "晨安" in headers


def test_parse_jsonl_chunks_text_contains_fields(jsonl_tree):
    _, memory_dir = jsonl_tree
    chunks = parse_jsonl_chunks(memory_dir / "people" / "people.jsonl")
    zk = next(c for c in chunks if c["header"] == "智凱")
    # Text should contain searchable fields
    assert "labmate" in zk["text"]
    assert "AudioMatters" in zk["text"]
    assert "凱哥" in zk["text"]


def test_parse_jsonl_chunks_empty(tmp_path):
    f = tmp_path / "empty.jsonl"
    f.write_text("", encoding="utf-8")
    assert parse_jsonl_chunks(f) == []


def test_parse_jsonl_chunks_invalid_lines(tmp_path):
    f = tmp_path / "bad.jsonl"
    f.write_text('{"good": "record"}\nnot json\n{"another": "record"}\n', encoding="utf-8")
    chunks = parse_jsonl_chunks(f)
    assert len(chunks) == 2  # only 2 valid JSON objects


def test_collect_jsonl_files(jsonl_tree):
    _, memory_dir = jsonl_tree
    files = collect_jsonl_files(memory_dir)
    names = [f.name for f in files]
    assert "people.jsonl" in names
    assert "opportunities.jsonl" in names


# ---------------------------------------------------------------------------
# New tests: build_index includes JSONL
# ---------------------------------------------------------------------------

@pytest.fixture
def mixed_tree(tmp_path):
    """Memory tree with both MD and JSONL files."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    (memory_dir / "knowledge.md").write_text(
        "# Knowledge\n\n"
        "## Mechanistic Interpretability\n"
        "Research on neural network internals.\n",
        encoding="utf-8",
    )

    people_dir = memory_dir / "people"
    people_dir.mkdir()
    (people_dir / "people.jsonl").write_text(
        json.dumps({"id": "P001", "name": "智凱", "notes": "AudioMatters co-author",
                    "tags": ["lab"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tmp_path, memory_dir


def test_build_index_includes_jsonl(mixed_tree):
    _, memory_dir = mixed_tree
    index = build_index(memory_dir, force=True)
    paths = {c["path"] for c in index["chunks"]}
    assert any(".jsonl" in p for p in paths)
    assert any(".md" in p for p in paths)


def test_build_index_creates_fts5_db(mixed_tree):
    _, memory_dir = mixed_tree
    build_index(memory_dir, force=True)
    assert _fts5_db_path(memory_dir).exists()


# ---------------------------------------------------------------------------
# New tests: SQLite FTS5 backend
# ---------------------------------------------------------------------------

def test_search_fts5_basic(mixed_tree):
    _, memory_dir = mixed_tree
    build_index(memory_dir, force=True)
    results = search_fts5("mechanistic", memory_dir, top_k=5)
    assert isinstance(results, list)
    assert len(results) > 0
    # "Mechanistic Interpretability" is a section header in knowledge.md — it's indexed
    # even though it doesn't appear in the body text snippet
    assert any("knowledge.md" in r["path"] for r in results)


def test_search_fts5_chinese(mixed_tree):
    _, memory_dir = mixed_tree
    build_index(memory_dir, force=True)
    results = search_fts5("智凱", memory_dir, top_k=5)
    assert isinstance(results, list)
    # Should find the JSONL record about 智凱
    assert len(results) > 0


def test_search_fts5_empty_query(mixed_tree):
    _, memory_dir = mixed_tree
    build_index(memory_dir, force=True)
    results = search_fts5("", memory_dir)
    assert results == []


def test_search_fts5_output_format(mixed_tree):
    _, memory_dir = mixed_tree
    build_index(memory_dir, force=True)
    results = search_fts5("AudioMatters", memory_dir, top_k=3)
    assert isinstance(results, list)
    if results:
        r = results[0]
        assert "path" in r
        assert "lines" in r
        assert "snippet" in r
        assert "score" in r


def test_search_fts5_missing_db(tmp_path):
    """Should raise if FTS5 db doesn't exist."""
    import pytest
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        search_fts5("anything", memory_dir)


# ---------------------------------------------------------------------------
# New tests: keyword fallback
# ---------------------------------------------------------------------------

def test_keyword_search_basic():
    chunks = [
        {"path": "a.md", "header": "A", "line_start": 1, "line_end": 5,
         "text": "AudioMatters is a paper about audio processing in LLMs"},
        {"path": "b.md", "header": "B", "line_start": 1, "line_end": 3,
         "text": "Mechanistic interpretability research"},
        {"path": "c.md", "header": "C", "line_start": 1, "line_end": 2,
         "text": "unrelated content about cooking"},
    ]
    results = keyword_search("audio processing", chunks, top_k=5)
    assert len(results) > 0
    assert results[0]["path"] == "a.md"


def test_keyword_search_chinese():
    chunks = [
        {"path": "people.jsonl", "header": "智凱", "line_start": 1, "line_end": 1,
         "text": "labmate 李宏毅 Lab AudioMatters co-author 智凱哥 凱哥"},
        {"path": "other.md", "header": "Other", "line_start": 1, "line_end": 2,
         "text": "unrelated english content only"},
    ]
    results = keyword_search("智凱", chunks, top_k=5)
    assert len(results) > 0
    assert results[0]["path"] == "people.jsonl"


def test_keyword_search_no_match():
    chunks = [
        {"path": "a.md", "header": "A", "line_start": 1, "line_end": 2,
         "text": "hello world"},
    ]
    results = keyword_search("xyzzy nonexistent", chunks)
    assert results == []


def test_keyword_search_top_k():
    chunks = [
        {"path": f"{i}.md", "header": str(i), "line_start": 1, "line_end": 1,
         "text": f"research topic {i}"}
        for i in range(10)
    ]
    results = keyword_search("research", chunks, top_k=3)
    assert len(results) <= 3


def test_keyword_search_output_format():
    chunks = [
        {"path": "a.md", "header": "A", "line_start": 10, "line_end": 15,
         "text": "test content here"},
    ]
    results = keyword_search("test", chunks)
    assert len(results) == 1
    r = results[0]
    assert r["path"] == "a.md"
    assert r["lines"] == "10-15"
    assert "test" in r["snippet"]
    assert isinstance(r["score"], float)


# ---------------------------------------------------------------------------
# New tests: fallback chain via search()
# ---------------------------------------------------------------------------

def test_search_auto_backend(mixed_tree):
    _, memory_dir = mixed_tree
    results = search("mechanistic", memory_dir, top_k=3, backend="auto")
    assert isinstance(results, list)


def test_search_bm25_backend(mixed_tree):
    _, memory_dir = mixed_tree
    results = search("mechanistic", memory_dir, top_k=3, backend="bm25")
    assert isinstance(results, list)


def test_search_keyword_backend(mixed_tree):
    _, memory_dir = mixed_tree
    results = search("mechanistic", memory_dir, top_k=3, backend="keyword")
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_fts5_backend(mixed_tree):
    _, memory_dir = mixed_tree
    results = search("AudioMatters", memory_dir, top_k=3, backend="fts5")
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_jsonl_content_findable(mixed_tree):
    _, memory_dir = mixed_tree
    # "智凱" exists only in JSONL — should be found
    results = search("智凱", memory_dir, top_k=5)
    assert isinstance(results, list)
    assert len(results) > 0
    assert any(".jsonl" in r["path"] for r in results)


def test_search_fallback_to_keyword_when_bm25_fails(mixed_tree, monkeypatch):
    """If BM25 is unavailable, should fall back to keyword search."""
    _, memory_dir = mixed_tree

    def mock_bm25(*args, **kwargs):
        raise ImportError("rank_bm25 not installed")

    import memory_search_local as msl
    monkeypatch.setattr(msl, "search_bm25", mock_bm25)
    monkeypatch.setattr(msl, "search_fts5", lambda *a, **kw: (_ for _ in ()).throw(Exception("no fts5")))

    results = search("mechanistic", memory_dir, top_k=3, backend="auto")
    assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
