#!/usr/bin/env python3
"""
Local BM25 memory search over memory/*.md files.

Usage:
  python3 memory_search_local.py "mechanistic interpretability"
  python3 memory_search_local.py "Leo research deadline" --top 5
  python3 memory_search_local.py "AudioMatters" --include-daily
  python3 memory_search_local.py --rebuild-index
  python3 memory_search_local.py --stats
"""
import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Workspace discovery
# ---------------------------------------------------------------------------

def find_workspace() -> Path:
    """Find workspace root via git or fallback to known path."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.home() / ".openclaw" / "workspace"


# ---------------------------------------------------------------------------
# Tokenizer & stopwords
# ---------------------------------------------------------------------------

STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his i if in into is "
    "it its just me my no nor not of on or our she so than that the their them "
    "then there these they this to too up us was we were what when where which "
    "who why will with you your 的 了 是 在 我 有 和 就 不 人 都 一 這 上 也 "
    "個 到 說 們 為 子 你 來 他 她 它 要 會 可以 沒有 很 過 對 而 但 還 把 被 從 "
    "那 之 與 嗎 吧 啊 呢".split()
)

_SPLIT_RE = re.compile(r"[\w\u4e00-\u9fff\u3400-\u4dbf]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase, split on whitespace/punctuation, remove stopwords."""
    tokens = _SPLIT_RE.findall(text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


# ---------------------------------------------------------------------------
# Chunk parser
# ---------------------------------------------------------------------------

DAILY_RE = re.compile(r"\d{4}-\d{2}-\d{2}\.md$")


def _is_daily(path: Path) -> bool:
    return bool(DAILY_RE.match(path.name))


def parse_chunks(filepath: Path) -> list[dict]:
    """Split a markdown file into chunks by ## headers."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if not text.strip():
        return []

    lines = text.split("\n")
    chunks = []
    current_header = filepath.name
    current_lines: list[str] = []
    start_line = 1

    for i, line in enumerate(lines, 1):
        if line.startswith("## "):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    chunks.append({
                        "path": str(filepath),
                        "header": current_header,
                        "line_start": start_line,
                        "line_end": i - 1,
                        "text": body,
                    })
            current_header = line.lstrip("# ").strip()
            current_lines = []
            start_line = i
        else:
            current_lines.append(line)

    # Last chunk
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append({
                "path": str(filepath),
                "header": current_header,
                "line_start": start_line,
                "line_end": len(lines),
                "text": body,
            })

    return chunks


# ---------------------------------------------------------------------------
# Index build / cache
# ---------------------------------------------------------------------------

def collect_files(memory_dir: Path, include_daily: bool = False) -> list[Path]:
    """Collect markdown files from memory/."""
    files = []
    # Top-level MEMORY.md
    mem_md = memory_dir.parent / "MEMORY.md"
    if mem_md.exists():
        files.append(mem_md)

    # Walk memory/ recursively
    for root, _dirs, fnames in os.walk(memory_dir):
        for fname in fnames:
            if not fname.endswith(".md"):
                continue
            p = Path(root) / fname
            if not include_daily and _is_daily(p):
                continue
            files.append(p)

    return sorted(files)


def _index_path(memory_dir: Path) -> Path:
    return memory_dir / ".search_index.json"


def _needs_rebuild(memory_dir: Path, include_daily: bool) -> bool:
    idx_file = _index_path(memory_dir)
    if not idx_file.exists():
        return True
    try:
        idx_mtime = idx_file.stat().st_mtime
        meta = json.loads(idx_file.read_text(encoding="utf-8"))
        if meta.get("include_daily") != include_daily:
            return True
    except (OSError, json.JSONDecodeError, KeyError):
        return True

    for f in collect_files(memory_dir, include_daily):
        if f.stat().st_mtime > idx_mtime:
            return True
    return False


def build_index(memory_dir: Path, include_daily: bool = False, force: bool = False) -> dict:
    """Build or load cached BM25 index. Returns index metadata dict."""
    idx_file = _index_path(memory_dir)

    if not force and not _needs_rebuild(memory_dir, include_daily):
        return json.loads(idx_file.read_text(encoding="utf-8"))

    files = collect_files(memory_dir, include_daily)
    all_chunks = []
    for f in files:
        all_chunks.extend(parse_chunks(f))

    # Tokenize each chunk
    tokenized = [tokenize(c["text"]) for c in all_chunks]

    # Store index: chunks + tokenized corpus for BM25
    index_data = {
        "include_daily": include_daily,
        "num_files": len(files),
        "num_chunks": len(all_chunks),
        "chunks": [
            {
                "path": c["path"],
                "header": c["header"],
                "line_start": c["line_start"],
                "line_end": c["line_end"],
                "text": c["text"][:500],  # truncate for cache size
            }
            for c in all_chunks
        ],
        "corpus": tokenized,
    }

    try:
        idx_file.write_text(json.dumps(index_data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # non-fatal: just can't cache

    return index_data


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(
    query: str,
    memory_dir: Path,
    top_k: int = 5,
    include_daily: bool = False,
    force_rebuild: bool = False,
) -> list[dict]:
    """BM25 search over memory chunks. Returns list of results."""
    from rank_bm25 import BM25Okapi

    if not query.strip():
        return []

    index = build_index(memory_dir, include_daily, force=force_rebuild)
    chunks = index["chunks"]
    corpus = index["corpus"]

    if not corpus:
        return []

    bm25 = BM25Okapi(corpus)
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)

    # Rank and take top_k
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    results = []
    for idx, score in ranked[:top_k]:
        if score <= 0:
            break
        c = chunks[idx]
        # Build snippet: first 3-4 lines of chunk text
        text_lines = c["text"].split("\n")
        snippet = "\n".join(text_lines[:4]).strip()
        if len(text_lines) > 4:
            snippet += "\n..."

        results.append({
            "path": c["path"],
            "lines": f"{c['line_start']}-{c['line_end']}",
            "snippet": snippet,
            "score": round(float(score), 2),
        })

    return results


def print_stats(memory_dir: Path, include_daily: bool = False) -> None:
    """Print index statistics."""
    index = build_index(memory_dir, include_daily)
    print(f"Files indexed: {index['num_files']}")
    print(f"Chunks: {index['num_chunks']}")
    print(f"Include daily: {index['include_daily']}")

    # Unique paths
    paths = {c["path"] for c in index["chunks"]}
    print(f"Unique files with chunks: {len(paths)}")

    # Vocab size
    vocab: set[str] = set()
    for tokens in index["corpus"]:
        vocab.update(tokens)
    print(f"Vocabulary size: {len(vocab)}")

    idx_file = _index_path(memory_dir)
    if idx_file.exists():
        size_kb = idx_file.stat().st_size / 1024
        print(f"Cache file: {idx_file} ({size_kb:.1f} KB)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Local BM25 memory search")
    parser.add_argument("query", nargs="*", help="Search query")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--include-daily", action="store_true",
                        help="Include daily YYYY-MM-DD.md files")
    parser.add_argument("--rebuild-index", action="store_true", help="Force index rebuild")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--json", action="store_true", help="JSON output (default)")
    args = parser.parse_args()

    workspace = find_workspace()
    memory_dir = workspace / "memory"

    if args.stats:
        print_stats(memory_dir, include_daily=args.include_daily)
        return

    if args.rebuild_index:
        build_index(memory_dir, include_daily=args.include_daily, force=True)
        print("Index rebuilt.")
        if not args.query:
            return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    query = " ".join(args.query)
    results = search(
        query=query,
        memory_dir=memory_dir,
        top_k=args.top,
        include_daily=args.include_daily,
        force_rebuild=args.rebuild_index,
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
