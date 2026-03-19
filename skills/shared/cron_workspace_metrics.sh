#!/usr/bin/env bash
# cron_workspace_metrics.sh — Daily workspace metrics snapshot.
#
# Usage (crontab -e):
#   43 23 * * * /Users/leonardo/.openclaw/workspace/skills/shared/cron_workspace_metrics.sh
#
# Or run manually:
#   bash skills/shared/cron_workspace_metrics.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$WORKSPACE"

python3 skills/shared/workspace_metrics.py --snapshot --json \
    >> /dev/null 2>&1

echo "$(date '+%Y-%m-%dT%H:%M:%S%z') workspace-metrics snapshot OK" \
    >> "$WORKSPACE/memory/metrics/cron.log"
