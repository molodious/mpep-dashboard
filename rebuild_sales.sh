#!/usr/bin/env bash
# Triggered by salesWebhookServer.js after a new paid order is logged.
# Rebuilds sales.html, commits, and pushes if there are changes.
# Uses a lock file to prevent overlapping builds.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK_FILE="/tmp/rebuild_sales.lock"

# Acquire lock (non-blocking) — skip if a build is already running
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  echo "[rebuild] Another build is already running, skipping."
  exit 0
fi

cd "$REPO_DIR"

echo "[rebuild] $(date -u '+%Y-%m-%dT%H:%M:%SZ') Starting sales dashboard rebuild..."

# Pull latest to avoid conflicts with any other pushes
git pull --rebase --quiet origin main || true

# Run the build
python3 build_sales_dashboard.py

# Commit and push only if sales.html changed
git add sales.html
if git diff --cached --quiet; then
  echo "[rebuild] No changes to sales.html."
else
  git commit -m "Auto-update sales dashboard [$(date -u '+%Y-%m-%dT%H:%M:%SZ')]"
  git push origin main
  echo "[rebuild] Dashboard updated and pushed."
fi
