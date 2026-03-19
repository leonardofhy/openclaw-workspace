# Task: Build Lightweight Memory Search (BM25)

The `memory_search` tool is currently disabled (requires external embedding API).
Build a fast, local, zero-dependency alternative using BM25 + keyword search.

## Context

Read these files first:
- `AGENTS.md` — how memory works, what files exist
- `MEMORY.md` — example of what's in memory
- `memory/knowledge.md` — another memory file
- `memory/anti-patterns.md` — another memory file
- `skills/leo-diary/scripts/search_diary.py` — see how diary search works (can borrow patterns)
- Check how many daily memory files exist: `ls memory/*.md | wc -l`

## What to Build

### `skills/shared/memory_search_local.py`

A local BM25 search engine over all memory/*.md files.

```
python3 memory_search_local.py "mechanistic interpretability speech"
python3 memory_search_local.py "Leo research deadline" --top 5
python3 memory_search_local.py "AudioMatters" --include-daily
python3 memory_search_local.py --rebuild-index   # force rebuild
python3 memory_search_local.py --stats           # index stats
```

**Architecture:**

1. **Index builder** (`build_index()`):
   - Scan: `MEMORY.md`, `memory/*.md` (optionally daily `YYYY-MM-DD.md`)
   - Parse each file into chunks (by `##` header sections)
   - Build inverted index: `{term: [(doc_id, chunk_id, tf), ...]}`
   - Cache index to `memory/.search_index.json` (rebuild if files newer than index)
   - Fast: should index ~100 files in < 2 seconds

2. **BM25 scorer** (`search(query, top_k=5, include_daily=False)`):
   - Use `rank_bm25` package (already installed: `from rank_bm25 import BM25Okapi`)
   - Tokenize query + docs: lowercase, split on whitespace/punctuation, remove stopwords
   - Return: `[{path, line_start, snippet, score}, ...]`
   - snippet = 3-4 lines around the best matching chunk

3. **Output format** (matches memory_search tool contract):
   ```json
   [
     {
       "path": "memory/2026-03-18.md",
       "lines": "45-48",
       "snippet": "...",
       "score": 12.4
     }
   ]
   ```

4. **Index invalidation**: compare file mtimes vs index timestamp; rebuild if any file newer

### `skills/shared/test_memory_search_local.py`

Tests:
- test_index_builds: index created from temp markdown files
- test_basic_search: "mechanistic" finds relevant chunk
- test_bm25_ranking: more matching terms → higher score
- test_top_k: returns exactly k results
- test_include_daily: daily files included when flag set
- test_cache_invalidation: modified file triggers rebuild
- test_empty_query: returns empty gracefully
- test_special_chars: handles punctuation in query

### Integration Note

After building, update `memory_search` calls to use this as fallback:
In `AGENTS.md` under Memory section, add:
> "If `memory_search` tool returns `disabled=true`, fall back to:
> `python3 skills/shared/memory_search_local.py '<query>' --top 5`"

Do NOT modify the actual `memory_search` tool (it's OpenClaw-internal).
Just build the local alternative and document it.

## Constraints
- Use `rank_bm25` (BM25Okapi) — already installed, do NOT reinvent BM25 from scratch
- No other non-stdlib dependencies (no numpy, no sklearn, no NLTK)
- Must handle unicode (Chinese characters in memory files)
- Index file must be human-readable JSON (not pickle)
- Should work from any cwd (uses find_workspace() to locate memory/)
