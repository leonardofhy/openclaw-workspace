#!/usr/bin/env python3
"""Generate daily literature review report from scout results and paper notes.

Usage:
    python3 report_generator.py                    # today's report
    python3 report_generator.py --discord          # concise Discord version
    python3 report_generator.py --date 2026-03-24  # specific date
    python3 report_generator.py --weekly           # aggregate last 7 days
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

WORKSPACE = Path.home() / ".openclaw" / "workspace"
DAILY_DIR = WORKSPACE / "memory" / "lalm-ke" / "daily"
NOTES_DIR = WORKSPACE / "memory" / "lalm-ke" / "paper-notes"
REPORTS_DIR = WORKSPACE / "memory" / "lalm-ke" / "reports"
WEEKLY_DIR = WORKSPACE / "memory" / "lalm-ke" / "weekly"
QUEUE_PATH = WORKSPACE / "memory" / "lalm-ke" / "reading-queue.md"
INDEX_PATH = NOTES_DIR / "index.json"

TZ = timezone(timedelta(hours=8))

# ─── Data loaders ─────────────────────────────────────────────────────────────

def load_scout_data(target_date: str) -> dict | None:
    """Load scout JSON for a given date."""
    json_path = DAILY_DIR / f"{target_date}.json"
    if not json_path.exists():
        return None
    with open(json_path) as f:
        return json.load(f)


def load_paper_index() -> dict:
    """Load paper notes index."""
    if INDEX_PATH.exists():
        with open(INDEX_PATH) as f:
            return json.load(f)
    return {"papers": {}}


def load_paper_note(arxiv_id: str) -> str | None:
    """Load a paper note markdown file."""
    note_path = NOTES_DIR / f"{arxiv_id}.md"
    if note_path.exists():
        return note_path.read_text(encoding="utf-8")
    return None


def extract_note_field(note: str, field: str) -> str:
    """Extract a named field value from note metadata (## Section or **field:** value)."""
    # Try ## Section header style
    section_re = re.compile(
        rf"^##\s+{re.escape(field)}\s*$\n+(.*?)(?=\n##|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    m = section_re.search(note)
    if m:
        return m.group(1).strip()

    # Try **Field:** value style
    inline_re = re.compile(
        rf"\*\*{re.escape(field)}:\*\*\s*(.+?)(?:\n|$)",
        re.IGNORECASE,
    )
    m = inline_re.search(note)
    if m:
        return m.group(1).strip()

    return ""


def get_note_summary(note: str) -> str:
    """Get the Summary section from a note."""
    return extract_note_field(note, "Summary")[:300]


def get_note_relevance_score(note: str) -> int:
    """Parse relevance score from note."""
    m = re.search(r"\*\*Relevance:\*\*\s*(\d)/3", note)
    if m:
        return int(m.group(1))
    m = re.search(r"Score:\s*(\d)/3", note)
    if m:
        return int(m.group(1))
    return 0


def load_reading_queue() -> list[str]:
    """Load reading queue items from markdown file."""
    if not QUEUE_PATH.exists():
        return []
    text = QUEUE_PATH.read_text(encoding="utf-8")
    # Find unchecked items: - [ ] or * [ ]
    unchecked = re.findall(r"^[\s\-\*]+\[ \]\s*(.+)$", text, re.MULTILINE)
    checked = re.findall(r"^[\s\-\*]+\[x\]\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return unchecked, checked


# ─── Report building ──────────────────────────────────────────────────────────

def build_report(target_date: str, discord: bool = False) -> str:
    """Build the daily report for a given date."""
    scout = load_scout_data(target_date)
    index = load_paper_index()

    # Papers read today (from index, filter by read_date)
    papers_read_today = {
        aid: info for aid, info in index.get("papers", {}).items()
        if info.get("read_date") == target_date
    }

    # ─ Stats ─
    total_scanned = scout["total_found"] if scout else 0
    total_in_scout = scout["shown"] if scout else 0
    total_read = len(papers_read_today)

    # ─ Categorise scout papers ─
    high_relevance = []    # score >= 30
    medium_relevance = []  # score 20-29
    low_relevance = []     # score < 20

    if scout:
        for paper in scout.get("papers", []):
            score = paper.get("score", 0)
            aid = paper.get("arxiv_id", "")
            if score >= 30:
                high_relevance.append(paper)
            elif score >= 20:
                medium_relevance.append(paper)
            else:
                low_relevance.append(paper)

    # ─ Reading queue ─
    try:
        queue_pending, queue_done = load_reading_queue()
    except Exception:
        queue_pending, queue_done = [], []

    if discord:
        return build_discord_report(
            target_date=target_date,
            total_scanned=total_scanned,
            total_in_scout=total_in_scout,
            total_read=total_read,
            high_relevance=high_relevance,
            medium_relevance=medium_relevance,
            low_relevance=low_relevance,
            papers_read_today=papers_read_today,
            index=index,
            queue_pending=queue_pending,
            queue_done=queue_done,
        )
    else:
        return build_full_report(
            target_date=target_date,
            total_scanned=total_scanned,
            total_in_scout=total_in_scout,
            total_read=total_read,
            high_relevance=high_relevance,
            medium_relevance=medium_relevance,
            low_relevance=low_relevance,
            papers_read_today=papers_read_today,
            index=index,
            queue_pending=queue_pending,
            queue_done=queue_done,
        )


def build_full_report(
    target_date: str,
    total_scanned: int,
    total_in_scout: int,
    total_read: int,
    high_relevance: list,
    medium_relevance: list,
    low_relevance: list,
    papers_read_today: dict,
    index: dict,
    queue_pending: list,
    queue_done: list,
) -> str:
    lines = [
        f"# LALM-KE Literature Review — {target_date}",
        "",
        "## 📊 Stats",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Papers scanned (arXiv) | {total_scanned} |",
        f"| Papers in scout (scored > 0) | {total_in_scout} |",
        f"| High relevance (≥30) | {len(high_relevance)} |",
        f"| Medium relevance (20-29) | {len(medium_relevance)} |",
        f"| Low relevance (<20) | {len(low_relevance)} |",
        f"| Read in detail today | {total_read} |",
        f"| Reading queue pending | {len(queue_pending)} |",
        "",
    ]

    # ─ High relevance ─
    if high_relevance:
        lines += ["## 🔴 High Relevance (Score ≥30)", ""]
        for paper in high_relevance:
            aid = paper.get("arxiv_id", "")
            title = paper.get("title", "Unknown")
            score = paper.get("score", 0)
            url = paper.get("url", f"https://arxiv.org/abs/{aid}")
            authors = paper.get("authors", "")
            abstract = paper.get("abstract_snippet", "")[:200]

            lines += [f"### [{title}]({url})", f"**Score:** {score} | **arXiv:** {aid}"]
            if authors:
                lines.append(f"**Authors:** {authors}")

            # If we have a note, include summary
            if aid in papers_read_today:
                note = load_paper_note(aid)
                if note:
                    summary = get_note_summary(note)
                    relevance = get_note_relevance_score(note)
                    if summary:
                        lines += ["", f"**Summary:** {summary}"]
                    lines += [f"**LALM-KE Relevance:** {relevance}/3", ""]
                else:
                    lines += ["", f"> {abstract}...", ""]
            else:
                lines += ["", f"> {abstract}...", ""]
    else:
        lines += ["## 🔴 High Relevance (Score ≥30)", "", "_No papers with score ≥30 today._", ""]

    # ─ Medium relevance ─
    if medium_relevance:
        lines += ["## 🟡 Medium Relevance (Score 20-29)", ""]
        for paper in medium_relevance:
            aid = paper.get("arxiv_id", "")
            title = paper.get("title", "Unknown")
            score = paper.get("score", 0)
            url = paper.get("url", f"https://arxiv.org/abs/{aid}")
            abstract = paper.get("abstract_snippet", "")[:150]
            lines.append(f"- **[{title}]({url})** (score: {score}) — {abstract}...")
        lines.append("")
    else:
        lines += ["## 🟡 Medium Relevance (Score 20-29)", "", "_No papers in this range today._", ""]

    # ─ Low relevance ─
    if low_relevance:
        lines += ["## 🟢 Low Relevance (Score <20)", ""]
        for paper in low_relevance:
            title = paper.get("title", "Unknown")
            url = paper.get("url", "#")
            score = paper.get("score", 0)
            lines.append(f"- [{title}]({url}) (score: {score})")
        lines.append("")
    else:
        lines += ["## 🟢 Low Relevance (Score <20)", "", "_None._", ""]

    # ─ Papers read today (detailed notes) ─
    if papers_read_today:
        lines += ["## 📖 Read in Detail Today", ""]
        for aid, info in papers_read_today.items():
            title = info.get("title", aid)
            relevance = info.get("relevance", 0)
            source = info.get("source", "unknown")
            lines.append(f"- **{title}** — Relevance: {relevance}/3 | Source: {source}")
            note_path = NOTES_DIR / f"{aid}.md"
            lines.append(f"  → Notes: `memory/lalm-ke/paper-notes/{aid}.md`")
        lines.append("")

    # ─ Reading queue ─
    lines += ["## 📚 Reading Queue", ""]
    if queue_pending:
        lines.append(f"**Pending ({len(queue_pending)}):**")
        for item in queue_pending[:10]:
            lines.append(f"- [ ] {item}")
        if len(queue_pending) > 10:
            lines.append(f"- _(+{len(queue_pending) - 10} more)_")
        lines.append("")
    else:
        lines += ["_Queue file not found or empty. Create `memory/lalm-ke/reading-queue.md`._", ""]

    if queue_done:
        lines.append(f"**Done ({len(queue_done)}):** {len(queue_done)} papers completed")
        lines.append("")

    lines += [
        "---",
        f"*Generated by report_generator.py · {datetime.now(TZ).strftime('%Y-%m-%d %H:%M %Z')}*",
    ]
    return "\n".join(lines)


def build_discord_report(
    target_date: str,
    total_scanned: int,
    total_in_scout: int,
    total_read: int,
    high_relevance: list,
    medium_relevance: list,
    low_relevance: list,
    papers_read_today: dict,
    index: dict,
    queue_pending: list,
    queue_done: list,
) -> str:
    """Build compact Discord-friendly report (<2000 chars, bullets only)."""
    parts = [f"**LALM-KE Scout — {target_date}**"]
    parts.append(
        f"📊 {total_scanned} scanned · {total_in_scout} scored · "
        f"{len(high_relevance)}🔴 {len(medium_relevance)}🟡 {len(low_relevance)}🟢 · "
        f"{total_read} read"
    )
    parts.append("")

    if high_relevance:
        parts.append("**🔴 High relevance:**")
        for p in high_relevance[:3]:
            title = p.get("title", "?")[:60]
            score = p.get("score", 0)
            aid = p.get("arxiv_id", "")
            url = p.get("url", f"https://arxiv.org/abs/{aid}")
            # Check if we have a note
            note_snippet = ""
            if aid in papers_read_today:
                note = load_paper_note(aid)
                if note:
                    summary = get_note_summary(note)
                    note_snippet = f" — {summary[:80]}..." if summary else ""
            parts.append(f"• [{title}](<{url}>) ({score}){note_snippet}")
        if len(high_relevance) > 3:
            parts.append(f"  _(+{len(high_relevance) - 3} more)_")
        parts.append("")

    if medium_relevance:
        parts.append("**🟡 Medium relevance:**")
        for p in medium_relevance[:5]:
            title = p.get("title", "?")[:55]
            score = p.get("score", 0)
            aid = p.get("arxiv_id", "")
            url = p.get("url", f"https://arxiv.org/abs/{aid}")
            parts.append(f"• [{title}](<{url}>) ({score})")
        if len(medium_relevance) > 5:
            parts.append(f"  _(+{len(medium_relevance) - 5} more)_")
        parts.append("")

    if queue_pending:
        parts.append(f"📚 Queue: {len(queue_pending)} pending")

    parts.append(f"_Generated {datetime.now(TZ).strftime('%H:%M %Z')}_")

    result = "\n".join(parts)

    # Hard truncate at 1990 chars
    if len(result) > 1990:
        result = result[:1987] + "..."

    return result


# ─── Weekly report ────────────────────────────────────────────────────────────

def build_weekly_report(end_date_str: str) -> str:
    """Aggregate last 7 days into a weekly report."""
    end_date = date.fromisoformat(end_date_str)
    dates = [(end_date - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    total_scanned = 0
    total_read = 0
    all_high: list[dict] = []
    all_medium: list[dict] = []
    daily_counts: list[dict] = []

    index = load_paper_index()

    for d in dates:
        scout = load_scout_data(d)
        papers_read = {
            aid: info for aid, info in index.get("papers", {}).items()
            if info.get("read_date") == d
        }

        if scout:
            scanned = scout.get("total_found", 0)
            shown = scout.get("shown", 0)
            papers = scout.get("papers", [])
            high = [p for p in papers if p.get("score", 0) >= 30]
            medium = [p for p in papers if 20 <= p.get("score", 0) < 30]
            total_scanned += scanned
            all_high.extend(high)
            all_medium.extend(medium)
            daily_counts.append({
                "date": d,
                "scanned": scanned,
                "shown": shown,
                "high": len(high),
                "medium": len(medium),
                "read": len(papers_read),
            })
        else:
            daily_counts.append({
                "date": d, "scanned": 0, "shown": 0, "high": 0, "medium": 0, "read": 0,
            })
        total_read += len(papers_read)

    # Dedup papers by arxiv_id
    seen_ids: set[str] = set()
    dedup_high = []
    for p in all_high:
        aid = p.get("arxiv_id", "")
        if aid not in seen_ids:
            seen_ids.add(aid)
            dedup_high.append(p)

    dedup_medium = []
    for p in all_medium:
        aid = p.get("arxiv_id", "")
        if aid not in seen_ids:
            seen_ids.add(aid)
            dedup_medium.append(p)

    lines = [
        f"# LALM-KE Weekly Report — {dates[0]} to {dates[-1]}",
        "",
        "## 📊 Weekly Summary",
        "",
        f"- **Total scanned:** {total_scanned} papers",
        f"- **High relevance:** {len(dedup_high)} unique papers (≥30)",
        f"- **Medium relevance:** {len(dedup_medium)} unique papers (20-29)",
        f"- **Read in detail:** {total_read} papers",
        "",
        "## 📅 Daily Breakdown",
        "",
        "| Date | Scanned | High🔴 | Medium🟡 | Read |",
        "|------|---------|--------|----------|------|",
    ]
    for dc in daily_counts:
        lines.append(
            f"| {dc['date']} | {dc['scanned']} | {dc['high']} | {dc['medium']} | {dc['read']} |"
        )
    lines.append("")

    if dedup_high:
        lines += ["## 🔴 Notable High-Relevance Papers", ""]
        for p in dedup_high[:10]:
            title = p.get("title", "?")
            url = p.get("url", "#")
            score = p.get("score", 0)
            lines.append(f"- **[{title}]({url})** — score {score}")
        lines.append("")

    lines += [
        "---",
        f"*Generated by report_generator.py (weekly) · {datetime.now(TZ).strftime('%Y-%m-%d %H:%M %Z')}*",
    ]
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LALM-KE Daily Report Generator")
    parser.add_argument("--date", type=str, default=None, help="Date to report on (YYYY-MM-DD, default: today)")
    parser.add_argument("--discord", action="store_true", help="Output concise Discord version (<2000 chars)")
    parser.add_argument("--weekly", action="store_true", help="Generate weekly aggregate report (last 7 days)")
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout, don't save file")
    args = parser.parse_args()

    target_date = args.date or date.today().isoformat()

    if args.weekly:
        report = build_weekly_report(target_date)
        report_type = "weekly"
    else:
        # Check if scout data exists
        scout_path = DAILY_DIR / f"{target_date}.json"
        if not scout_path.exists():
            print(f"[WARN] No scout data found for {target_date}: {scout_path}")
            print("[INFO] Generating partial report from paper notes only...")

        report = build_report(target_date, discord=args.discord)
        report_type = "discord" if args.discord else "daily"

    if args.dry_run or args.discord:
        print(report)
        return

    # Save report
    if args.weekly:
        output_dir = WEEKLY_DIR
        filename = f"{target_date}-weekly.md"
    else:
        output_dir = REPORTS_DIR
        filename = f"{target_date}.md"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[OK] Report saved: {output_path}")
    print(f"     Type: {report_type} | Date: {target_date}")

    # Also print a short preview
    lines = report.split("\n")
    preview = "\n".join(lines[:20])
    print(f"\n--- Preview ---\n{preview}\n...")


if __name__ == "__main__":
    main()
