#!/usr/bin/env python3
"""Title Workbench: generate, score, and select paper titles.

Minimal deterministic CLI for Leo's paper title workflow.

Examples:
  python3 skills/paper-writing/scripts/title_workbench.py generate \
    --md memory/paper/title-brainstorm.md --batch-label "Batch 6" --n 10

  python3 skills/paper-writing/scripts/title_workbench.py score \
    --md memory/paper/title-brainstorm.md --batch-label "Batch 6"

  python3 skills/paper-writing/scripts/title_workbench.py select \
    --md memory/paper/title-brainstorm.md --batch-label "Batch 6" --top-k 5
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_MD = Path("memory/paper/title-brainstorm.md")

STRATEGY_TEMPLATES = {
    "method": [
        "Auditing {obj} in {domain}",
        "Disentangling {signal_a} from {signal_b} in {domain}",
        "Revisiting {domain} with {method}",
        "Quantifying {signal_a} Reliance in {domain}",
    ],
    "finding": [
        "Most {obj} Don't Need {signal_a}",
        "Minimal {signal_a}, Maximal Scores in {domain}",
        "Scoring Without {signal_a}: Evidence from {scope}",
        "From Full Signals to Fragments: {domain} Under the Microscope",
    ],
    "redesign": [
        "Towards {goal}: Auditing and Repairing {shortcut}",
        "Designing Benchmarks That Must Be {verb_pp}",
        "A Roadmap to {goal}: Evidence from {method} at Scale",
        "Benchmarking for {good}, Not {bad}",
    ],
    "short": [
        "Do Models Actually Listen?",
        "The Benchmark Wasn't Listening",
        "Hearing Without Listening",
        "Scoring Without Sound",
    ],
}

PLACEHOLDERS = {
    "obj": ["Audio Questions", "Benchmark Items", "Audio-Language Tasks"],
    "domain": ["Audio-Language Benchmarks", "Audio-Language Evaluation"],
    "signal_a": ["Audio", "Acoustic Evidence", "Sound"],
    "signal_b": ["Text Priors", "Heuristic Shortcuts", "Language Priors"],
    "method": ["Audio-Need Analysis", "Necessity Audits", "Fine-Grained Necessity Audits"],
    "scope": ["8 Models and 3 Suites", "Large-Scale Necessity Audits"],
    "goal": ["Audio-Faithful Evaluation", "Audio-Required Evaluation"],
    "shortcut": ["Text-Prior Shortcuts", "Read-Not-Listen Shortcuts"],
    "verb_pp": ["Heard", "Listened To"],
    "good": ["Ears", "Acoustic Grounding"],
    "bad": ["Priors", "Text Shortcuts"],
}


@dataclass
class ScoredTitle:
    title: str
    score: float
    breakdown: dict[str, float]


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def ensure_md(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"markdown file not found: {path}")
    return path.read_text(encoding="utf-8")


def append_section(path: Path, section: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        if not section.startswith("\n"):
            f.write("\n")
        f.write(section)
        if not section.endswith("\n"):
            f.write("\n")


def choose_template(strategy: str, n: int, rng: random.Random) -> list[str]:
    keys = [strategy] if strategy != "mixed" else list(STRATEGY_TEMPLATES.keys())
    out = []
    for _ in range(n):
        k = rng.choice(keys)
        out.append(rng.choice(STRATEGY_TEMPLATES[k]))
    return out


def fill_template(template: str, rng: random.Random) -> str:
    values = {}
    for key in re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template):
        if key not in PLACEHOLDERS:
            raise KeyError(f"unknown placeholder: {key}")
        values[key] = rng.choice(PLACEHOLDERS[key])
    title = template.format(**values)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def dedup_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for s in items:
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def extract_batch_titles(md_text: str, batch_label: str) -> list[str]:
    # Capture block starting from "## <batch_label>" until next "## "
    pattern = re.compile(
        rf"^##\s+{re.escape(batch_label)}[\s\S]*?(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    m = pattern.search(md_text)
    if not m:
        raise ValueError(f"batch not found: {batch_label}")
    block = m.group(0)
    titles = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*", block, flags=re.MULTILINE)
    if not titles:
        raise ValueError(f"no title entries found in batch: {batch_label}")
    return titles


def all_batch_labels(md_text: str) -> list[str]:
    return re.findall(r"^##\s+(Batch\s+\d+\s+—\s+[^\n]+)", md_text, flags=re.MULTILINE)


def latest_batch_label(md_text: str) -> str:
    labels = all_batch_labels(md_text)
    if not labels:
        raise ValueError("no batch sections found")
    return labels[-1]


def score_title(title: str) -> ScoredTitle:
    words = re.findall(r"[A-Za-z0-9\-']+", title)
    wc = len(words)

    # Heuristic rubric: 0-10
    length_score = max(0.0, 3.0 - abs(wc - 11) * 0.3)  # sweet spot ~11 words
    keyword_hits = sum(
        1
        for kw in ["audio", "benchmark", "evaluation", "necessity", "listen", "text prior", "acoustic"]
        if kw in title.lower()
    )
    specificity_score = min(2.5, keyword_hits * 0.5)
    clarity_score = 2.0 if ":" not in title or len(title.split(":")) == 2 else 1.0
    novelty_score = 1.5 if any(k in title.lower() for k in ["without", "minimal", "revisiting", "towards"]) else 0.8
    penalty = -1.0 if wc < 4 or wc > 20 else 0.0

    breakdown = {
        "length": round(length_score, 2),
        "specificity": round(specificity_score, 2),
        "clarity": round(clarity_score, 2),
        "novelty": round(novelty_score, 2),
        "penalty": round(penalty, 2),
    }
    total = round(sum(breakdown.values()), 2)
    return ScoredTitle(title=title, score=total, breakdown=breakdown)


def cmd_generate(args: argparse.Namespace) -> int:
    path = Path(args.md)
    _ = ensure_md(path)

    rng = random.Random(args.seed)
    templates = choose_template(args.strategy, args.n * 2, rng)
    candidates = [fill_template(t, rng) for t in templates]
    titles = dedup_keep_order(candidates)[: args.n]

    if len(titles) < args.n:
        eprint(f"WARN: generated {len(titles)} unique titles (< requested {args.n})")

    timestamp = dt.datetime.now().strftime("%H:%M")
    section = [f"\n## {args.batch_label} — {timestamp}（策略：{args.strategy}）\n"]
    start_idx = args.start_index
    for i, t in enumerate(titles, start=start_idx):
        section.append(f"\n{i}. **{t}**\n   — auto-generated via title_workbench\n")

    append_section(path, "".join(section))
    print(f"Appended {len(titles)} titles to {path} under '{args.batch_label}'.")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    path = Path(args.md)
    md = ensure_md(path)
    label = args.batch_label or latest_batch_label(md)
    titles = extract_batch_titles(md, label)
    scored = sorted((score_title(t) for t in titles), key=lambda x: x.score, reverse=True)

    print(f"Batch: {label}")
    for i, s in enumerate(scored, start=1):
        print(f"{i:>2}. {s.score:>4.2f} | {s.title}")
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    path = Path(args.md)
    md = ensure_md(path)
    label = args.batch_label or latest_batch_label(md)
    titles = extract_batch_titles(md, label)
    scored = sorted((score_title(t) for t in titles), key=lambda x: x.score, reverse=True)
    top = scored[: args.top_k]

    print(f"Top {len(top)} from: {label}")
    for i, s in enumerate(top, start=1):
        b = s.breakdown
        print(
            f"{i}. {s.title}\n"
            f"   score={s.score:.2f} (len={b['length']}, spec={b['specificity']}, clarity={b['clarity']}, novelty={b['novelty']}, penalty={b['penalty']})"
        )
    return 0


def cmd_shortlist(args: argparse.Namespace) -> int:
    path = Path(args.md)
    md = ensure_md(path)

    labels = args.batch_label or all_batch_labels(md)[-args.last_batches :]
    if not labels:
        raise ValueError("no batches selected for shortlist")

    all_titles: list[str] = []
    for label in labels:
        all_titles.extend(extract_batch_titles(md, label))

    unique_titles = dedup_keep_order(all_titles)
    scored = sorted((score_title(t) for t in unique_titles), key=lambda x: x.score, reverse=True)
    top = scored[: args.top_k]

    print(f"Shortlist top {len(top)} from {len(labels)} batches ({len(unique_titles)} unique titles)")
    for i, s in enumerate(top, start=1):
        print(f"{i}. {s.score:.2f} | {s.title}")

    if args.append_md:
        ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"\n## 🔖 Auto Shortlist — {ts}\n",
            f"\n來源 batches：{', '.join(labels)}\n",
        ]
        for i, s in enumerate(top, start=1):
            b = s.breakdown
            lines.append(
                f"\n{i}. **{s.title}**\n"
                f"   - score: {s.score:.2f} (len={b['length']}, spec={b['specificity']}, clarity={b['clarity']}, novelty={b['novelty']}, penalty={b['penalty']})\n"
            )
        append_section(path, "".join(lines))
        print(f"Appended shortlist section to {path}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate/score/select paper titles")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate and append a batch of titles")
    g.add_argument("--md", default=str(DEFAULT_MD), help="Path to brainstorm markdown")
    g.add_argument("--batch-label", required=True, help="Batch label, e.g. 'Batch 6'")
    g.add_argument("--strategy", choices=["mixed", "method", "finding", "redesign", "short"], default="mixed")
    g.add_argument("--n", type=int, default=10)
    g.add_argument("--start-index", type=int, default=1)
    g.add_argument("--seed", type=int, default=42)
    g.set_defaults(func=cmd_generate)

    s = sub.add_parser("score", help="Score titles in a batch")
    s.add_argument("--md", default=str(DEFAULT_MD))
    s.add_argument("--batch-label", default="", help="Default: latest batch")
    s.set_defaults(func=cmd_score)

    sel = sub.add_parser("select", help="Select top-k titles from a batch")
    sel.add_argument("--md", default=str(DEFAULT_MD))
    sel.add_argument("--batch-label", default="", help="Default: latest batch")
    sel.add_argument("--top-k", type=int, default=5)
    sel.set_defaults(func=cmd_select)

    sh = sub.add_parser("shortlist", help="Create top-k shortlist across multiple batches")
    sh.add_argument("--md", default=str(DEFAULT_MD))
    sh.add_argument("--batch-label", action="append", default=[], help="Repeatable; default uses latest N batches")
    sh.add_argument("--last-batches", type=int, default=3, help="Used when --batch-label is omitted")
    sh.add_argument("--top-k", type=int, default=5)
    sh.add_argument("--append-md", action="store_true", help="Append shortlist section into markdown")
    sh.set_defaults(func=cmd_shortlist)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if getattr(args, "n", 1) <= 0:
        eprint("ERROR: --n must be > 0")
        return 2
    if getattr(args, "top_k", 1) <= 0:
        eprint("ERROR: --top-k must be > 0")
        return 2
    if getattr(args, "last_batches", 1) <= 0:
        eprint("ERROR: --last-batches must be > 0")
        return 2

    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001
        eprint(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
