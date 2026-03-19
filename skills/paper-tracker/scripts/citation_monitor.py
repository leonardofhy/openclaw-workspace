#!/usr/bin/env python3
"""Citation monitoring for tracked arXiv papers.

Tracks citations for papers in knowledge-graph.md using the Semantic Scholar API.
Compares against last check state in memory/papers/citation-state.json.

Usage:
    citation_monitor.py check [--since YYYY-MM-DD] [--authors 'Name1,Name2']
    citation_monitor.py report
    citation_monitor.py reset
    citation_monitor.py trending

Storage:
    memory/papers/citation-state.json     # last check state
    memory/learning/knowledge-graph.md    # source of tracked papers
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _find_workspace() -> Path:
    import subprocess
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.home() / ".openclaw" / "workspace"

WORKSPACE = _find_workspace()
STATE_PATH = WORKSPACE / "memory" / "papers" / "citation-state.json"
KNOWLEDGE_GRAPH_PATH = WORKSPACE / "memory" / "learning" / "knowledge-graph.md"
TZ_TAIPEI = timezone(timedelta(hours=8))

S2_API = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS_PAPER = "title,authors,year,externalIds,citationCount,url"
S2_FIELDS_CITATIONS = "title,authors,year,externalIds,url"
REQUEST_DELAY = 1.1  # seconds between API calls (respect rate limit)

# arXiv ID regex pattern for knowledge graph extraction
ARXIV_ID_PATTERN = re.compile(r"arXiv:([0-9]{4}\.[0-9]{4,5})(?:v\d+)?")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_taipei() -> str:
    return datetime.now(TZ_TAIPEI).isoformat(timespec="seconds")


def extract_arxiv_papers() -> list[dict]:
    """Extract arXiv papers from knowledge-graph.md."""
    if not KNOWLEDGE_GRAPH_PATH.exists():
        print(f"Warning: Knowledge graph not found at {KNOWLEDGE_GRAPH_PATH}")
        return []

    content = KNOWLEDGE_GRAPH_PATH.read_text()
    papers = []

    for match in ARXIV_ID_PATTERN.finditer(content):
        arxiv_id = match.group(1)

        # Extract title and context from the line
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_end = content.find("\n", match.end())
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]

        # Extract title (between quotes or after "—")
        title = ""
        title_match = re.search(r'"([^"]+)"', line)
        if title_match:
            title = title_match.group(1)
        else:
            # Try to extract from pattern like "AuthorName et al. ... — title"
            dash_match = re.search(r'—\s*([^[]+)', line)
            if dash_match:
                title = dash_match.group(1).strip()

        # Extract authors (crude extraction)
        authors = []
        author_match = re.search(r'\*\*([^*]+(?:et al\.)?)', line)
        if author_match:
            author_text = author_match.group(1)
            # Simple author extraction
            if "et al" in author_text:
                authors.append(author_text.replace("et al.", "").strip())
            else:
                authors.append(author_text.strip())

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "line": line.strip()
        })

    return papers


def load_state() -> dict:
    """Load citation-state.json or return empty state."""
    if not STATE_PATH.exists():
        return {
            "last_check": None,
            "known_citations": {},   # arxiv_id -> [citing_paper_id, ...]
            "known_author_papers": {},  # author_name -> [paper_id, ...]
        }
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def s2_get(endpoint: str, params: dict | None = None) -> dict | None:
    """Make a GET request to the Semantic Scholar API."""
    url = f"{S2_API}/{endpoint}"
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "openclaw-citation-monitor/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  API error for {endpoint}: {e}", file=sys.stderr)
        return None


def s2_paper_id(arxiv_id: str) -> str:
    """Build Semantic Scholar paper identifier from arxiv ID."""
    return f"ARXIV:{arxiv_id}"


# ---------------------------------------------------------------------------
# Core: check citations for a paper
# ---------------------------------------------------------------------------

def check_citations(arxiv_id: str, since: str | None = None) -> list[dict]:
    """Get citations of a paper, optionally filtered by year from --since."""
    paper_id = s2_paper_id(arxiv_id)
    result = s2_get(f"paper/{paper_id}/citations", {
        "fields": S2_FIELDS_CITATIONS,
        "limit": 100,
    })
    if not result or "data" not in result:
        return []

    citations = []
    since_year = int(since[:4]) if since else 0
    for item in result["data"]:
        citing = item.get("citingPaper", {})
        if not citing.get("title"):
            continue
        year = citing.get("year") or 0
        if since_year and year < since_year:
            continue
        citations.append({
            "s2_id": citing.get("paperId", ""),
            "title": citing.get("title", ""),
            "authors": [a.get("name", "") for a in citing.get("authors", [])],
            "year": year,
            "arxiv_id": (citing.get("externalIds") or {}).get("ArXiv", ""),
            "url": citing.get("url", ""),
        })
    return citations


# ---------------------------------------------------------------------------
# Core: check papers by author
# ---------------------------------------------------------------------------

def check_author_papers(author_name: str, since: str | None = None) -> list[dict]:
    """Search for recent papers by an author."""
    # First, find the author ID
    search_result = s2_get("author/search", {"query": author_name, "limit": 1})
    if not search_result or not search_result.get("data"):
        return []

    author_id = search_result["data"][0].get("authorId")
    if not author_id:
        return []

    time.sleep(REQUEST_DELAY)

    # Get their papers
    result = s2_get(f"author/{author_id}/papers", {
        "fields": S2_FIELDS_PAPER,
        "limit": 50,
    })
    if not result or "data" not in result:
        return []

    since_year = int(since[:4]) if since else 0
    papers = []
    for item in result["data"]:
        year = item.get("year") or 0
        if since_year and year < since_year:
            continue
        papers.append({
            "s2_id": item.get("paperId", ""),
            "title": item.get("title", ""),
            "authors": [a.get("name", "") for a in item.get("authors", [])],
            "year": year,
            "arxiv_id": (item.get("externalIds") or {}).get("ArXiv", ""),
            "url": item.get("url", ""),
            "citation_count": item.get("citationCount", 0),
        })
    return papers


def fetch_trending_papers(query: str = "speech interpretability machine learning", limit: int = 10) -> list[dict]:
    """Fetch trending papers related to a search query."""
    import urllib.parse
    encoded_query = urllib.parse.quote(query)

    result = s2_get("paper/search", {
        "query": encoded_query,
        "limit": limit,
        "fields": S2_FIELDS_PAPER,
    })

    if not result or "data" not in result:
        return []

    # Sort by recent + high citation count (trending score)
    papers = result["data"]
    current_year = datetime.now().year

    for paper in papers:
        year = paper.get("year", 0) or current_year
        citations = paper.get("citationCount", 0)
        # Trending score: citations weighted by recency
        recency_factor = 1 + max(0, current_year - year) * 0.1
        paper["trending_score"] = citations / recency_factor if recency_factor > 0 else citations

    return sorted(papers, key=lambda p: p.get("trending_score", 0), reverse=True)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_check(args):
    """Check for new citations and author papers."""
    state = load_state()
    since = args.since or state.get("last_check")

    # Extract papers from knowledge graph
    print("Extracting arXiv papers from knowledge graph...")
    tracked = extract_arxiv_papers()
    if not tracked:
        print("No arXiv papers found in knowledge graph.")
        return 0

    print(f"Found {len(tracked)} arXiv papers.")

    # Apply author filter if specified
    if args.authors:
        author_filter = [name.strip().lower() for name in args.authors.split(",") if name.strip()]
        print(f"Filtering papers by authors: {', '.join(author_filter)}")
        filtered_papers = []
        for paper in tracked:
            if any(author.lower() in " ".join(paper["authors"]).lower() for author in author_filter):
                filtered_papers.append(paper)
        tracked = filtered_papers
        print(f"Filtered to {len(tracked)} papers.")

    arxiv_ids = [p["arxiv_id"] for p in tracked]
    known_citations = state.get("known_citations", {})

    new_citations_total = []

    print(f"\nChecking citations for {len(arxiv_ids)} tracked paper(s)…")
    if since:
        print(f"  (since {since})")
    print()

    for paper in tracked:
        arxiv_id = paper["arxiv_id"]
        title = paper["title"] or arxiv_id
        citations = check_citations(arxiv_id, since=since)

        known = set(known_citations.get(arxiv_id, []))
        new_cites = [c for c in citations if c["s2_id"] and c["s2_id"] not in known]

        if new_cites:
            print(f"  📈 {title[:60]} — {len(new_cites)} new citation(s):")
            for c in new_cites:
                authors_str = ", ".join(c["authors"][:2])
                if len(c["authors"]) > 2:
                    authors_str += " et al."
                cite_count = ""
                print(f"    - [{c['year']}] {c['title'][:70]} ({authors_str})")
                new_citations_total.append(c)

            # Update known citations
            known_citations[arxiv_id] = list(known | {c["s2_id"] for c in new_cites})
        else:
            total_cites = len(known_citations.get(arxiv_id, []))
            if total_cites > 0:
                print(f"  📊 {title[:60]} — {total_cites} total citations (no new)")
            else:
                print(f"  📊 {title[:60]} — no citations found")

        time.sleep(REQUEST_DELAY)

    # Save state
    state["last_check"] = now_taipei()[:10]
    state["known_citations"] = known_citations
    state["known_author_papers"] = state.get("known_author_papers", {})  # preserve existing data
    save_state(state)

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Papers checked: {len(tracked)}")
    print(f"   New citations found: {len(new_citations_total)}")
    print(f"   State saved to {STATE_PATH.relative_to(WORKSPACE)}")
    print(f"   Last check: {state['last_check']}")
    return 0


def cmd_report(args):
    """Show last check results from state."""
    state = load_state()
    if not state.get("last_check"):
        print("No checks have been run yet. Run 'check' first.")
        return 0

    print(f"Last check: {state['last_check']}")
    known_citations = state.get("known_citations", {})
    total_citations = sum(len(v) for v in known_citations.values())
    print(f"Tracked papers with citations: {len(known_citations)}")
    print(f"Total known citations: {total_citations}")

    known_author_papers = state.get("known_author_papers", {})
    if known_author_papers:
        print(f"\nTracked authors:")
        for author, papers in known_author_papers.items():
            print(f"  {author}: {len(papers)} known paper(s)")

    # Top cited papers from knowledge graph
    if known_citations:
        print(f"\nTop cited (by known citation count):")
        tracked = extract_arxiv_papers()
        ranked = sorted(known_citations.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for arxiv_id, cites in ranked:
            title = next((p["title"] for p in tracked if p["arxiv_id"] == arxiv_id), arxiv_id)
            print(f"  {arxiv_id}: {len(cites)} citations — {title[:60]}")

    return 0


def cmd_trending(args):
    """Show trending related papers."""
    print("🔥 Fetching trending related papers...")

    # Use a query related to the research field based on knowledge graph content
    query = getattr(args, 'query', "speech interpretability machine learning")
    limit = getattr(args, 'limit', 10)

    trending_papers = fetch_trending_papers(query, limit)

    if not trending_papers:
        print("No trending papers found.")
        return 0

    print(f"\nTop {len(trending_papers)} trending papers in '{query}':")
    print("-" * 80)

    for i, paper in enumerate(trending_papers, 1):
        authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])][:2])
        if len(paper.get("authors", [])) > 2:
            authors += " et al."

        year = paper.get("year", "")
        cite_count = paper.get("citationCount", 0)
        trending_score = paper.get("trending_score", 0)
        arxiv_id = (paper.get("externalIds") or {}).get("ArXiv", "")
        arxiv_info = f" [arXiv:{arxiv_id}]" if arxiv_id else ""

        print(f"{i:2d}. {paper.get('title', '')[:70]}")
        print(f"    {authors} ({year}) — {cite_count} citations, score: {trending_score:.1f}{arxiv_info}")
        print()

    return 0


def cmd_reset(args):
    """Reset citation state."""
    save_state({
        "last_check": None,
        "known_citations": {},
        "known_author_papers": {},
    })
    print("Citation state reset.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="citation_monitor.py",
        description="Monitor citations for arXiv papers tracked in knowledge graph",
    )
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check for new citations")
    p_check.add_argument("--since", help="Check from date (YYYY-MM-DD)")
    p_check.add_argument("--authors", help="Comma-separated author names to filter by")

    sub.add_parser("report", help="Show last check results")
    sub.add_parser("reset", help="Reset citation state")

    p_trending = sub.add_parser("trending", help="Show trending related papers")
    p_trending.add_argument("--query", default="speech interpretability machine learning",
                           help="Search query for trending papers")
    p_trending.add_argument("--limit", type=int, default=10,
                           help="Number of papers to show")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    dispatch = {
        "check": cmd_check,
        "report": cmd_report,
        "reset": cmd_reset,
        "trending": cmd_trending,
    }
    return dispatch[args.command](args) or 0


if __name__ == "__main__":
    sys.exit(main())
