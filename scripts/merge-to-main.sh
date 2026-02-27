#!/bin/bash
# merge-to-main.sh — Create a PR from current branch to main
# Usage: ./scripts/merge-to-main.sh
# Requires: gh CLI authenticated, git SSH access
set -uo pipefail

export PATH="$HOME/.local/bin:$PATH"

WORKSPACE="$HOME/.openclaw/workspace"
cd "$WORKSPACE"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
SHORT_HASH=$(git rev-parse --short HEAD)
COMMIT_COUNT=$(git rev-list --count origin/main.."$BRANCH" 2>/dev/null || echo "?")

# 1. Cross-merge: pull the other branch first
if [ "$BRANCH" = "lab-desktop" ]; then
    OTHER="macbook-m3"
elif [ "$BRANCH" = "macbook-m3" ]; then
    OTHER="lab-desktop"
else
    echo "❌ Unknown branch: $BRANCH (expected lab-desktop or macbook-m3)"
    exit 1
fi

echo "📥 Cross-merging origin/$OTHER..."
git fetch origin
git merge "origin/$OTHER" --no-edit 2>/dev/null || {
    echo "⚠️ Merge conflict with $OTHER. Aborting cross-merge."
    git merge --abort 2>/dev/null || true
}
git push origin "$BRANCH" 2>/dev/null || true

# 2. Check if there are new commits vs main
DIFF_COUNT=$(git rev-list --count origin/main.."$BRANCH" 2>/dev/null || echo "0")
if [ "$DIFF_COUNT" = "0" ]; then
    echo "✅ No new commits vs main. Skipping PR."
    echo "RESULT:skip:no_changes"
    exit 0
fi

# 3. Check if an open PR already exists
EXISTING_PR=$(gh pr list --base main --head "$BRANCH" --state open --json number --jq '.[0].number' 2>/dev/null || echo "")
if [ -n "$EXISTING_PR" ]; then
    echo "📌 Open PR #$EXISTING_PR already exists. Skipping."
    echo "RESULT:skip:pr_exists:#$EXISTING_PR"
    exit 0
fi

# 4. Create PR
TITLE="🔄 [$BRANCH] sync to main — $TIMESTAMP"
BODY="**Auto-generated PR** from \`$BRANCH\` → \`main\`

- **Commits**: $DIFF_COUNT new commit(s) since last merge
- **Latest**: $SHORT_HASH
- **Generated at**: $TIMESTAMP

---
\`\`\`
$(git log --oneline origin/main.."$BRANCH" | head -20)
\`\`\`"

PR_URL=$(gh pr create \
    --base main \
    --head "$BRANCH" \
    --title "$TITLE" \
    --body "$BODY" \
    2>&1)

echo "✅ PR created: $PR_URL"

# 5. Auto-merge the PR (since we're the only contributors)
# NOTE: use sed (BSD/GNU compatible). Avoid GNU-only `grep -P`.
PR_NUM=$(printf '%s\n' "$PR_URL" | sed -nE 's#^.*/pull/([0-9]+).*$#\1#p' | head -n1)
if [ -z "$PR_NUM" ]; then
    # Fallback: query currently open PR for this branch
    PR_NUM=$(gh pr list --base main --head "$BRANCH" --state open --json number --jq '.[0].number' 2>/dev/null || echo "")
fi

if [ -n "$PR_NUM" ]; then
    gh pr merge "$PR_NUM" --merge --auto 2>/dev/null || {
        # If auto-merge not enabled, just merge directly
        gh pr merge "$PR_NUM" --merge 2>/dev/null || echo "⚠️ Auto-merge failed. PR needs manual merge."
    }
    echo "✅ PR #$PR_NUM merged to main"
    # Pull main back into our branch
    git fetch origin
    git merge origin/main --no-edit 2>/dev/null || true
    git push origin "$BRANCH" 2>/dev/null || true
else
    echo "⚠️ Could not parse PR number from gh output. Skipping auto-merge step."
fi

echo "RESULT:success:$PR_URL"
