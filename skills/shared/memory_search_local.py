#!/usr/bin/env python3
"""
Local memory search with multiple backends.

Backends (in fallback order):
  1. SQLite FTS5  — zero-dependency, persistent, fast, handles CJK
  2. BM25         — rank_bm25 package, probabilistic ranking
  3. Keyword      — simple term matching, always available

Searches both .md and .jsonl files in memory/.

Usage:
  python3 memory_search_local.py "mechanistic interpretability"
  python3 memory_search_local.py "Leo research deadline" --top 5
  python3 memory_search_local.py "AudioMatters" --include-daily
  python3 memory_search_local.py --rebuild-index
  python3 memory_search_local.py --stats
  python3 memory_search_local.py "query" --backend bm25
"""
import sys
import os
import re
import json
import sqlite3
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
_CJK_RE = re.compile(r"([\u4e00-\u9fff\u3400-\u4dbf\uff00-\uffef])")


def tokenize(text: str) -> list[str]:
    """Lowercase, split on whitespace/punctuation, remove stopwords."""
    tokens = _SPLIT_RE.findall(text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def _cjk_expand(text: str) -> str:
    """Add spaces between CJK characters for character-level FTS5 tokenization."""
    return _CJK_RE.sub(r" \1 ", text)


def _fts5_tokens(query: str) -> list[str]:
    """Extract FTS5 query tokens — like tokenize() but allows single CJK chars."""
    expanded = _cjk_expand(query)
    tokens = _SPLIT_RE.findall(expanded.lower())
    result = []
    for t in tokens:
        if t in STOPWORDS:
            continue
        # Single CJK characters are meaningful; filter single ASCII/digit chars
        is_cjk = bool(_CJK_RE.match(t))
        if len(t) > 1 or is_cjk:
            result.append(t)
    return result


# ---------------------------------------------------------------------------
# Chunk parser — Markdown
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
# Chunk parser — JSONL
# ---------------------------------------------------------------------------

def _extract_strings(value, parts: list[str]) -> None:
    """Recursively extract all string values from a JSON value."""
    if isinstance(value, str) and value.strip():
        parts.append(value.strip())
    elif isinstance(value, list):
        for item in value:
            _extract_strings(item, parts)
    elif isinstance(value, dict):
        for v in value.values():
            _extract_strings(v, parts)


def parse_jsonl_chunks(filepath: Path) -> list[dict]:
    """Parse a JSONL file into searchable chunks (one chunk per record)."""
    try:
        raw = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    chunks = []
    for line_num, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue

        parts: list[str] = []
        _extract_strings(record, parts)
        text = " ".join(parts)
        if not text.strip():
            continue

        # Use meaningful field as header
        header = str(
            record.get("name") or record.get("title") or
            record.get("id") or f"record-{line_num}"
        )

        chunks.append({
            "path": str(filepath),
            "header": header,
            "line_start": line_num,
            "line_end": line_num,
            "text": text[:500],
        })

    return chunks


# ---------------------------------------------------------------------------
# Index build / cache
# ---------------------------------------------------------------------------

def collect_files(memory_dir: Path, include_daily: bool = False) -> list[Path]:
    """Collect markdown files from memory/ (excludes daily unless requested)."""
    files = []
    mem_md = memory_dir.parent / "MEMORY.md"
    if mem_md.exists():
        files.append(mem_md)

    for root, _dirs, fnames in os.walk(memory_dir):
        for fname in fnames:
            if not fname.endswith(".md"):
                continue
            p = Path(root) / fname
            if not include_daily and _is_daily(p):
                continue
            files.append(p)

    return sorted(files)


def collect_jsonl_files(memory_dir: Path) -> list[Path]:
    """Collect all JSONL files from memory/."""
    files = []
    for root, _dirs, fnames in os.walk(memory_dir):
        for fname in fnames:
            if fname.endswith(".jsonl"):
                files.append(Path(root) / fname)
    return sorted(files)


def _index_path(memory_dir: Path) -> Path:
    return memory_dir / ".search_index.json"


def _fts5_db_path(memory_dir: Path) -> Path:
    return memory_dir / ".search_fts5.db"


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

    all_files = (
        collect_files(memory_dir, include_daily) +
        collect_jsonl_files(memory_dir)
    )
    for f in all_files:
        if f.stat().st_mtime > idx_mtime:
            return True
    return False


def build_index(memory_dir: Path, include_daily: bool = False, force: bool = False) -> dict:
    """Build or load cached index (JSON + FTS5). Returns index metadata dict."""
    idx_file = _index_path(memory_dir)
    fts5_db = _fts5_db_path(memory_dir)

    needs_json = force or _needs_rebuild(memory_dir, include_daily)
    needs_fts5 = needs_json or not fts5_db.exists()

    if not needs_json:
        index_data = json.loads(idx_file.read_text(encoding="utf-8"))
    else:
        md_files = collect_files(memory_dir, include_daily)
        jsonl_files = collect_jsonl_files(memory_dir)
        all_chunks: list[dict] = []

        for f in md_files:
            all_chunks.extend(parse_chunks(f))
        for f in jsonl_files:
            all_chunks.extend(parse_jsonl_chunks(f))

        # Include header text so header terms are findable (e.g. "## Mechanistic Interpretability")
        tokenized = [tokenize(c.get("header", "") + " " + c["text"]) for c in all_chunks]

        index_data = {
            "include_daily": include_daily,
            "num_files": len(md_files) + len(jsonl_files),
            "num_chunks": len(all_chunks),
            "chunks": [
                {
                    "path": c["path"],
                    "header": c.get("header", ""),
                    "line_start": c["line_start"],
                    "line_end": c["line_end"],
                    "text": c["text"][:500],
                }
                for c in all_chunks
            ],
            "corpus": tokenized,
        }

        try:
            idx_file.write_text(json.dumps(index_data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    if needs_fts5:
        try:
            _build_fts5(fts5_db, index_data["chunks"], include_daily)
        except Exception:
            pass  # FTS5 failure is non-fatal

    return index_data


# ---------------------------------------------------------------------------
# SQLite FTS5 backend
# ---------------------------------------------------------------------------

def _build_fts5(db_path: Path, chunks: list[dict], include_daily: bool) -> None:
    """Build SQLite FTS5 index from chunk list."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DROP TABLE IF EXISTS chunks")
        conn.execute("DROP TABLE IF EXISTS meta")
        # unicode61 handles CJK by treating each char as a token when we pre-expand
        conn.execute("""
            CREATE VIRTUAL TABLE chunks USING fts5(
                chunk_id UNINDEXED,
                path UNINDEXED,
                header UNINDEXED,
                line_start UNINDEXED,
                line_end UNINDEXED,
                display_text UNINDEXED,
                text,
                tokenize='unicode61 remove_diacritics 1'
            )
        """)
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        rows = []
        for i, c in enumerate(chunks):
            # Include header + text so header terms are searchable
            full_text = c.get("header", "") + " " + c["text"]
            expanded = _cjk_expand(full_text)
            rows.append((
                i,
                c["path"],
                c.get("header", ""),
                c.get("line_start", 0),
                c.get("line_end", 0),
                c["text"],
                expanded,
            ))
        conn.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?,?)", rows)
        conn.execute("INSERT INTO meta VALUES ('include_daily', ?)", (str(include_daily),))
        conn.commit()
    finally:
        conn.close()


def search_fts5(query: str, memory_dir: Path, top_k: int = 5) -> list[dict]:
    """Search using SQLite FTS5. Raises if unavailable."""
    db_path = _fts5_db_path(memory_dir)
    if not db_path.exists():
        raise FileNotFoundError("FTS5 index not built")

    # Use _fts5_tokens (not tokenize) to preserve single CJK chars after expansion
    tokens = _fts5_tokens(query)
    if not tokens:
        return []

    # Use OR so partial matches rank via FTS5's internal BM25 (same as rank_bm25 behavior)
    fts_query = " OR ".join(tokens)

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            """SELECT path, header, line_start, line_end, display_text, rank
               FROM chunks WHERE text MATCH ? ORDER BY rank LIMIT ?""",
            (fts_query, top_k),
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        raise
    conn.close()

    results = []
    for path, header, line_start, line_end, text, rank in rows:
        text_lines = text.split("\n")
        snippet = "\n".join(text_lines[:4]).strip()
        if len(text_lines) > 4:
            snippet += "\n..."
        results.append({
            "path": path,
            "lines": f"{line_start}-{line_end}",
            "snippet": snippet,
            "score": round(abs(float(rank)), 4),
        })
    return results


# ---------------------------------------------------------------------------
# BM25 backend
# ---------------------------------------------------------------------------

def search_bm25(query: str, index: dict, top_k: int = 5) -> list[dict]:
    """Search using BM25 (rank_bm25 package). Raises ImportError if unavailable."""
    from rank_bm25 import BM25Okapi

    chunks = index["chunks"]
    corpus = index["corpus"]
    if not corpus:
        return []

    bm25 = BM25Okapi(corpus)
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    results = []
    for idx, score in ranked[:top_k]:
        if score <= 0:
            break
        c = chunks[idx]
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


# ---------------------------------------------------------------------------
# Keyword fallback backend
# ---------------------------------------------------------------------------

def keyword_search(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Simple substring keyword search — always available, no dependencies."""
    query_lower = query.lower()
    terms = [t for t in re.split(r"\s+", query_lower) if t]
    if not terms:
        return []

    scored: list[tuple[int, dict]] = []
    for c in chunks:
        # Search both header and body for consistency with BM25/FTS5
        searchable = (c.get("header", "") + " " + c["text"]).lower()
        match_count = sum(1 for t in terms if t in searchable)
        if match_count > 0:
            scored.append((match_count, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, c in scored[:top_k]:
        text_lines = c["text"].split("\n")
        snippet = "\n".join(text_lines[:4]).strip()
        if len(text_lines) > 4:
            snippet += "\n..."
        results.append({
            "path": c["path"],
            "lines": f"{c['line_start']}-{c['line_end']}",
            "snippet": snippet,
            "score": float(score),
        })
    return results


# ---------------------------------------------------------------------------
# Unified search with fallback chain
# ---------------------------------------------------------------------------

def search(
    query: str,
    memory_dir: Path,
    top_k: int = 5,
    include_daily: bool = False,
    force_rebuild: bool = False,
    backend: str = "auto",
) -> list[dict]:
    """Search memory chunks. Fallback order: FTS5 → BM25 → keyword.

    Args:
        backend: "auto" | "fts5" | "bm25" | "keyword"
    """
    if not query.strip():
        return []

    index = build_index(memory_dir, include_daily, force=force_rebuild)
    chunks = index["chunks"]
    if not chunks:
        return []

    order = {
        "auto": ["fts5", "bm25", "keyword"],
        "fts5": ["fts5"],
        "bm25": ["bm25"],
        "keyword": ["keyword"],
    }.get(backend, ["fts5", "bm25", "keyword"])

    for b in order:
        try:
            if b == "fts5":
                results = search_fts5(query, memory_dir, top_k)
                return results
            elif b == "bm25":
                results = search_bm25(query, index, top_k)
                return results
            elif b == "keyword":
                return keyword_search(query, chunks, top_k)
        except Exception:
            continue  # try next backend

    return []


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(memory_dir: Path, include_daily: bool = False) -> None:
    """Print index statistics."""
    index = build_index(memory_dir, include_daily)
    print(f"Files indexed:            {index['num_files']}")
    print(f"Chunks:                   {index['num_chunks']}")
    print(f"Include daily:            {index['include_daily']}")

    paths = {c["path"] for c in index["chunks"]}
    md_paths = [p for p in paths if p.endswith(".md")]
    jsonl_paths = [p for p in paths if p.endswith(".jsonl")]
    print(f"Markdown files with chunks: {len(md_paths)}")
    print(f"JSONL files with chunks:  {len(jsonl_paths)}")

    vocab: set[str] = set()
    for tokens in index["corpus"]:
        vocab.update(tokens)
    print(f"Vocabulary size:          {len(vocab)}")

    idx_file = _index_path(memory_dir)
    if idx_file.exists():
        size_kb = idx_file.stat().st_size / 1024
        print(f"JSON cache:               {idx_file} ({size_kb:.1f} KB)")

    fts5_db = _fts5_db_path(memory_dir)
    if fts5_db.exists():
        size_kb = fts5_db.stat().st_size / 1024
        print(f"FTS5 database:            {fts5_db} ({size_kb:.1f} KB)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Local memory search (FTS5/BM25/keyword)")
    parser.add_argument("query", nargs="*", help="Search query")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--include-daily", action="store_true",
                        help="Include daily YYYY-MM-DD.md files")
    parser.add_argument("--rebuild-index", action="store_true", help="Force index rebuild")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--json", action="store_true", help="JSON output (default)")
    parser.add_argument("--backend", default="auto",
                        choices=["auto", "fts5", "bm25", "keyword"],
                        help="Search backend (default: auto)")
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
        backend=args.backend,
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
