#!/bin/bash
# Sync latest feed recommendations to Google Sheets
# Usage: ./sync_digest_to_sheets.sh [--all] [--limit N]
# Per-source timeout: 30s. Failed sources are skipped, not fatal.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MEMORY_DIR="$SCRIPT_DIR/../../../memory"
FEEDS_DIR="$MEMORY_DIR/feeds"

LIMIT=${2:-20}  # default top-N recommendations
PER_SOURCE_TIMEOUT=30  # seconds per source fetch

cd "$SCRIPT_DIR"

# Fetch + score + rank articles with timeout
echo "Fetching & scoring articles (top $LIMIT, ${PER_SOURCE_TIMEOUT}s timeout)..." >&2
if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout $((PER_SOURCE_TIMEOUT * 4))"
else
    # macOS: use gtimeout from coreutils, or skip
    if command -v gtimeout >/dev/null 2>&1; then
        TIMEOUT_CMD="gtimeout $((PER_SOURCE_TIMEOUT * 4))"
    else
        TIMEOUT_CMD=""
    fi
fi

$TIMEOUT_CMD python3 feed.py recommend --limit "$LIMIT" > /tmp/feed_articles.json 2>/tmp/feed_fetch.err || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "WARNING: feed.py recommend timed out after $((PER_SOURCE_TIMEOUT * 4))s" >&2
    else
        echo "WARNING: feed.py recommend failed (exit $EXIT_CODE), but continuing..." >&2
    fi
    cat /tmp/feed_fetch.err >&2
}

# Check if JSON is valid
if ! python3 -m json.tool /tmp/feed_articles.json > /dev/null 2>&1; then
    echo "ERROR: Invalid JSON from feed.py, aborting sync" >&2
    exit 1
fi

# Report any source-level errors
python3 -c "
import json, sys
d = json.load(open('/tmp/feed_articles.json'))
errors = d.get('errors', [])
for e in errors:
    print(f\"  WARNING: {e['source']} failed: {e['error']}\", file=sys.stderr)
" 2>&1 >&2 || true

# Count articles — recommend outputs 'items' not 'articles'
COUNT=$(python3 -c "import json; d=json.load(open('/tmp/feed_articles.json')); print(len(d.get('items', d.get('articles', []))))")
echo "Got $COUNT scored articles, syncing to Sheet..." >&2

if [ "$COUNT" -eq 0 ]; then
    echo "WARNING: No articles to sync, skipping Sheet update" >&2
    exit 0
fi

# Sync to Google Sheets
python3 sync_to_sheets.py --json-file /tmp/feed_articles.json

# Generate Discord digest message
python3 discord_digest.py --json-file /tmp/feed_articles.json > /tmp/feed_discord_digest.txt 2>/dev/null || {
    echo "WARNING: Discord digest formatting failed, skipping Discord push" >&2
}

# Output the digest path for the cron agent to pick up and send
if [ -s /tmp/feed_discord_digest.txt ]; then
    echo "DISCORD_DIGEST=/tmp/feed_discord_digest.txt" >&2
    echo "---DISCORD_DIGEST_START---"
    cat /tmp/feed_discord_digest.txt
    echo "---DISCORD_DIGEST_END---"
fi

echo "Done ✓" >&2
