#!/bin/bash
# Unified dashboard: schedule timeline + RPG status
# Usage: bash dashboard.sh
set -euo pipefail
WORKSPACE="$(cd "$(dirname "$0")/../../.." && pwd)"
echo ""
python3 "$WORKSPACE/skills/daily-scheduler/scripts/schedule_data.py" --display --no-memory
python3 "$WORKSPACE/skills/leo-diary/scripts/rpg_dashboard.py"
