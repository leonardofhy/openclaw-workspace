#!/usr/bin/env python3
"""Fetch full paper text and generate structured reading notes.

Usage:
    python3 paper_reader.py --arxiv-id 2310.08475
    python3 paper_reader.py --from-scout daily/2026-03-24.json --top 5
    python3 paper_reader.py --from-scout daily/2026-03-24.json --min-score 25
    python3 paper_reader.py --skip-existing
    python3 paper_reader.py --dry-run
    python3 paper_reader.py --arxiv-id 2310.08475 --summarize
"""

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─── Paths ────────────────────────────────────────────────────────────────────

WORKSPACE = Path.home() / ".openclaw" / "workspace"
NOTES_DIR = WORKSPACE / "memory" / "lalm-ke" / "paper-notes"
DAILY_DIR = WORKSPACE / "memory" / "lalm-ke" / "daily"
INDEX_PATH = NOTES_DIR / "index.json"

TZ = timezone(timedelta(hours=8))
MAX_PAPER_BYTES = 80 * 1024  # 80KB

# ─── Network helpers ──────────────────────────────────────────────────────────

def fetch_url(url: str, headers: dict | None = None, retries: int = 1) -> str | None:
    """Fetch URL, return text content. Retry once on failure."""
    req_headers = {"User-Agent": "lalm-ke-reader/1.0"}
    if headers:
        req_headers.update(headers)
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=req_headers)
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # Try UTF-8 first, then latin-1
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    return raw.decode("latin-1", errors="replace")
        except HTTPError as e:
            if attempt < retries:
                print(f"  [WARN] HTTP {e.code} for {url}, retrying...")
                time.sleep(2)
            else:
                print(f"  [WARN] HTTP {e.code} for {url}: {e}")
                return None
        except (URLError, OSError) as e:
            if attempt < retries:
                print(f"  [WARN] Network error for {url}, retrying...")
                time.sleep(2)
            else:
                print(f"  [WARN] Network error for {url}: {e}")
                return None
    return None


# ─── arXiv metadata fetch ────────────────────────────────────────────────────

import xml.etree.ElementTree as ET
import urllib.parse

def fetch_arxiv_metadata(arxiv_id: str) -> dict | None:
    """Fetch metadata from arXiv API (abstract, title, authors, date)."""
    clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())
    params = urllib.parse.urlencode({
        "id_list": clean_id,
        "max_results": 1,
    })
    url = f"http://export.arxiv.org/api/query?{params}"
    text = fetch_url(url)
    if not text:
        return None

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    try:
        root = ET.fromstring(text)
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None
        title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
        title = re.sub(r"\s+", " ", title)
        abstract = (entry.findtext("atom:summary", namespaces=ns) or "").strip()
        abstract = re.sub(r"\s+", " ", abstract)

        authors = []
        for auth_el in entry.findall("atom:author", ns):
            name = auth_el.findtext("atom:name", namespaces=ns)
            if name:
                authors.append(name.strip())

        published = (entry.findtext("atom:published", namespaces=ns) or "").strip()
        pub_date = published[:10] if published else "unknown"

        cats = [c.attrib.get("term", "") for c in entry.findall("atom:category", ns)]

        return {
            "title": title,
            "authors": ", ".join(authors),
            "date": pub_date,
            "abstract": abstract,
            "categories": cats,
            "arxiv_id": clean_id,
        }
    except ET.ParseError as e:
        print(f"  [WARN] XML parse error: {e}")
        return None


# ─── Paper content fetch (HF → arXiv abstract fallback) ───────────────────────

