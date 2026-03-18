#!/usr/bin/env python3
"""Resolve [CITE: ...] markers in Paper A markdown files to \\cite{key} format.

Reads all paper-a-*.md files, maps each [CITE: X] marker to a BibTeX key
from references.bib, and outputs:
  1. A mapping table (CITE marker → BibTeX key)
  2. Optionally rewrites files with \\cite{key} replacements (--apply flag)
"""

import re
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).parent
BIB_FILE = DOCS_DIR / "references.bib"

# Paper source files (not the compiled draft)
PAPER_FILES = [
    "paper-a-abstract.md",
    "paper-a-intro-rw.md",
    "paper-a-method.md",
    "paper-a-results.md",
    "paper-a-results-stub.md",
    "paper-a-discussion-stub.md",
    "paper-a-outline.md",
    "paper-a-draft.md",
]

# Mapping: [CITE: marker_text] → bibtex_key
# Each key matches the pattern used in the [CITE: ...] markers
CITE_MAP: dict[str, str] = {
    # Causal abstraction & intervention methods
    "Geiger et al. 2301.04709": "geiger2021causal",
    "Geiger et al. 2303.02536": "geiger2023das",
    "Wu et al. 2024": "wu2024pyvene",
    "Heimersheim and Nanda 2024": "heimersheim2024patching",
    "Huang et al. 2024": "huang2024ravel",
    # Audio-LM behavioral studies
    "Zhao 2602.23136": "zhao2026modalitycollapse",
    "Chen 2603.02266": "chen2026mpar2",
    "IISc/Microsoft 2602.23300": "mistere2026",
    "2602.17598": "cascade2026",
    # Audio-LM interpretability
    "Ho et al. 2025": "ho2025audiolens",
    "Glazer et al. 2025": "glazer2025beyondtranscription",
    "2601.03115": "zhao2026esn",
    "Chowdhury et al. 2026": "chowdhury2026ard",
    "Djanibekov et al. 2025": "djanibekov2025spirit",
    "2603.02250": "sgpa2026",
    # Speech model interpretability
    "Reid 2023": "reid2023whisper",
    "2602.18899": "choi2026phonological",
    "2603.03096": "vanrensburg2026speaker",
    "2602.15307": "kawamura2026aape",
    "Ma et al. 2026": "ma2026lora",
    # Vision-language analogs
    "Li et al. 2025": "li2025fcct",
    "Fan et al. 2026": "fan2026embedlens",
    "Liu et al. 2025": "liu2025visualrep",
    # Sparse autoencoders for audio
    "Aparin et al. 2026": "aparin2026audiosae",
    "Karvonen et al. 2025": "karvonen2025saebench",
    "Bhalla et al. 2025": "bhalla2025tsae",
    # Causal methods in audio-adjacent domains
    "2603.01006": "agrepa2026",
    "2602.01247": "maghsoudi2026braintospeech",
    # Multimodal theory
    "Sutter et al.": "sutter2024modality",
    "Asiaee et al. 2602.24266": "asiaee2026sparse",
    # ALME benchmark (referenced as TODO in method)
    "2602.11488": "alme2026",
}

# Ambiguous bare-year entries — context-dependent resolution
CITE_YEAR_CONTEXT: dict[str, dict[str, str]] = {
    "2025": {
        "Braun": "braun2025scd",
        "Mariotte": "mariotte2025audiosae",
    },
    "2024": {
        "Heimersheim": "heimersheim2024patching",
        "Wu": "wu2024pyvene",
    },
}


def extract_cite_markers(text: str) -> list[tuple[int, str]]:
    """Extract all [CITE: ...] markers with line numbers."""
    results = []
    for i, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"\[CITE:\s*([^\]]+)\]", line):
            results.append((i, match.group(1).strip()))
    return results


def resolve_marker(marker: str, context_line: str = "") -> str | None:
    """Resolve a CITE marker to a BibTeX key."""
    # Direct lookup
    if marker in CITE_MAP:
        return CITE_MAP[marker]

    # Handle bare year markers [CITE: 2024], [CITE: 2025] with context disambiguation
    if marker in CITE_YEAR_CONTEXT:
        for author_hint, key in CITE_YEAR_CONTEXT[marker].items():
            if author_hint in context_line:
                return key
        return None  # ambiguous

    # Try partial matching (arXiv ID only)
    for cite_text, key in CITE_MAP.items():
        if marker in cite_text or cite_text in marker:
            return key

    return None


def replace_citations_in_text(text: str) -> tuple[str, list[dict]]:
    """Replace [CITE: X] markers with \\cite{key} in text."""
    replacements = []

    def replace_fn(match: re.Match) -> str:
        marker = match.group(1).strip()
        full_line = match.string[max(0, match.start() - 80):match.end() + 20]
        key = resolve_marker(marker, full_line)
        replacements.append({
            "marker": f"[CITE: {marker}]",
            "key": key,
            "resolved": key is not None,
        })
        if key:
            return f"\\cite{{{key}}}"
        return match.group(0)  # leave unresolved markers intact

    result = re.sub(r"\[CITE:\s*([^\]]+)\]", replace_fn, text)
    return result, replacements


def print_mapping_table(all_replacements: dict[str, list[dict]]) -> None:
    """Print the CITE marker → BibTeX key mapping table."""
    print("\n" + "=" * 80)
    print("  CITATION MAPPING TABLE")
    print("=" * 80)
    print(f"\n  {'CITE Marker':<45} {'BibTeX Key':<30} {'Status'}")
    print(f"  {'-' * 44} {'-' * 29} {'-' * 10}")

    seen = set()
    resolved_count = 0
    unresolved_count = 0

    for filename, reps in all_replacements.items():
        for r in reps:
            marker = r["marker"]
            if marker in seen:
                continue
            seen.add(marker)

            key = r["key"] or "[UNRESOLVED]"
            status = "OK" if r["resolved"] else "MISSING"
            if r["resolved"]:
                resolved_count += 1
            else:
                unresolved_count += 1
            print(f"  {marker:<45} {key:<30} {status}")

    print(f"\n  Total: {resolved_count} resolved, {unresolved_count} unresolved")
    print("=" * 80)


def main():
    apply_mode = "--apply" in sys.argv

    if not BIB_FILE.exists():
        print(f"WARNING: {BIB_FILE} not found. Run this after creating references.bib.")

    all_replacements: dict[str, list[dict]] = {}

    for filename in PAPER_FILES:
        path = DOCS_DIR / filename
        if not path.exists():
            continue

        text = path.read_text()
        markers = extract_cite_markers(text)

        if not markers:
            continue

        new_text, replacements = replace_citations_in_text(text)
        all_replacements[filename] = replacements

        if apply_mode and new_text != text:
            path.write_text(new_text)
            print(f"  Updated: {filename} ({len(replacements)} citations)")

    # Print mapping table
    print_mapping_table(all_replacements)

    # Summary
    if not apply_mode:
        print("\n  Dry run — no files modified. Use --apply to rewrite files.")
    else:
        print("\n  Files updated with \\cite{key} replacements.")


if __name__ == "__main__":
    main()
