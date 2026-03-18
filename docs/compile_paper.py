#!/usr/bin/env python3
"""Compile Paper A from component section files into a unified draft."""

import re
import os
from pathlib import Path

DOCS_DIR = Path(__file__).parent
OUTPUT_FILE = DOCS_DIR / "paper-a-draft.md"

# Section files in paper order
SECTION_FILES = [
    ("Introduction + Related Work", "paper-a-intro-rw.md"),
    ("Method", "paper-a-method.md"),
    ("Results", "paper-a-results-stub.md"),
    ("Discussion", "paper-a-discussion-stub.md"),
]

# Word count targets per section
WORD_TARGETS = {
    "Introduction": 800,
    "Related Work": 1000,
    "Method": 1500,
    "Results": 1500,
    "Discussion": 800,
}


def count_words(text: str) -> int:
    """Count words excluding markdown syntax, tables, and math."""
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove math blocks
    text = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
    # Remove inline math
    text = re.sub(r"\$[^$]+\$", "", text)
    # Remove markdown table rows (lines starting with |)
    text = re.sub(r"^\|.*$", "", text, flags=re.MULTILINE)
    # Remove markdown headers markers but keep text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove link/image syntax
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}|_{1,3}", "", text)
    return len(text.split())


def find_markers(text: str, filename: str) -> list[dict]:
    """Find all [TODO] and [CITE] markers with line numbers."""
    markers = []
    for i, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"\[(TODO[^\]]*)\]", line):
            markers.append({
                "type": "TODO",
                "text": match.group(1),
                "file": filename,
                "line": i,
            })
        for match in re.finditer(r"\[(CITE[^\]]*)\]", line):
            markers.append({
                "type": "CITE",
                "text": match.group(1),
                "file": filename,
                "line": i,
            })
    return markers


def extract_sections(text: str) -> dict[str, str]:
    """Split text into top-level sections by ## or # headers."""
    sections = {}
    current_name = None
    current_lines = []

    for line in text.splitlines():
        header_match = re.match(r"^#{1,2}\s+(§?\d+\.?\d*\s+)?(.+)", line)
        if header_match:
            if current_name:
                sections[current_name] = "\n".join(current_lines)
            current_name = header_match.group(2).strip()
            current_lines = [line]
        elif current_name:
            current_lines.append(line)

    if current_name:
        sections[current_name] = "\n".join(current_lines)
    return sections


def generate_toc(merged_text: str) -> str:
    """Generate a table of contents from markdown headers."""
    toc_lines = ["## Table of Contents\n"]
    for line in merged_text.splitlines():
        match = re.match(r"^(#{1,3})\s+(.+)", line)
        if match:
            level = len(match.group(1))
            title = match.group(2)
            anchor = re.sub(r"[^a-z0-9\s-]", "", title.lower())
            anchor = re.sub(r"\s+", "-", anchor.strip())
            indent = "  " * (level - 1)
            toc_lines.append(f"{indent}- [{title}](#{anchor})")
    return "\n".join(toc_lines) + "\n"


def build_merged_draft() -> str:
    """Read all section files and merge into a single document."""
    outline_path = DOCS_DIR / "paper-a-outline.md"
    outline_text = outline_path.read_text() if outline_path.exists() else ""

    # Extract abstract from outline
    abstract = ""
    if "## Abstract" in outline_text:
        start = outline_text.index("## Abstract")
        end = outline_text.index("\n---", start)
        abstract = outline_text[start:end].strip()

    parts = []
    parts.append("# The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse\n")
    if abstract:
        parts.append(abstract + "\n")
    parts.append("---\n")

    for label, filename in SECTION_FILES:
        path = DOCS_DIR / filename
        if path.exists():
            content = path.read_text().strip()
            parts.append(content)
            parts.append("\n\n---\n")
        else:
            parts.append(f"# {label}\n\n[TODO: Section not yet written]\n\n---\n")

    # Conclusion from outline
    parts.append("## §6 Conclusion\n")
    parts.append("[TODO: 1 paragraph summary of contributions]\n")
    parts.append("[TODO: 1 sentence on broadest implication — "
                 '"mechanistic understanding of when ALMs listen vs. guess"]\n')

    return "\n".join(parts)


