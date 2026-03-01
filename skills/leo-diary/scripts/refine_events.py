#!/usr/bin/env python3
"""Refine people_db events using LLM-quality analysis.

Two modes:
  1. export: Output events needing refinement as structured JSON for LLM
  2. apply:  Apply refined JSON back to events.jsonl

Usage:
  # Step 1: Export a batch for one person
  refine_events.py export "智凱" > /tmp/refine_智凱.json

  # Step 2: LLM processes and outputs refined JSON (same structure + new fields)
  # The LLM adds: summary_refined, type_refined, sentiment_refined, is_real_interaction

  # Step 3: Apply refined data back
  refine_events.py apply --file /tmp/refined_智凱.json

  # Or: export all people needing refinement
  refine_events.py export-all --out-dir /tmp/refine_batches/

  # Batch apply all refined files
  refine_events.py apply-all --dir /tmp/refined_batches/
"""

import argparse
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
PEOPLE_FILE = WORKSPACE / "memory" / "people" / "people.jsonl"
EVENTS_FILE = WORKSPACE / "memory" / "people" / "events.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _save_jsonl(path: Path, items: list[dict]):
    import tempfile, os
    content = "\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp, path)
    except:
        try: os.close(fd)
        except: pass
        try: os.unlink(tmp)
        except: pass
        raise


def find_person(people, name):
    name_lower = name.lower()
    for p in people:
        if p.get("name", "").lower() == name_lower:
            return p
        for a in p.get("aliases", []):
            if a.lower() == name_lower:
                return p
    return None


def cmd_export(args):
    people = _load_jsonl(PEOPLE_FILE)
    events = _load_jsonl(EVENTS_FILE)
    p = find_person(people, args.name)
    if not p:
        print(f"❌ 找不到: {args.name}", file=sys.stderr)
        sys.exit(1)

    person_events = sorted(
        [e for e in events if e.get("person_id") == p["id"]],
        key=lambda e: e.get("date", "")
    )

    # Build export with LLM instructions
    export = {
        "person": p["name"],
        "person_id": p["id"],
        "aliases": p.get("aliases", []),
        "relationship": p.get("relationship", ""),
        "instructions": (
            "For each event below, provide:\n"
            "  - summary_refined: 1-2 sentence clean summary in 繁體中文, describing "
            "what happened between Leo and this person. Remove raw diary fragments.\n"
            "  - type_refined: one of [meeting, chat, meal, conflict, favor, milestone, work, social, interaction]\n"
            "  - sentiment_refined: one of [positive, negative, mixed, neutral]\n"
            "  - is_real_interaction: true if Leo directly interacted with this person; "
            "false if the person is merely mentioned in passing.\n"
            "Output the same JSON array with these 4 new fields added to each event."
        ),
        "events": [
            {
                "id": e["id"],
                "date": e["date"],
                "type": e.get("type", ""),
                "sentiment": e.get("sentiment", ""),
                "summary": e.get("summary", ""),
            }
            for e in person_events
        ],
    }
    json.dump(export, sys.stdout, ensure_ascii=False, indent=2)
    print(f"\n# {len(person_events)} events exported for {p['name']}", file=sys.stderr)


def cmd_export_all(args):
    people = _load_jsonl(PEOPLE_FILE)
    events = _load_jsonl(EVENTS_FILE)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for p in people:
        person_events = [e for e in events if e.get("person_id") == p["id"]]
        if not person_events:
            continue

        export = {
            "person": p["name"],
            "person_id": p["id"],
            "aliases": p.get("aliases", []),
            "relationship": p.get("relationship", ""),
            "event_count": len(person_events),
            "events": [
                {
                    "id": e["id"],
                    "date": e["date"],
                    "type": e.get("type", ""),
                    "sentiment": e.get("sentiment", ""),
                    "summary": e.get("summary", ""),
                }
                for e in sorted(person_events, key=lambda e: e.get("date", ""))
            ],
        }
        out_path = out_dir / f"{p['id']}_{p['name']}.json"
        out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2))
        print(f"  📄 {out_path.name}: {len(person_events)} events", file=sys.stderr)

    print(f"\n💾 Exported to {out_dir}", file=sys.stderr)