def fetch_paper_content(arxiv_id: str) -> tuple[str, str]:
    """Fetch full paper content. Returns (content, source_label)."""
    clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())

    # Try 1: HuggingFace papers markdown
    hf_md_url = f"https://huggingface.co/papers/{clean_id}.md"
    content = fetch_url(hf_md_url)
    if content and len(content) > 500:
        print(f"  [OK] Fetched from HF markdown ({len(content)} bytes)")
        return content, "huggingface_md"

    # Try 2: HuggingFace papers with Accept: text/markdown
    hf_url = f"https://huggingface.co/papers/{clean_id}"
    content = fetch_url(hf_url, headers={"Accept": "text/markdown"})
    if content and len(content) > 500:
        print(f"  [OK] Fetched from HF papers ({len(content)} bytes)")
        return content, "huggingface_html"

    # Try 3: arXiv abstract only (always works)
    print(f"  [INFO] Falling back to arXiv abstract for {clean_id}")
    meta = fetch_arxiv_metadata(clean_id)
    if meta and meta.get("abstract"):
        content = f"# Abstract\n\n{meta['abstract']}"
        return content, "arxiv_abstract_only"

    return "", "not_found"


# ─── Content truncation ───────────────────────────────────────────────────────

def smart_truncate(content: str, max_bytes: int = MAX_PAPER_BYTES) -> str:
    """If content exceeds max_bytes, keep intro + method + conclusion sections."""
    encoded = content.encode("utf-8")
    if len(encoded) <= max_bytes:
        return content

    print(f"  [INFO] Content too large ({len(encoded)} bytes), truncating to key sections...")

    # Heuristic: find section boundaries
    sections = {}
    section_pattern = re.compile(
        r"^#{1,3}\s*(abstract|introduction|related work|method|approach|model|"
        r"experiment|result|conclusion|limitation|future)",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(section_pattern.finditer(content))

    for i, m in enumerate(matches):
        name = m.group(1).lower()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections[name] = content[start:end]

    # Priority order: abstract, intro, method/approach/model, results/experiments, conclusion
    priority_keys = [
        "abstract", "introduction", "method", "approach", "model",
        "result", "experiment", "conclusion", "limitation",
    ]
    parts = []
    budget = max_bytes
    for key in priority_keys:
        for sec_name, sec_content in sections.items():
            if key in sec_name:
                chunk = sec_content.encode("utf-8")[:budget // len(priority_keys)]
                parts.append(chunk.decode("utf-8", errors="ignore"))
                break

    if parts:
        return "\n\n[TRUNCATED - key sections only]\n\n" + "\n\n".join(parts)

    # Fallback: just truncate at max_bytes
    return content.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore") + "\n\n[TRUNCATED]"


# ─── Section extraction ───────────────────────────────────────────────────────

def extract_section(content: str, section_names: list[str], max_chars: int = 1500) -> str:
    """Extract a named section from markdown content."""
    # Build pattern matching any of the section names
    pattern_str = "|".join(re.escape(n) for n in section_names)
    header_re = re.compile(
        rf"^#{1,3}\s*(?:{pattern_str})\b[^\n]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    next_header_re = re.compile(r"^#{1,3}\s", re.MULTILINE)

    m = header_re.search(content)
    if not m:
        return ""

    section_start = m.end()
    # Find next header after this section
    next_m = next_header_re.search(content, section_start)
    section_end = next_m.start() if next_m else len(content)

    text = content[section_start:section_end].strip()
    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def extract_abstract(content: str, meta: dict | None = None) -> str:
    """Extract abstract from paper content or metadata."""
    # Try section extraction
    abstract = extract_section(content, ["abstract"], max_chars=800)
    if abstract:
        return abstract
    # Fall back to metadata
    if meta and meta.get("abstract"):
        return meta["abstract"][:800]
    # Try first paragraph
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    if paragraphs:
        return paragraphs[0][:600]
    return "Not available"


def extract_key_sections(content: str) -> dict[str, str]:
    """Extract key sections from paper markdown."""
    return {
        "abstract": extract_section(content, ["abstract"], 800),
        "introduction": extract_section(content, ["introduction", "intro"], 1200),
        "method": extract_section(content, [
            "method", "approach", "model", "architecture",
            "proposed method", "our approach", "methodology"
        ], 1500),
        "results": extract_section(content, [
            "result", "experiment", "evaluation", "performance",
            "main result", "experimental result"
        ], 1200),
        "conclusion": extract_section(content, [
            "conclusion", "summary", "discussion", "future work"
        ], 800),
    }


# ─── LALM-KE relevance analysis ──────────────────────────────────────────────

KE_KEYWORDS = [
    "knowledge editing", "model editing", "factual editing",
    "ROME", "MEMIT", "MEND", "SERAC", "GRACE", "WISE",
    "knowledge neurons", "locate-and-edit", "knowledge update",
    "fact tracing", "causal tracing", "knowledge injection",
    "counterfactual editing", "sequential editing",
]

LALM_KEYWORDS = [
    "audio language model", "speech language model", "audio LLM",
    "SALMONN", "Qwen-Audio", "WavLLM", "SLAM-LLM", "AudioPaLM",
    "LALM", "speech LLM", "spoken language model", "audio foundation",
    "audio understanding", "speech understanding", "multimodal audio",
]

def compute_relevance(title: str, abstract: str, content: str) -> tuple[int, str]:
    """Compute LALM-KE relevance score 0-3 with explanation."""
    text = f"{title} {abstract} {content[:2000]}".lower()

    ke_hits = [kw for kw in KE_KEYWORDS if kw.lower() in text]
    lalm_hits = [kw for kw in LALM_KEYWORDS if kw.lower() in text]

    if ke_hits and lalm_hits:
        score = 3
        explanation = (
            f"Direct intersection of KE and LALM. "
            f"KE signals: {', '.join(ke_hits[:3])}. "
            f"LALM signals: {', '.join(lalm_hits[:2])}."
        )
    elif ke_hits:
        score = 2 if len(ke_hits) >= 2 else 1
        explanation = f"Knowledge editing focused. Signals: {', '.join(ke_hits[:4])}."
    elif lalm_hits:
        score = 2 if len(lalm_hits) >= 2 else 1
        explanation = f"Audio/speech LM focused. Signals: {', '.join(lalm_hits[:4])}."
    else:
        score = 0
        explanation = "No direct LALM-KE signals found."

    return score, explanation


# ─── Note generation ─────────────────────────────────────────────────────────

def generate_note(
    arxiv_id: str,
    meta: dict,
    content: str,
    source_label: str,
    scout_score: float = 0.0,
    dry_run: bool = False,
) -> str:
    """Generate structured paper note from extracted content."""
    today = date.today().isoformat()
    title = meta.get("title", f"Paper {arxiv_id}")
    authors = meta.get("authors", "Unknown")
    pub_date = meta.get("date", "unknown")

    sections = extract_key_sections(content)
    abstract_text = sections["abstract"] or extract_abstract(content, meta)
    method_text = sections["method"] or "_Method section not found_"
    results_text = sections["results"] or "_Results section not found_"
    intro_text = sections["introduction"] or "_Introduction not found_"
    conclusion_text = sections["conclusion"] or "_Conclusion not found_"

    relevance_score, relevance_explanation = compute_relevance(title, abstract_text, content)

    # Build summary from available sections
    summary_parts = []
    if abstract_text and abstract_text != "Not available":
        summary_parts.append(abstract_text[:400])
    if conclusion_text and conclusion_text != "_Conclusion not found_":
        summary_parts.append(conclusion_text[:300])
    summary = " ".join(summary_parts)[:700] if summary_parts else "Summary not available."

    note = f"""# {title}

- **arXiv:** {arxiv_id}
- **Authors:** {authors}
- **Date:** {pub_date}
- **Scout Score:** {scout_score}
- **Relevance:** {relevance_score}/3 — {relevance_explanation}
- **Read Date:** {today}
- **Note Type:** auto-extracted (source: {source_label})

## Summary

{summary}

## Problem

{intro_text[:600] if intro_text != "_Introduction not found_" else "_Not extracted_"}

## Method

{method_text[:800] if method_text != "_Method section not found_" else "_Not extracted_"}

## Key Results

{results_text[:800] if results_text != "_Results section not found_" else "_Not extracted_"}

## LALM-KE Relevance

**Score: {relevance_score}/3**

{relevance_explanation}

{"**Direct LALM-KE intersection** — this paper may directly address knowledge editing in audio/speech LMs." if relevance_score == 3 else ""}
{"**Related — may have transferable insights** for the LALM-KE problem." if relevance_score == 2 else ""}
{"**Tangentially relevant** — worth monitoring." if relevance_score == 1 else ""}
{"**Low direct relevance** — filing for reference." if relevance_score == 0 else ""}

## Open Questions

{conclusion_text[:400] if conclusion_text != "_Conclusion not found_" else "_Not extracted — read full paper for limitations and future work._"}

## Connections

_To be filled during deeper reading._

---
*Note auto-extracted by paper_reader.py on {today}. Upgrade with `--summarize` for LLM-ready format.*
"""
    return note.strip()


# ─── LLM summarization prompt output ─────────────────────────────────────────

def generate_summarize_output(arxiv_id: str, meta: dict, content: str) -> str:
    """Output paper content formatted for LLM summarization."""
    title = meta.get("title", f"Paper {arxiv_id}")
    authors = meta.get("authors", "Unknown")
    pub_date = meta.get("date", "unknown")
    sections = extract_key_sections(content)

    output = f"""=== LLM SUMMARIZATION REQUEST ===
Paper: {title}
arXiv: {arxiv_id}
Authors: {authors}
Date: {pub_date}

Please generate a structured note in this exact format:

# {title}
- **arXiv:** {arxiv_id}
- **Authors:** {authors}
- **Date:** {pub_date}
- **Relevance:** [0-3]/3 — [explanation of connection to knowledge editing × audio LMs]
- **Read Date:** {date.today().isoformat()}

## Summary
[3-5 sentence summary]

## Problem
[what problem does this paper address]

## Method
[key technique / approach]

## Key Results
[quantitative results if available]

## LALM-KE Relevance
[connection to knowledge editing × audio language models]

## Open Questions
[limitations, future work]

## Connections
[links to other papers, methods, or concepts]

=== PAPER CONTENT ===

### Abstract
{sections['abstract'] or meta.get('abstract', 'Not available')}

### Introduction
{sections['introduction'] or 'Not extracted'}

### Method / Approach
{sections['method'] or 'Not extracted'}

### Results / Experiments
{sections['results'] or 'Not extracted'}

### Conclusion
{sections['conclusion'] or 'Not extracted'}
=== END ==="""
    return output


# ─── Index management ─────────────────────────────────────────────────────────

def load_index() -> dict:
    """Load paper notes index."""
    if INDEX_PATH.exists():
        with open(INDEX_PATH) as f:
            return json.load(f)
    return {"papers": {}, "last_updated": None}


def save_index(index: dict) -> None:
    """Save paper notes index."""
    index["last_updated"] = datetime.now(TZ).isoformat()
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def is_already_read(arxiv_id: str, index: dict) -> bool:
    """Check if paper already has a note."""
    clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())
    return clean_id in index.get("papers", {})


# ─── Process single paper ────────────────────────────────────────────────────

def process_paper(
    arxiv_id: str,
    scout_score: float = 0.0,
    skip_existing: bool = False,
    dry_run: bool = False,
    summarize: bool = False,
    index: dict | None = None,
) -> bool:
    """Fetch, parse, and save note for a single paper. Returns True on success."""
    clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())
    print(f"\n[Paper] {clean_id} (scout score: {scout_score})")

    if index is None:
        index = load_index()

    if skip_existing and is_already_read(clean_id, index):
        print(f"  [SKIP] Already have notes for {clean_id}")
        return False

    # Fetch metadata
    print(f"  Fetching metadata from arXiv API...")
    meta = fetch_arxiv_metadata(clean_id)
    if not meta:
        print(f"  [WARN] Could not fetch metadata for {clean_id}, skipping")
        return False
    print(f"  Title: {meta['title'][:70]}")

    # Fetch full content
    print(f"  Fetching paper content...")
    content, source_label = fetch_paper_content(clean_id)

    if not content:
        print(f"  [WARN] Could not fetch content for {clean_id}, creating abstract-only note")
        content = f"# Abstract\n\n{meta.get('abstract', 'Not available')}"
        source_label = "arxiv_abstract_only"

    # Truncate if needed
    content = smart_truncate(content)

    # Generate output
    if summarize:
        output = generate_summarize_output(clean_id, meta, content)
        print("\n" + output)
        return True

    note = generate_note(
        arxiv_id=clean_id,
        meta=meta,
        content=content,
        source_label=source_label,
        scout_score=scout_score,
        dry_run=dry_run,
    )

    if dry_run:
        print(f"\n--- DRY RUN NOTE PREVIEW ---")
        print(note[:800])
        print("--- (truncated) ---")
        return True

    # Save note
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    note_path = NOTES_DIR / f"{clean_id}.md"
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note)
    print(f"  [OK] Saved note: {note_path}")

    # Update index
    relevance_score, _ = compute_relevance(meta.get("title", ""), meta.get("abstract", ""), content)
    index["papers"][clean_id] = {
        "arxiv_id": clean_id,
        "title": meta.get("title", ""),
        "authors": meta.get("authors", ""),
        "date": meta.get("date", ""),
        "read_date": date.today().isoformat(),
        "scout_score": scout_score,
        "relevance": relevance_score,
        "note_path": str(note_path),
        "source": source_label,
    }
    save_index(index)

    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LALM-KE Paper Reader — fetch and generate structured notes")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--arxiv-id", type=str, help="Single arXiv ID to process")
    group.add_argument("--from-scout", type=str, help="Path to daily scout JSON output")

    parser.add_argument("--top", type=int, default=None, help="Top N papers from scout (default: all)")
    parser.add_argument("--min-score", type=float, default=None, help="Min scout score threshold")
    parser.add_argument("--skip-existing", action="store_true", help="Skip papers with existing notes")
    parser.add_argument("--dry-run", action="store_true", help="Parse and preview, don't write files")
    parser.add_argument("--summarize", action="store_true", help="Output LLM-ready summarization prompt")

    args = parser.parse_args()

    # Validate
    if not args.arxiv_id and not args.from_scout:
        parser.print_help()
        print("\n[ERROR] Provide either --arxiv-id or --from-scout")
        sys.exit(1)

    if args.dry_run:
        print("[DRY RUN] No files will be written.")

    index = load_index()
    papers_to_process: list[tuple[str, float]] = []

    if args.arxiv_id:
        papers_to_process = [(args.arxiv_id, 0.0)]

    elif args.from_scout:
        scout_path = Path(args.from_scout)
        # Resolve relative paths against DAILY_DIR
        if not scout_path.is_absolute():
            scout_path = DAILY_DIR / scout_path
        if not scout_path.exists():
            print(f"[ERROR] Scout file not found: {scout_path}")
            sys.exit(1)

        with open(scout_path) as f:
            scout_data = json.load(f)

        papers = scout_data.get("papers", [])
        print(f"[INFO] Loaded {len(papers)} papers from {scout_path}")

        # Filter by min score
        if args.min_score is not None:
            papers = [p for p in papers if p.get("score", 0) >= args.min_score]
            print(f"[INFO] After min-score {args.min_score}: {len(papers)} papers")

        # Sort by score descending (should already be sorted, but ensure)
        papers.sort(key=lambda x: -x.get("score", 0))

        # Apply top N limit
        if args.top is not None:
            papers = papers[:args.top]
            print(f"[INFO] Processing top {args.top} papers")

        papers_to_process = [
            (p.get("arxiv_id", ""), float(p.get("score", 0)))
            for p in papers
            if p.get("arxiv_id")
        ]

    if not papers_to_process:
        print("[WARN] No papers to process.")
        sys.exit(0)

    print(f"\n=== Processing {len(papers_to_process)} paper(s) ===")
    success_count = 0

    for i, (arxiv_id, scout_score) in enumerate(papers_to_process):
        if i > 0:
            print(f"  [Delay] Waiting 3 seconds...")
            time.sleep(3)

        ok = process_paper(
            arxiv_id=arxiv_id,
            scout_score=scout_score,
            skip_existing=args.skip_existing,
            dry_run=args.dry_run,
            summarize=args.summarize,
            index=index,
        )
        if ok:
            success_count += 1

    print(f"\n=== Done: {success_count}/{len(papers_to_process)} papers processed ===")
    if not args.dry_run and not args.summarize:
        print(f"Notes saved to: {NOTES_DIR}")
        print(f"Index: {INDEX_PATH}")


if __name__ == "__main__":
    main()