def completeness_report(all_markers: list[dict], section_words: dict[str, int]) -> str:
    """Generate a completeness report."""
    lines = [
        "",
        "=" * 70,
        "  PAPER A COMPLETENESS REPORT",
        "=" * 70,
        "",
        "── Section Status ──────────────────────────────────────────────────",
        "",
    ]

    expected_sections = {
        "Introduction": "paper-a-intro-rw.md",
        "Related Work": "paper-a-intro-rw.md",
        "Method": "paper-a-method.md",
        "Results": "paper-a-results-stub.md",
        "Discussion": "paper-a-discussion-stub.md",
    }

    for section, filename in expected_sections.items():
        path = DOCS_DIR / filename
        exists = path.exists()
        status = "✓ EXISTS" if exists else "✗ MISSING"
        target = WORD_TARGETS.get(section, "?")
        actual = section_words.get(section, 0)

        if isinstance(target, int) and actual > 0:
            pct = actual / target * 100
            bar_len = 30
            filled = min(int(pct / 100 * bar_len), bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            word_info = f"{actual:>5}w / {target}w  [{bar}] {pct:.0f}%"
        else:
            word_info = f"{actual:>5}w / {target}w"

        lines.append(f"  {status:<12} §{section:<20} {word_info}")
        lines.append(f"  {'':12} source: {filename}")
        lines.append("")

    # Total word count
    total = sum(section_words.values())
    total_target = sum(WORD_TARGETS.values())
    lines.append(f"  TOTAL: {total}w / {total_target}w target")
    lines.append("")

    # Marker summary
    todos = [m for m in all_markers if m["type"] == "TODO"]
    cites = [m for m in all_markers if m["type"] == "CITE"]

    lines.append("── Markers ─────────────────────────────────────────────────────────")
    lines.append(f"  TODOs remaining: {len(todos)}")
    lines.append(f"  CITEs remaining: {len(cites)}")
    lines.append("")

    if todos:
        lines.append("── TODO List ───────────────────────────────────────────────────────")
        for m in todos:
            lines.append(f"  {m['file']}:{m['line']}  [{m['text']}]")
        lines.append("")

    if cites:
        lines.append("── CITE List ───────────────────────────────────────────────────────")
        for m in cites:
            lines.append(f"  {m['file']}:{m['line']}  [{m['text']}]")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    print("Compiling Paper A draft...")
    print()

    # Build merged document
    merged = build_merged_draft()

    # Generate TOC
    toc = generate_toc(merged)

    # Insert TOC after title + abstract
    parts = merged.split("---\n", 1)
    if len(parts) == 2:
        final = parts[0] + toc + "\n---\n" + parts[1]
    else:
        final = toc + "\n" + merged

    # Write output
    OUTPUT_FILE.write_text(final)
    print(f"  Draft written to: {OUTPUT_FILE}")
    print(f"  Total length: {len(final)} chars, {count_words(final)} words (prose)")

    # Collect markers from all source files
    all_markers = []
    section_words = {}

    source_files = [f for _, f in SECTION_FILES] + ["paper-a-outline.md"]
    for filename in source_files:
        path = DOCS_DIR / filename
        if path.exists():
            text = path.read_text()
            all_markers.extend(find_markers(text, filename))

    # Word counts per logical section (approximate by file mapping)
    file_section_map = {
        "paper-a-intro-rw.md": {
            "Introduction": r"(?:^|\n)#+ .*Introduction.*?\n(.*?)(?=\n#+ .*Related Work|\Z)",
            "Related Work": r"(?:^|\n)#+ .*Related Work.*?\n(.*?)(?=\n# |\Z)",
        },
        "paper-a-method.md": {"Method": None},  # whole file
        "paper-a-results-stub.md": {"Results": None},
        "paper-a-discussion-stub.md": {"Discussion": None},
    }

    for filename, sections in file_section_map.items():
        path = DOCS_DIR / filename
        if not path.exists():
            continue
        text = path.read_text()
        for section_name, pattern in sections.items():
            if pattern is None:
                section_words[section_name] = count_words(text)
            else:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    section_words[section_name] = count_words(match.group(1))
                else:
                    section_words[section_name] = count_words(text) // len(sections)

    # Print report
    report = completeness_report(all_markers, section_words)
    print(report)


if __name__ == "__main__":
    main()
