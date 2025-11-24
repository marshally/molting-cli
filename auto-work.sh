#!/usr/bin/env bash

# Auto-work script: Automatically creates PRs when count drops below 5
# Runs in a forever loop, checking PR count and spawning /work-next

set -e

MAX_PRS=5
SLEEP_MINUTES=5

# Flag for graceful shutdown
RUNNING=true

# Signal handler for graceful shutdown
cleanup() {
  echo ""
  echo "🛑 Received shutdown signal, stopping gracefully..."
  RUNNING=false
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

echo "🤖 Auto-work script started"
echo "   Max PRs: ${MAX_PRS}"
echo "   Check interval: ${SLEEP_MINUTES} minutes"
echo "   Press Ctrl+C to stop gracefully"
echo ""

while $RUNNING; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting iteration..."

  # Fetch and rebase from origin
  echo "  📡 Fetching from origin..."
  if ! git fetch origin; then
    echo "  ❌ Failed to fetch from origin, stopping..."
    exit 1
  fi

  echo "  🔄 Rebasing main onto origin/main..."
  if ! git merge origin/main; then
    echo "  ❌ Merge conflict detected, stopping..."
    git merge --abort
    exit 1
  fi

  # Count open PRs
  pr_count=$(gh pr list --state open --json number --jq 'length')

  echo "  📊 Open PRs: ${pr_count}"

  # Check if we're at or above the limit
  if [ "$pr_count" -ge "$MAX_PRS" ]; then
    echo "  ⏸️  At PR limit (${pr_count}/${MAX_PRS}), waiting..."
  else
    echo "  🚀 Below limit (${pr_count}/${MAX_PRS}), starting new work..."

    # Temporarily disable trap to allow current task to complete
    trap - SIGINT SIGTERM

    # Run /work-next command
    if claude --dangerously-skip-permissions --print "/work-next"; then
      echo "  ✅ Work completed successfully"
    else
      echo "  ❌ Work failed or was interrupted"
      # If work was interrupted, exit gracefully
      RUNNING=false
    fi

    # Re-enable trap for next iteration
    trap cleanup SIGINT SIGTERM
  fi

  echo "  💤 Sleeping for ${SLEEP_MINUTES} minutes..."
  echo ""

  # Sleep with ability to interrupt
  for i in $(seq 1 $SLEEP_MINUTES); do
    if ! $RUNNING; then
      break
    fi
    sleep 60
  done
done

echo "✅ Auto-work script stopped cleanly"