def cmd_apply(args):
    """Apply refined events back to events.jsonl."""
    refined_path = Path(args.file)
    if not refined_path.exists():
        print(f"❌ 檔案不存在: {args.file}", file=sys.stderr)
        sys.exit(1)

    refined_data = json.loads(refined_path.read_text())
    refined_events = refined_data if isinstance(refined_data, list) else refined_data.get("events", [])

    # Build lookup: event_id → refined fields
    refined_map = {}
    for e in refined_events:
        eid = e.get("id")
        if eid:
            refined_map[eid] = e

    if not refined_map:
        print("沒有可套用的 refined events。", file=sys.stderr)
        return

    # Load and update events.jsonl
    events = _load_jsonl(EVENTS_FILE)
    updated = 0
    removed = 0
    for e in events[:]:  # iterate copy
        eid = e.get("id")
        if eid in refined_map:
            r = refined_map[eid]

            # Remove false positives
            if r.get("is_real_interaction") is False:
                events.remove(e)
                removed += 1
                continue

            # Apply refined fields
            if r.get("summary_refined"):
                e["summary"] = r["summary_refined"]
            if r.get("type_refined"):
                e["type"] = r["type_refined"]
            if r.get("sentiment_refined"):
                e["sentiment"] = r["sentiment_refined"]
            updated += 1

    _save_jsonl(EVENTS_FILE, events)
    print(f"✅ Applied: {updated} updated, {removed} removed (false positives)")


def cmd_apply_all(args):
    """Apply all refined files in a directory."""
    dir_path = Path(args.dir)
    if not dir_path.exists():
        print(f"❌ 目錄不存在: {args.dir}", file=sys.stderr)
        sys.exit(1)

    total_updated = 0
    total_removed = 0

    for f in sorted(dir_path.glob("*.json")):
        data = json.loads(f.read_text())
        refined_events = data if isinstance(data, list) else data.get("events", [])

        refined_map = {}
        for e in refined_events:
            eid = e.get("id")
            if eid:
                refined_map[eid] = e

        if not refined_map:
            continue

        events = _load_jsonl(EVENTS_FILE)
        updated = 0
        removed = 0
        for e in events[:]:
            eid = e.get("id")
            if eid in refined_map:
                r = refined_map[eid]
                if r.get("is_real_interaction") is False:
                    events.remove(e)
                    removed += 1
                    continue
                if r.get("summary_refined"):
                    e["summary"] = r["summary_refined"]
                if r.get("type_refined"):
                    e["type"] = r["type_refined"]
                if r.get("sentiment_refined"):
                    e["sentiment"] = r["sentiment_refined"]
                updated += 1

        _save_jsonl(EVENTS_FILE, events)
        name = data.get("person", f.stem) if isinstance(data, dict) else f.stem
        print(f"  {name}: {updated} updated, {removed} removed")
        total_updated += updated
        total_removed += removed

    print(f"\n✅ Total: {total_updated} updated, {total_removed} removed")


def main():
    parser = argparse.ArgumentParser(description="Refine people_db events with LLM")
    sub = parser.add_subparsers(dest="command")

    p_exp = sub.add_parser("export", help="Export events for one person")
    p_exp.add_argument("name")

    p_exp_all = sub.add_parser("export-all", help="Export all people")
    p_exp_all.add_argument("--out-dir", default="/tmp/refine_batches")

    p_apply = sub.add_parser("apply", help="Apply refined JSON")
    p_apply.add_argument("--file", required=True)

    p_apply_all = sub.add_parser("apply-all", help="Apply all refined files in dir")
    p_apply_all.add_argument("--dir", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"export": cmd_export, "export-all": cmd_export_all,
     "apply": cmd_apply, "apply-all": cmd_apply_all}[args.command](args)


if __name__ == "__main__":
    main()
