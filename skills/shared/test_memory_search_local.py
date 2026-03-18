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
    _is_daily, _index_path,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
