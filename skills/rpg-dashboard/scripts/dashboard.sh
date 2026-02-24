#!/bin/bash
# Unified dashboard: schedule timeline + RPG status
# Usage: bash dashboard.sh [--schedule|--rpg]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/dashboard.py" "$@"
