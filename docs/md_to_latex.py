#!/usr/bin/env python3
"""Convert docs/paper-a-draft.md to docs/paper-a.tex.

Reads the Markdown draft and produces a conference-style LaTeX document
with an IEEE/Interspeech-style preamble.  Run from the workspace root:

    python3 docs/md_to_latex.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
SRC_MD = SCRIPT_DIR / "paper-a-draft.md"
DST_TEX = SCRIPT_DIR / "paper-a.tex"
RESULTS_TABLE = SCRIPT_DIR / "results_table.tex"
BIB_FILE = SCRIPT_DIR / "references.bib"

# ---------------------------------------------------------------------------
# LaTeX preamble / document structure
# ---------------------------------------------------------------------------

PREAMBLE = r"""\documentclass[a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\geometry{margin=1in}
\usepackage{times}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{multirow}
\usepackage{array}
"""

TITLE_BLOCK = r"""\title{The Listening Geometry: Where Audio-Language Models Listen, Guess, and Collapse}
\author{Anonymous Authors}
\date{}
"""

DOC_BEGIN = r"""\begin{document}
\maketitle
\tableofcontents
\newpage
"""

DOC_END = r"""
\bibliographystyle{IEEEtran}
\bibliography{references}
\end{document}
"""

# ---------------------------------------------------------------------------
# Helper: escape LaTeX special characters in plain text
# ---------------------------------------------------------------------------

# Characters that must be escaped in LaTeX text (not math, not already-LaTeX).
_ESCAPE_MAP = [
    # Order matters: backslash must come first so we don't double-escape it.
    # We intentionally skip backslash replacement here — LaTeX commands already
    # in the source (e.g. \ldots) must pass through untouched.
    ("&", r"\&"),
    ("%", r"\%"),
    # '#' — but only when not already inside a LaTeX command argument
    ("#", r"\#"),
    # '$' is skipped: we handle math separately.
    # Curly braces that are part of plain text (not LaTeX commands):
    # We leave them alone; accidental bare braces are uncommon and hard to
    # distinguish from intentional LaTeX.
]


def escape_text(text: str) -> str:
    """Escape LaTeX-special characters in plain (non-math, non-command) text."""
    for char, replacement in _ESCAPE_MAP:
        text = text.replace(char, replacement)
    return text


# ---------------------------------------------------------------------------
# Helper: cite key generation
# ---------------------------------------------------------------------------

def cite_to_key(cite_body: str) -> str:
    """Convert a [CITE: Author Year] string to a BibTeX key.

    Examples:
        "Smith 2025"         -> "smith2025"
        "Geiger et al. 2023" -> "geiger2023"
        "Ho et al. 2025"     -> "ho2025"
        "2602.23136"         -> "arxiv_2602.23136"
    """
    body = cite_body.strip()
    # ArXiv ID pattern (digits.digits, possibly with a year prefix)
    arxiv_match = re.match(r"^(\d{4}\.\d{4,5})$", body)
    if arxiv_match:
        return f"arxiv_{arxiv_match.group(1)}"

    # "Author Year" or "Author et al. Year" or "Author/Author Year"
    # Extract trailing 4-digit year
    year_match = re.search(r"\b(\d{4})\b", body)
    year = year_match.group(1) if year_match else ""

    # First token is the first author surname (or institution abbreviation)
    first_token = re.split(r"[\s/,]", body)[0]
    author = re.sub(r"[^a-zA-Z]", "", first_token).lower()

    if author and year:
        return f"{author}{year}"
    if author:
        return author
    if year:
        return f"ref{year}"
    return re.sub(r"\W+", "_", body.lower())[:32]


# ---------------------------------------------------------------------------
# Inline formatting: bold, italic, math, links, markers
# ---------------------------------------------------------------------------

def _protect_math(text: str) -> tuple[str, list[str]]:
    """Extract math spans so they are not touched by other substitutions.

    Returns the text with math replaced by placeholders (MATH_n) and
    a list of the original math strings.
    """
    placeholders: list[str] = []

    def _replace(m: re.Match) -> str:
        idx = len(placeholders)
        placeholders.append(m.group(0))
        return f"\x00MATH{idx}\x00"

    # Display math $$...$$ (possibly multiline — but at inline level we only
    # see single-line remnants; multiline is handled at block level).
    text = re.sub(r"\$\$.+?\$\$", _replace, text, flags=re.DOTALL)
    # Inline math $...$
    text = re.sub(r"\$(?!\$).+?(?<!\$)\$", _replace, text)
    return text, placeholders


def _restore_math(text: str, placeholders: list[str]) -> str:
    for idx, original in enumerate(placeholders):
        text = text.replace(f"\x00MATH{idx}\x00", original)
    return text


def _protect_lone_stars(text: str) -> str:
    """Replace unpaired asterisks (e.g. k*, t*) with LONESTAR placeholders.

    Valid italic spans (*word*) and bold spans (**word**) have their asterisks
    consumed by the subsequent regex pass.  Asterisks that are NOT part of any
    valid pairing — typically mathematical superscript-stars like k* or t* —
    are replaced with ``\\x00LONESTAR\\x00`` so they pass through as literal ``*``.

    An asterisk run is a valid OPENER only when preceded by whitespace, start,
    or punctuation (not a word character).  It is a valid CLOSER only when
    followed by whitespace, end, or punctuation (not a word character or another *).
    Any run that does not qualify as opener or closer is treated as lone stars.
    """
    # Find positions and lengths of all *-runs (sequences of one or more *).
    runs: list[tuple[int, int]] = []  # (start, length)
    i = 0
    while i < len(text):
        if text[i] == "*":
            j = i
            while j < len(text) and text[j] == "*":
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1

    if not runs:
        return text

    _OPENER_BEFORE = set(" \t\n,.:;([{\"'")  # chars that can precede an opener
    _CLOSER_AFTER = set(" \t\n,.:;)]}\"'!?")  # chars that can follow a closer

    def can_open(pos: int, length: int) -> bool:
        """Return True if this run can serve as an italic/bold opener."""
        before = text[pos - 1] if pos > 0 else " "
        after = text[pos + length] if pos + length < len(text) else " "
        return (before in _OPENER_BEFORE or not before.isalpha()) and after not in _CLOSER_AFTER

    def can_close(pos: int, length: int) -> bool:
        """Return True if this run can serve as an italic/bold closer."""
        before = text[pos - 1] if pos > 0 else " "
        after = text[pos + length] if pos + length < len(text) else " "
        return before not in _OPENER_BEFORE and (after in _CLOSER_AFTER or not after.isalpha())

    # Greedily pair openers with closers of matching length.
    paired: set[int] = set()
    open_stack: list[tuple[int, int]] = []  # (run_index, length)

    for idx, (pos, length) in enumerate(runs):
        is_opener = can_open(pos, length)
        is_closer = can_close(pos, length)

        if is_closer:
            # Try to close a matching opener on the stack.
            for stack_idx in range(len(open_stack) - 1, -1, -1):
                o_idx, o_len = open_stack[stack_idx]
                if o_len == length:
                    paired.add(o_idx)
                    paired.add(idx)
                    open_stack.pop(stack_idx)
                    break
            # Whether or not we found a match, don't push as opener
            # unless it also qualifies as one.
        elif is_opener:
            open_stack.append((idx, length))
        # If neither opener nor closer: lone star — leave unpaired.

    # Build output: for each unpaired run immediately after a word char,
    # replace with LONESTAR placeholders.
    result_parts: list[str] = []
    prev_end = 0
    for idx, (pos, length) in enumerate(runs):
        result_parts.append(text[prev_end:pos])
        if idx not in paired:
            # Lone star: emit as LONESTAR so it passes through as literal *
            result_parts.append("\x00LONESTAR\x00" * length)
        else:
            result_parts.append(text[pos : pos + length])
        prev_end = pos + length
    result_parts.append(text[prev_end:])
    return "".join(result_parts)


def convert_inline(text: str) -> str:
    """Apply inline Markdown→LaTeX conversions to a single line or span.

    Processes (in order): math protection, escaped chars, bold, italic,
    links, CITE markers, Figure references, TODO markers, then restores math.
    """
    # 1. Protect math so inline patterns don't corrupt it.
    text, math_slots = _protect_math(text)

    # 1b. Handle backslash-escaped Markdown characters (\* \_ \[ etc.)
    #     Replace them with NUL-guarded placeholders so the regex patterns
    #     below don't treat them as Markdown syntax.
    text = text.replace(r"\*", "\x00ESTAR\x00")
    text = text.replace(r"\_", "\x00EUSCORE\x00")
    text = text.replace(r"\[", "\x00ELBRACK\x00")
    text = text.replace(r"\]", "\x00ERBRACK\x00")

    # 1c. Protect lone asterisks (mathematical superscript-star, e.g. k*, t*)
    #     that would otherwise be mistaken for italic delimiters.
    #     We use a paired-scan approach: first find all valid *italic* and
    #     **bold** spans, mark their asterisks as consumed, then any remaining
    #     word* pattern is a lone star.
    text = _protect_lone_stars(text)

    # 2. Bold **text** — handle before italic to avoid mis-parsing ***
    text = re.sub(r"\*\*\*(.+?)\*\*\*", lambda m: r"\textbf{\textit{" + m.group(1) + r"}}", text)
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: r"\textbf{" + m.group(1) + r"}", text)

    # 3. Italic *text* or _text_
    text = re.sub(r"\*(.+?)\*", lambda m: r"\textit{" + m.group(1) + r"}", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", lambda m: r"\textit{" + m.group(1) + r"}", text)

    # 3b. Restore escaped characters as their literal LaTeX equivalents.
    text = text.replace("\x00ESTAR\x00", "*")
    text = text.replace("\x00EUSCORE\x00", r"\_")
    text = text.replace("\x00ELBRACK\x00", "[")
    text = text.replace("\x00ERBRACK\x00", "]")
    text = text.replace("\x00LONESTAR\x00", "*")

    # 4. Inline code `code` → \texttt{code}
    text = re.sub(r"`([^`]+)`", lambda m: r"\texttt{" + m.group(1) + r"}", text)

    # 5. Links [text](url)
    def _link(m: re.Match) -> str:
        link_text = m.group(1)
        url = m.group(2)
        return r"\href{" + url + r"}{" + link_text + r"}"

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, text)

    # 6. [CITE: ...] → \cite{key}
    def _cite(m: re.Match) -> str:
        body = m.group(1)
        # Multiple citations separated by semicolons or commas
        parts = re.split(r"[;,]", body)
        keys = ", ".join(cite_to_key(p) for p in parts)
        return r"\cite{" + keys + r"}"

    text = re.sub(r"\[CITE:\s*([^\]]+)\]", _cite, text)

    # 7. [Figure N] → \ref{fig:N} placeholder
    text = re.sub(
        r"\[Figure\s+(\w+)\]",
        lambda m: r"\ref{fig:" + m.group(1).lower() + r"}",
        text,
    )

    # 8. [TODO: ...] → coloured annotation
    def _todo(m: re.Match) -> str:
        content = m.group(1).strip()
        # Escape any % inside TODO text
        content = content.replace("%", r"\%")
        return r"\textcolor{red}{[TODO: " + content + r"]}"

    text = re.sub(r"\[TODO:\s*([^\]]+)\]", _todo, text)

    # 9. Restore math
    text = _restore_math(text, math_slots)

    return text


# ---------------------------------------------------------------------------
# Block-level parser state
# ---------------------------------------------------------------------------

class State:
    """Mutable parser state shared across line-by-line processing."""

    def __init__(self) -> None:
        self.in_itemize: bool = False
        self.in_enumerate: bool = False
        self.in_code_block: bool = False
        self.code_lang: str = ""
        self.in_display_math: bool = False
        self.in_table: bool = False
        self.table_rows: list[list[str]] = []
        self.table_has_header: bool = False
        self.title_emitted: bool = False
        self.seen_titles: set[str] = set()
        self.in_toc: bool = False
        self.results_table_inserted: bool = False
        self.abstract_emitted: bool = False

    def close_list(self, out: list[str]) -> None:
        if self.in_itemize:
            out.append(r"\end{itemize}")
            self.in_itemize = False
        if self.in_enumerate:
            out.append(r"\end{enumerate}")
            self.in_enumerate = False

    def flush_table(self, out: list[str]) -> None:
        """Emit the accumulated Markdown table as LaTeX tabular."""
        if not self.table_rows:
            self.in_table = False
            return

        rows = self.table_rows
        self.table_rows = []
        self.in_table = False

        # Determine column count from the longest row.
        ncols = max(len(r) for r in rows)
        col_spec = "l" * ncols  # simple left-aligned columns

        out.append(r"\begin{table}[htbp]")
        out.append(r"\centering")
        out.append(r"\begin{tabular}{" + col_spec + r"}")
        out.append(r"\toprule")

        for row_idx, row in enumerate(rows):
            # Pad short rows
            while len(row) < ncols:
                row.append("")
            cells = [convert_inline(c.strip()) for c in row]
            out.append(" & ".join(cells) + r" \\")
            if row_idx == 0 and self.table_has_header:
                out.append(r"\midrule")

        out.append(r"\bottomrule")
        out.append(r"\end{tabular}")
        out.append(r"\end{table}")


# ---------------------------------------------------------------------------
# Table parsing helpers
# ---------------------------------------------------------------------------

def _is_table_separator(line: str) -> bool:
    """Return True if line is a Markdown table separator (|---|---|...)."""
    stripped = line.strip()
    if not stripped.startswith("|") and not stripped.endswith("|"):
        return False
    return bool(re.match(r"^[\s|:\-]+$", stripped))


def _parse_table_row(line: str) -> list[str]:
    """Split a pipe-delimited Markdown table row into cells."""
    # Strip leading/trailing pipes
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return stripped.split("|")


# ---------------------------------------------------------------------------
# Section heading conversion
# ---------------------------------------------------------------------------

def _convert_heading(level: int, text: str, state: State) -> str | None:
    """Convert a Markdown heading to a LaTeX sectioning command.

    Returns the LaTeX string, or None if the heading should be suppressed
    (e.g. duplicate title).
    """
    # Strip §N prefix from ## §N SectionName
    text = re.sub(r"^§\d+\s+", "", text).strip()
    # Strip leading "N.M " numeric prefix from ### N.M SubsectionName
    text = re.sub(r"^\d+(?:\.\d+)*\s+", "", text).strip()

    # Apply inline formatting (bold etc.) to heading text
    text = convert_inline(text)

    if level == 1:
        # The very first # heading becomes \title{}; subsequent ones are
        # treated as \section{} (or suppressed if duplicate).
        title_key = text.lower().strip()
        if not state.title_emitted:
            state.title_emitted = True
            state.seen_titles.add(title_key)
            # Title is emitted in the preamble; suppress body emission.
            return None
        if title_key in state.seen_titles:
            # Duplicate title — suppress entirely.
            return None
        state.seen_titles.add(title_key)
        return r"\section{" + text + r"}"
    elif level == 2:
        return r"\section{" + text + r"}"
    elif level == 3:
        return r"\subsection{" + text + r"}"
    else:
        return r"\subsubsection{" + text + r"}"


# ---------------------------------------------------------------------------
# Display math helpers
# ---------------------------------------------------------------------------

def _convert_display_math(inner: str) -> str:
    r"""Wrap display math content in \[...\]."""
    return r"\[" + inner.strip() + r"\]"


# ---------------------------------------------------------------------------
# Main conversion routine
# ---------------------------------------------------------------------------

def convert(md_text: str, has_bib: bool) -> str:
    """Convert Markdown text to a complete LaTeX document string."""
    lines = md_text.splitlines()
    out: list[str] = []
    state = State()

    # Pending display-math accumulator
    display_math_lines: list[str] = []

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        # ------------------------------------------------------------------
        # Code block handling (fenced with ``` or ~~~)
        # ------------------------------------------------------------------
        if state.in_code_block:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                out.append(r"\end{verbatim}")
                state.in_code_block = False
            else:
                # Verbatim: don't escape, pass through raw (but not the
                # line-number prefix).  We do need to handle % specially for
                # LaTeX verbatim: verbatim handles it, so pass raw.
                out.append(raw)
            i += 1
            continue

        # ------------------------------------------------------------------
        # Display math spanning multiple lines ($$...$$ block)
        # ------------------------------------------------------------------
        if state.in_display_math:
            if "$$" in stripped:
                # Close display math
                before_close = stripped[: stripped.index("$$")]
                if before_close.strip():
                    display_math_lines.append(before_close)
                inner = "\n".join(display_math_lines)
                out.append(_convert_display_math(inner))
                display_math_lines = []
                state.in_display_math = False
            else:
                display_math_lines.append(raw)
            i += 1
            continue

        # ------------------------------------------------------------------
        # Table of Contents: skip until a non-TOC heading or blank
        # ------------------------------------------------------------------
        if state.in_toc:
            # TOC lines start with "- [" (links) or are blank
            if stripped == "" or not (stripped.startswith("- [") or stripped.startswith("  ")):
                state.in_toc = False
                # Don't skip this line — fall through to process it
            else:
                i += 1
                continue

        # Detect start of TOC section
        if re.match(r"^##\s+Table of Contents", stripped, re.IGNORECASE):
            state.in_toc = True
            i += 1
            continue

        # ------------------------------------------------------------------
        # Horizontal rule (---, ***, ___)  → skip
        # ------------------------------------------------------------------
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            i += 1
            continue

        # ------------------------------------------------------------------
        # Blank line
        # ------------------------------------------------------------------
        if stripped == "":
            state.close_list(out)
            if state.in_table:
                state.flush_table(out)
            if not (state.in_code_block or state.in_display_math):
                out.append("")
            i += 1
            continue

        # ------------------------------------------------------------------
        # Fenced code block open
        # ------------------------------------------------------------------
        if re.match(r"^```|^~~~", stripped):
            state.close_list(out)
            lang_match = re.match(r"^(?:```|~~~)(\w*)", stripped)
            state.code_lang = lang_match.group(1) if lang_match else ""
            out.append(r"\begin{verbatim}")
            state.in_code_block = True
            i += 1
            continue

        # ------------------------------------------------------------------
        # Display math $$ ... $$ on a single line or multi-line open
        # ------------------------------------------------------------------
        if stripped.startswith("$$"):
            rest = stripped[2:]
            if "$$" in rest:
                # Single-line display math: $$...$$
                inner = rest[: rest.index("$$")]
                out.append(_convert_display_math(inner))
            else:
                # Multi-line open: accumulate until closing $$
                display_math_lines = [rest] if rest.strip() else []
                state.in_display_math = True
            i += 1
            continue

        # ------------------------------------------------------------------
        # Headings
        # ------------------------------------------------------------------
        heading_match = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if heading_match:
            state.close_list(out)
            if state.in_table:
                state.flush_table(out)
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # Special: "Abstract (sketch)" or "# Abstract" → abstract environment.
            # Emit only once; the first occurrence is the sketch (suppress it)
            # and the second is the full abstract (emit it).  We detect the
            # "sketch" variant by "(sketch)" in the heading text.
            if level in (1, 2) and re.match(r"abstract", heading_text, re.IGNORECASE):
                is_sketch = re.search(r"sketch", heading_text, re.IGNORECASE) is not None
                if is_sketch:
                    # Skip the sketch abstract entirely — advance past its body.
                    i += 1
                    while i < len(lines):
                        l = lines[i].strip()
                        if re.match(r"^#{1,4}\s+", l) or (l == "" and i + 1 < len(lines) and re.match(r"^#{1,4}\s+", lines[i + 1].strip())):
                            break
                        i += 1
                    continue
                if state.abstract_emitted:
                    # Suppress duplicate abstract heading
                    i += 1
                    continue
                state.abstract_emitted = True
                out.append(r"\begin{abstract}")
                # Collect subsequent non-heading lines; skip leading blank lines
                # but stop at the first heading after text has been found.
                i += 1
                abstract_lines: list[str] = []
                found_text = False
                while i < len(lines):
                    l = lines[i].strip()
                    if re.match(r"^#{1,4}\s+", l):
                        # Stop at the next heading
                        break
                    if l == "":
                        if found_text:
                            # Blank line after content — end of abstract paragraph
                            break
                        # Blank line before any content — skip
                        i += 1
                        continue
                    found_text = True
                    abstract_lines.append(convert_inline(escape_text(l)))
                    i += 1
                out.append(" ".join(abstract_lines))
                out.append(r"\end{abstract}")
                continue  # i already advanced inside the inner loop

            latex_heading = _convert_heading(level, heading_text, state)
            if latex_heading is not None:
                out.append(latex_heading)

                # After the Results section heading, insert results table
                results_section = re.search(r"Results", heading_text, re.IGNORECASE)
                if results_section and not state.results_table_inserted and level in (1, 2):
                    out.append("")
                    out.append(r"\input{results_table}")
                    out.append("")
                    state.results_table_inserted = True

            i += 1
            continue

        # ------------------------------------------------------------------
        # Table row
        # ------------------------------------------------------------------
        if stripped.startswith("|"):
            if _is_table_separator(stripped):
                # This is the separator line; mark that we have a header row
                if not state.in_table:
                    # Shouldn't happen, but guard anyway
                    i += 1
                    continue
                state.table_has_header = True
                i += 1
                continue
            # Data row
            if not state.in_table:
                state.close_list(out)
                state.in_table = True
                state.table_has_header = False
                state.table_rows = []
            state.table_rows.append(_parse_table_row(stripped))
            i += 1
            continue
        else:
            # Not a table line — flush any pending table
            if state.in_table:
                state.flush_table(out)

        # ------------------------------------------------------------------
        # Bullet list item (- item or * item)
        # ------------------------------------------------------------------
        bullet_match = re.match(r"^(\s*)[-*]\s+(.*)", raw)
        if bullet_match:
            # TOC entries are "- [text](anchor)" — skip
            content = bullet_match.group(2).strip()
            if re.match(r"^\[.*\]\(#", content):
                i += 1
                continue
            if state.in_enumerate:
                out.append(r"\end{enumerate}")
                state.in_enumerate = False
            if not state.in_itemize:
                out.append(r"\begin{itemize}")
                state.in_itemize = True
            out.append(r"\item " + convert_inline(escape_text(content)))
            i += 1
            continue

        # ------------------------------------------------------------------
        # Numbered list item (1. item, 2. item, …)
        # ------------------------------------------------------------------
        enum_match = re.match(r"^(\s*)\d+\.\s+(.*)", raw)
        if enum_match:
            content = enum_match.group(2).strip()
            if state.in_itemize:
                out.append(r"\end{itemize}")
                state.in_itemize = False
            if not state.in_enumerate:
                out.append(r"\begin{enumerate}")
                state.in_enumerate = True
            out.append(r"\item " + convert_inline(escape_text(content)))
            i += 1
            continue

        # ------------------------------------------------------------------
        # Regular paragraph text
        # ------------------------------------------------------------------
        state.close_list(out)
        out.append(convert_inline(escape_text(stripped)))
        i += 1

    # Flush any open environments at end of file
    state.close_list(out)
    if state.in_table:
        state.flush_table(out)
    if state.in_code_block:
        out.append(r"\end{verbatim}")
    if state.in_display_math:
        out.append(_convert_display_math("\n".join(display_math_lines)))

    body = "\n".join(out)

    # ------------------------------------------------------------------
    # Assemble the full document
    # ------------------------------------------------------------------
    has_bib_line = ""
    if has_bib:
        has_bib_line = ""  # bibliography command is always added; .bib presence confirmed

    document = (
        PREAMBLE
        + "\n"
        + TITLE_BLOCK
        + "\n"
        + DOC_BEGIN
        + "\n"
        + body
        + "\n"
        + DOC_END
    )
    return document


# ---------------------------------------------------------------------------
# Post-processing: clean up excess blank lines and fix minor artefacts
# ---------------------------------------------------------------------------

def postprocess(tex: str) -> str:
    """Clean up generated LaTeX — collapse excessive blank lines."""
    # Collapse 3+ consecutive blank lines into 2
    tex = re.sub(r"\n{4,}", "\n\n\n", tex)
    return tex


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not SRC_MD.exists():
        print(f"ERROR: source file not found: {SRC_MD}", file=sys.stderr)
        sys.exit(1)

    md_text = SRC_MD.read_text(encoding="utf-8")
    has_bib = BIB_FILE.exists()

    print(f"Converting {SRC_MD.name} ...")
    if has_bib:
        print(f"  Bibliography: {BIB_FILE.name} found.")
    else:
        print(f"  Bibliography: {BIB_FILE.name} not found — will still emit \\bibliography{{references}}.")

    tex = convert(md_text, has_bib=has_bib)
    tex = postprocess(tex)

    DST_TEX.write_text(tex, encoding="utf-8")
    print(f"Written: {DST_TEX}")
    lines = tex.count("\n")
    print(f"  {lines} lines of LaTeX generated.")


if __name__ == "__main__":
    main()
