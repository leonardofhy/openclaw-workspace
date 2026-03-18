#!/usr/bin/env python3
"""Feed Recommender CLI — multi-source feed aggregation and recommendation.

Usage:
    python3 feed.py sources                       # list available sources
    python3 feed.py enable <name>                  # enable a source
    python3 feed.py disable <name>                 # disable a source
    python3 feed.py fetch [--source X] [--limit N] # fetch articles
    python3 feed.py recommend [--limit 10]         # score + rank top-N
    python3 feed.py mark-seen <uid...>             # mark as seen
    python3 feed.py feedback <uid> <+|->           # record feedback
    python3 feed.py profile                        # show interest profile
    python3 feed.py stats                          # show stats
    python3 feed.py config                         # show current config
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure this script can find its sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

import feed_engine as engine
from sources import discover_sources


def cmd_sources(args: argparse.Namespace) -> None:
    """List all available sources with enabled/disabled status."""
    cfg = engine.load_config()
    available = discover_sources()
    src_cfg = cfg.get('sources', {})

    print(f"{'Source':<10} {'Status':<10} {'Limit':<8} {'Notes'}")
    print("-" * 50)
    for name in sorted(available.keys()):
        settings = src_cfg.get(name, {})
        enabled = settings.get('enabled', True)
        limit = settings.get('limit', '-')
        status = "enabled" if enabled else "disabled"
        notes = ""
        if 'categories' in settings:
            notes = f"categories: {', '.join(settings['categories'])}"
        print(f"{name:<10} {status:<10} {str(limit):<8} {notes}")

    # Show configured but not discovered sources
    for name in sorted(src_cfg.keys()):
        if name not in available:
            print(f"{name:<10} {'missing':<10} {'-':<8} plugin not found")


def cmd_enable(args: argparse.Namespace) -> None:
    cfg = engine.load_config()
    name = args.name
    if name not in cfg.get('sources', {}):
        cfg.setdefault('sources', {})[name] = {"enabled": True}
    else:
        cfg['sources'][name]['enabled'] = True
    engine.save_config(cfg)
    print(f"Enabled source: {name}")


def cmd_disable(args: argparse.Namespace) -> None:
    cfg = engine.load_config()
    name = args.name
    if name not in cfg.get('sources', {}):
        cfg.setdefault('sources', {})[name] = {"enabled": False}
    else:
        cfg['sources'][name]['enabled'] = False
    engine.save_config(cfg)
    print(f"Disabled source: {name}")


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch articles from enabled sources (or a specific one)."""
    cfg = engine.load_config()
    sources = engine.load_sources(cfg)

    if args.source:
        sources = [s for s in sources if s.name == args.source]
        if not sources:
            print(f"ERROR: source '{args.source}' not found or disabled", file=sys.stderr)
            sys.exit(1)

    print(f"Fetching from {len(sources)} source(s)...", file=sys.stderr)
    articles, errors = engine.fetch_all(sources, limit_per_source=args.limit, config=cfg)

    output = {
        'total': len(articles),
        'articles': [a.to_dict() for a in articles],
    }
    if errors:
        output['errors'] = errors
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_recommend(args: argparse.Namespace) -> None:
    """Fetch, score, rank, output top-N recommendations."""
    cfg = engine.load_config()
    sources = engine.load_sources(cfg)

    if args.source:
        sources = [s for s in sources if s.name == args.source]
        if not sources:
            print(f"ERROR: source '{args.source}' not found or disabled", file=sys.stderr)
            sys.exit(1)

    print(f"Fetching from {len(sources)} source(s)...", file=sys.stderr)
    articles, fetch_errors = engine.fetch_all(sources, config=cfg)

    if not articles:
        print("No articles fetched", file=sys.stderr)
        result = {"items": [], "error": "no_articles"}
        if fetch_errors:
            result['errors'] = fetch_errors
        json.dump(result, sys.stdout)
        return

    profile = engine.load_profile(cfg)
    threshold = cfg.get('dedup', {}).get('title_similarity_threshold', 0.85)
    scored = engine.recommend(articles, profile, limit=args.limit,
                              title_threshold=threshold)

    output = {
        'total_fetched': len(articles),
        'recommended': len(scored),
        'items': [s.to_dict() for s in scored],
    }
    if fetch_errors:
        output['errors'] = fetch_errors
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    print()
    print(f"Recommended: {len(scored)} articles from {len(articles)} fetched", file=sys.stderr)


def cmd_mark_seen(args: argparse.Namespace) -> None:
    engine.mark_seen(args.uids)
    print(f"Marked {len(args.uids)} as seen", file=sys.stderr)


def cmd_feedback(args: argparse.Namespace) -> None:
    positive = args.sentiment == '+'
    # Try to extract source from uid (format: source:id)
    source = ""
    if ':' in args.uid:
        source = args.uid.split(':')[0]
    engine.record_feedback(args.uid, positive, title=args.title or "", source=source)
    symbol = '+' if positive else '-'
    print(f"Feedback recorded: {symbol} {args.uid}", file=sys.stderr)


def cmd_profile(args: argparse.Namespace) -> None:
    cfg = engine.load_config()
    profile = engine.load_profile(cfg)
    json.dump(profile, sys.stdout, indent=2, ensure_ascii=False)
    print()


def cmd_stats(args: argparse.Namespace) -> None:
    stats = engine.get_stats()
    json.dump(stats, sys.stdout, indent=2, ensure_ascii=False)
    print()


def cmd_config(args: argparse.Namespace) -> None:
    cfg = engine.load_config()
    json.dump(cfg, sys.stdout, indent=2, ensure_ascii=False)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description='Feed Recommender — multi-source')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('sources', help='List available sources')

    p_enable = sub.add_parser('enable', help='Enable a source')
    p_enable.add_argument('name', help='Source name')

    p_disable = sub.add_parser('disable', help='Disable a source')
    p_disable.add_argument('name', help='Source name')

    p_fetch = sub.add_parser('fetch', help='Fetch articles')
    p_fetch.add_argument('--source', default=None, help='Specific source')
    p_fetch.add_argument('--limit', type=int, default=20, help='Limit per source')

    p_rec = sub.add_parser('recommend', help='Score + rank recommendations')
    p_rec.add_argument('--limit', type=int, default=10, help='Top N')
    p_rec.add_argument('--source', default=None, help='Specific source')

    p_seen = sub.add_parser('mark-seen', help='Mark articles as seen')
    p_seen.add_argument('uids', nargs='+', help='Article UIDs')

    p_fb = sub.add_parser('feedback', help='Record feedback')
    p_fb.add_argument('uid', help='Article UID')
    p_fb.add_argument('sentiment', choices=['+', '-'])
    p_fb.add_argument('--title', default='')

    sub.add_parser('profile', help='Show interest profile')
    sub.add_parser('stats', help='Show stats')
    sub.add_parser('config', help='Show config')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        'sources': cmd_sources,
        'enable': cmd_enable,
        'disable': cmd_disable,
        'fetch': cmd_fetch,
        'recommend': cmd_recommend,
        'mark-seen': cmd_mark_seen,
        'feedback': cmd_feedback,
        'profile': cmd_profile,
        'stats': cmd_stats,
        'config': cmd_config,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
