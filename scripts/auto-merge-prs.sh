#!/usr/bin/env bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"
}

# Lock file to prevent concurrent runs
LOCK_FILE="/tmp/auto-merge-prs.lock"

# Acquire lock or exit if already running
acquire_lock() {
    # Check if lock file exists
    if [ -f "$LOCK_FILE" ]; then
        # Read PID from lock file
        OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")

        # Check if process is still running
        if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
            warn "Another instance is already running (PID: $OLD_PID). Exiting."
            exit 0
        else
            # Stale lock file, remove it
            warn "Removing stale lock file (PID: $OLD_PID)"
            rm -f "$LOCK_FILE"
        fi
    fi

    # Create lock file with current PID
    echo $$ > "$LOCK_FILE"
}

# Release lock on exit
release_lock() {
    # Only remove lock file if it contains our PID
    if [ -f "$LOCK_FILE" ]; then
        LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [ "$LOCK_PID" = "$$" ]; then
            rm -f "$LOCK_FILE"
        fi
    fi
}

# Set up trap to release lock on exit
trap release_lock EXIT INT TERM

# Acquire the lock
acquire_lock

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    error "gh CLI is not installed. Please install it first: https://cli.github.com/"
    exit 1
fi

# Check if we're authenticated
if ! gh auth status &> /dev/null; then
    error "Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

# Label that can override approval requirement
AUTOMERGE_LABEL="${AUTOMERGE_LABEL:-automerge}"

# Get list of open PRs in JSON format
log "Fetching open PRs..."
prs=$(gh pr list --json number,headRefName,title,author,isDraft,reviewDecision,statusCheckRollup,mergeable,mergeStateStatus,url,headRepository,headRepositoryOwner,labels)

# Check if there are any PRs
if [ "$(echo "$prs" | jq '. | length')" -eq 0 ]; then
    log "No open PRs found."
    exit 0
fi

# Process each PR
echo "$prs" | jq -c '.[]' | while read -r pr; do
    number=$(echo "$pr" | jq -r '.number')
    title=$(echo "$pr" | jq -r '.title')
    author=$(echo "$pr" | jq -r '.author.login')
    is_draft=$(echo "$pr" | jq -r '.isDraft')
    review_decision=$(echo "$pr" | jq -r '.reviewDecision')
    mergeable=$(echo "$pr" | jq -r '.mergeable')
    merge_state=$(echo "$pr" | jq -r '.mergeStateStatus')
    url=$(echo "$pr" | jq -r '.url')
    head_ref=$(echo "$pr" | jq -r '.headRefName')

    log "Processing PR #$number: $title"

    # Skip draft PRs
    if [ "$is_draft" = "true" ]; then
        warn "PR #$number is a draft. Skipping."
        continue
    fi

    # Check if PR has the automerge label
    has_automerge_label=$(echo "$pr" | jq -r --arg label "$AUTOMERGE_LABEL" '.labels // [] | map(.name) | contains([$label])')

    # Check if PR is approved OR has automerge label
    if [ "$review_decision" != "APPROVED" ] && [ "$has_automerge_label" != "true" ]; then
        warn "PR #$number is not approved (status: $review_decision) and doesn't have '$AUTOMERGE_LABEL' label. Skipping."
        continue
    fi

    if [ "$has_automerge_label" = "true" ]; then
        log "PR #$number has '$AUTOMERGE_LABEL' label - bypassing approval requirement"
    fi

    # Check status checks
    status_checks=$(echo "$pr" | jq -r '.statusCheckRollup // [] | map(.conclusion) | .[]')
    if [ -z "$status_checks" ]; then
        failed_checks=0
    else
        failed_checks=$(echo "$status_checks" | { grep -v "SUCCESS" || true; } | { grep -v "SKIPPED" || true; } | wc -l | tr -d ' ')
    fi

    if [ "$failed_checks" -gt 0 ]; then
        warn "PR #$number has failing status checks. Skipping."
        continue
    fi

    log "PR #$number is ready (approved or labeled) and has passing checks!"

    # Check if PR is mergeable
    if [ "$mergeable" = "MERGEABLE" ]; then
        log "PR #$number is mergeable. Attempting rebase and merge..."

        if gh pr merge "$number" --rebase --auto 2>&1; then
            log "Successfully merged PR #$number with rebase"
        else
            warn "Rebase merge failed (branch may have merge commits). Trying squash merge..."
            if gh pr merge "$number" --squash --auto; then
                log "Successfully merged PR #$number with squash"
            else
                error "Failed to merge PR #$number with both rebase and squash"
            fi
        fi
    elif [ "$mergeable" = "CONFLICTING" ]; then
        warn "PR #$number has merge conflicts. Attempting to resolve..."

        # Get repository info
        repo_owner=$(echo "$pr" | jq -r '.headRepositoryOwner.login')
        repo_name=$(echo "$pr" | jq -r '.headRepository.name')

        # Call the conflict resolution script
        if [ -f "$SCRIPT_DIR/resolve-merge-conflicts.sh" ]; then
            "$SCRIPT_DIR/resolve-merge-conflicts.sh" "$repo_owner" "$repo_name" "$number" "$head_ref"
        else
            error "Conflict resolution script not found: $SCRIPT_DIR/resolve-merge-conflicts.sh"
        fi
    else
        warn "PR #$number mergeable status is: $mergeable. Skipping."
    fi

    echo ""
done

log "Finished processing PRs."
