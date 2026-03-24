#!/bin/bash
# LALM-KE Daily Pipeline — Scout → Read → Report
# Usage: ./daily_pipeline.sh [--skip-existing] [--limit N]
set -euo pipefail

WORKSPACE="$HOME/.openclaw/workspace"
SCRIPTS="$WORKSPACE/skills/lalm-ke-scout/scripts"
DATE=$(date +%Y-%m-%d)

# Parse optional args
SKIP_EXISTING=""
SCOUT_LIMIT=20
READER_TOP=5

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-existing) SKIP_EXISTING="--skip-existing" ;;
        --limit) SCOUT_LIMIT="$2"; shift ;;
        --top) READER_TOP="$2"; shift ;;
        *) echo "[WARN] Unknown arg: $1" ;;
    esac
    shift
done

LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"
echo "$LOG_PREFIX LALM-KE Daily Pipeline starting..."
echo "$LOG_PREFIX Date: $DATE | Scout limit: $SCOUT_LIMIT | Reader top: $READER_TOP"

# ─── Step 1: Scout ────────────────────────────────────────────────────────────
echo ""
echo "$LOG_PREFIX [1/3] Running scout..."
python3 "$SCRIPTS/daily_scout.py" --limit "$SCOUT_LIMIT"
echo "$LOG_PREFIX Scout complete"

# ─── Step 2: Read top papers ──────────────────────────────────────────────────
SCOUT_JSON="$WORKSPACE/memory/lalm-ke/daily/$DATE.json"

if [[ ! -f "$SCOUT_JSON" ]]; then
    echo "$LOG_PREFIX [WARN] Scout output not found at $SCOUT_JSON, skipping paper reading"
else
    echo ""
    echo "$LOG_PREFIX [2/3] Reading top $READER_TOP papers..."
    python3 "$SCRIPTS/paper_reader.py" \
        --from-scout "$SCOUT_JSON" \
        --top "$READER_TOP" \
        ${SKIP_EXISTING}
    echo "$LOG_PREFIX Paper reading complete"
fi

# ─── Step 3: Report ──────────────────────────────────────────────────────────
echo ""
echo "$LOG_PREFIX [3/3] Generating report..."
python3 "$SCRIPTS/report_generator.py"
echo "$LOG_PREFIX Report saved to memory/lalm-ke/reports/$DATE.md"

# ─── Discord output (print to stdout, pipe to openclaw if desired) ────────────
echo ""
echo "=== Discord Summary ==="
python3 "$SCRIPTS/report_generator.py" --discord --dry-run
echo "======================"

echo ""
echo "$LOG_PREFIX Pipeline complete."
echo "$LOG_PREFIX Artifacts:"
echo "  - Scout:   $WORKSPACE/memory/lalm-ke/daily/$DATE.json"
echo "  - Notes:   $WORKSPACE/memory/lalm-ke/paper-notes/"
echo "  - Report:  $WORKSPACE/memory/lalm-ke/reports/$DATE.md"
