#!/usr/bin/env python3
"""Knowledge graph keyword search tool.

Searches across memory/learning/knowledge-graph.md AND memory/learning/kg/*.md
using case-insensitive keyword matching. Results are printed to stdout with
source file attribution.

Usage:
    python3 kg_query.py --query 'AND-gate'
    python3 kg_query.py --query 'RAVEL' --context 5
    python3 kg_query.py --query 'sparse autoencoder' --json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from jsonl_store import find_workspace


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


def _make_match(source: str, heading: str | None, line_num: int, lines: list[str]) -> dict[str, Any]:
    """Build a match record for a single hit."""
    return {
        "source": source,
        "heading": heading,
        "line": line_num,
        "lines": lines,
    }


# ---------------------------------------------------------------------------
# knowledge-graph.md search — section-aware
# ---------------------------------------------------------------------------


def _search_knowledge_graph(kg_path: Path, query: str, context_lines: int) -> list[dict[str, Any]]:
    """Search knowledge-graph.md by splitting on ## headings.

    Returns one result per matching section, with up to ``context_lines``
    lines of context around each match within that section.
    """
    if not kg_path.exists():
        return []

    raw = kg_path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    # Split into sections on ## or ### headings (keep the delimiter).
    section_split = re.split(r"(?m)^(#{1,6} .+)$", raw)

    results: list[dict[str, Any]] = []
    rel_source = str(kg_path)

    # section_split alternates: [text_before_first_heading, heading, body, heading, body, ...]
    heading: str | None = None
    pending_text = section_split[0]

    chunks: list[tuple[str | None, str]] = [(None, pending_text)]
    i = 1
    while i < len(section_split) - 1:
        chunks.append((section_split[i], section_split[i + 1]))
        i += 2

    global_line = 1  # 1-indexed line counter across the full file

    for section_heading, body in chunks:
        section_lines = body.splitlines(keepends=False)
        if section_heading:
            heading_line_count = 1
        else:
            heading_line_count = 0

        match_line_indices: list[int] = []
        for idx, line in enumerate(section_lines):
            if pattern.search(line) or (section_heading and pattern.search(section_heading)):
                if pattern.search(line):
                    match_line_indices.append(idx)

        # Also match on heading itself — include first few lines of body.
        if section_heading and pattern.search(section_heading) and not match_line_indices:
            match_line_indices = list(range(min(context_lines, len(section_lines))))

        if match_line_indices:
            # Collect a window around each match, deduplicated and sorted.
            covered: set[int] = set()
            windows: list[tuple[int, int]] = []
            for mi in sorted(match_line_indices):
                start = max(0, mi - context_lines)
                end = min(len(section_lines), mi + context_lines + 1)
                windows.append((start, end))

            # Merge overlapping windows.
            merged: list[tuple[int, int]] = []
            for start, end in sorted(windows):
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))

            for start, end in merged:
                excerpt = section_lines[start:end]
                abs_line = global_line + heading_line_count + start + 1
                results.append(
                    _make_match(
                        source=rel_source,
                        heading=section_heading,
                        line_num=abs_line,
                        lines=excerpt,
                    )
                )

        global_line += heading_line_count + len(section_lines)

    return results


# ---------------------------------------------------------------------------
# kg/*.md search — file-level, with line context
# ---------------------------------------------------------------------------


def _search_kg_files(kg_dir: Path, query: str, context_lines: int) -> list[dict[str, Any]]:
    """Search all *.md files in the kg/ directory.

    Returns results grouped by file; within each file matches are shown with
    ``context_lines`` lines of surrounding context.
    """
    if not kg_dir.is_dir():
        return []

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    results: list[dict[str, Any]] = []

    for md_file in sorted(kg_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        file_lines = md_file.read_text(encoding="utf-8").splitlines(keepends=False)
        match_indices = [i for i, ln in enumerate(file_lines) if pattern.search(ln)]

        if not match_indices:
            continue

        # Merge context windows.
        windows: list[tuple[int, int]] = [
            (max(0, mi - context_lines), min(len(file_lines), mi + context_lines + 1))
            for mi in match_indices
        ]
        merged: list[tuple[int, int]] = []
        for start, end in sorted(windows):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        for start, end in merged:
            results.append(
                _make_match(
                    source=str(md_file),
                    heading=None,
                    line_num=start + 1,
                    lines=file_lines[start:end],
                )
            )

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _format_human(results: list[dict[str, Any]], query: str) -> str:
    """Render results as readable plain text."""
    if not results:
        return f"No results found for: {query!r}"

    parts: list[str] = [f"Search results for: {query!r}  ({len(results)} match(es))\n"]
    parts.append("=" * 70)

    for r in results:
        source_label = r["source"]
        heading_label = f"  [{r['heading']}]" if r["heading"] else ""
        parts.append(f"\nSource: {source_label}{heading_label}  (line {r['line']})")
        parts.append("-" * 60)
        for line in r["lines"]:
            parts.append(line)
        parts.append("")

    return "\n".join(parts)


def _format_json(results: list[dict[str, Any]], query: str) -> str:
    """Render results as JSON."""
    payload = {
        "query": query,
        "total_matches": len(results),
        "results": results,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and run the search."""
    parser = argparse.ArgumentParser(
        description="Keyword search across the Autodidact knowledge graph.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search term (case-insensitive).",
    )
    parser.add_argument(
        "--context", "-c",
        type=int,
        default=3,
        metavar="N",
        help="Lines of context around each match (default: 3).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as machine-readable JSON.",
    )
    args = parser.parse_args()

    workspace = find_workspace()
    kg_main = workspace / "memory" / "learning" / "knowledge-graph.md"
    kg_dir = workspace / "memory" / "learning" / "kg"

    results: list[dict[str, Any]] = []
    results.extend(_search_knowledge_graph(kg_main, args.query, args.context))
    results.extend(_search_kg_files(kg_dir, args.query, args.context))

    if args.json_output:
        print(_format_json(results, args.query))
    else:
        print(_format_human(results, args.query))

    # Exit code: 1 if no results (grep convention).
    sys.exit(0 if results else 1)


if __name__ == "__main__":
    main()
