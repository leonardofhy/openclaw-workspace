#!/bin/bash
# Sync latest feed recommendations to Google Sheets
# Usage: ./sync_digest_to_sheets.sh [--all] [--limit N]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MEMORY_DIR="$SCRIPT_DIR/../../../memory"
FEEDS_DIR="$MEMORY_DIR/feeds"

LIMIT=${2:-20}  # default 20 articles per source
ALL_SOURCES=${1:---limit-sources}  # if --all, use all 4 sources; else use preferred

cd "$SCRIPT_DIR"

# Fetch latest articles
echo "Fetching articles (limit: $LIMIT)..." >&2
python3 feed.py fetch --limit "$LIMIT" > /tmp/feed_articles.json 2>/tmp/feed_fetch.err || {
    echo "WARNING: feed.py fetch failed, but continuing..." >&2
    cat /tmp/feed_fetch.err >&2
}

# Check if JSON is valid
if ! python3 -m json.tool /tmp/feed_articles.json > /dev/null 2>&1; then
    echo "ERROR: Invalid JSON from feed.py, aborting sync" >&2
    exit 1
fi

# Count articles
COUNT=$(python3 -c "import json; d=json.load(open('/tmp/feed_articles.json')); print(len(d.get('articles', [])))")
echo "Got $COUNT articles, syncing to Sheet..." >&2

# Sync to Google Sheets
python3 sync_to_sheets.py --json-file /tmp/feed_articles.json

echo "Done ✓" >&2
