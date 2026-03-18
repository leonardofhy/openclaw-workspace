#!/usr/bin/env bash
# Set up git hooks for this workspace.
set -euo pipefail

git config core.hooksPath .githooks
chmod +x .githooks/pre-push
echo "✅ Git hooks configured — pre-push will run tests on changed files."
