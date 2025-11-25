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

    # Extract repository information from URL (format: https://github.com/owner/repo/pull/number)
    pr_repo=$(echo "$url" | sed -E 's|https://github.com/([^/]+/[^/]+)/pull/.*|\1|')

    log "Processing PR #$number in $pr_repo: $title"

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
        warn "PR #$number has failing status checks. Attempting to fix..."

        # Get repository info
        repo_owner=$(echo "$pr" | jq -r '.headRepositoryOwner.login')
        repo_name=$(echo "$pr" | jq -r '.headRepository.name')

        # Call the build failure fix script
        if [ -f "$SCRIPT_DIR/fix-build-failures.sh" ]; then
            # Capture output to a temporary file
            ERROR_LOG=$(mktemp)
            if "$SCRIPT_DIR/fix-build-failures.sh" "$repo_owner" "$repo_name" "$number" "$head_ref" 2>&1 | tee "$ERROR_LOG"; then
                log "Successfully fixed build failures for PR #$number"
                log "Waiting for CI to re-run checks..."
                rm -f "$ERROR_LOG"
                # Continue to next PR - the fixes have been pushed and CI will re-run
                continue
            else
                error "Failed to fix build failures for PR #$number"

                # Strip ANSI color codes from the log
                CLEAN_LOG=$(cat "$ERROR_LOG" | sed 's/\x1b\[[0-9;]*m//g')

                # Extract the last error from the cleaned log
                ERROR_SUMMARY=$(echo "$CLEAN_LOG" | grep -E "ERROR:|fatal:|error:" | tail -5 || echo "Unknown error occurred")

                # Change label from automerge to automerge-error
                if [ "$has_automerge_label" = "true" ]; then
                    log "Changing label from '$AUTOMERGE_LABEL' to 'automerge-error'"
                    gh pr edit "$number" --repo "$pr_repo" --remove-label "$AUTOMERGE_LABEL" --add-label "automerge-error" 2>/dev/null || true
                fi

                # Add a comment to the PR about the failure
                COMMENT_BODY="## ⚠️ Automatic Build Failure Fix Failed

**Summary:** The auto-merge script attempted to fix build/test failures but encountered an error.

**Error Details:**
\`\`\`
$ERROR_SUMMARY
\`\`\`

**Full Log:**
<details>
<summary>Click to expand full error log</summary>

\`\`\`
$CLEAN_LOG
\`\`\`
</details>

Please fix the build failures manually."

                gh pr comment "$number" --repo "$pr_repo" --body "$COMMENT_BODY" 2>/dev/null || true
                rm -f "$ERROR_LOG"
                continue
            fi
        else
            warn "Build failure fix script not found: $SCRIPT_DIR/fix-build-failures.sh"
            warn "PR #$number has failing status checks. Skipping."
            continue
        fi
    fi

    log "PR #$number is ready (approved or labeled) and has passing checks!"

    # Check if PR is mergeable
    if [ "$mergeable" = "MERGEABLE" ]; then
        log "PR #$number is mergeable. Attempting rebase merge..."

        if gh pr merge "$number" --repo "$pr_repo" --rebase --auto 2>&1; then
            log "Successfully merged PR #$number with rebase"
        else
            error "Rebase merge failed for PR #$number. Manual intervention required."
            error "This may be due to merge commits in the branch history. Consider rebasing the branch manually."
        fi
    elif [ "$mergeable" = "CONFLICTING" ]; then
        warn "PR #$number has merge conflicts. Attempting to resolve..."

        # Get repository info
        repo_owner=$(echo "$pr" | jq -r '.headRepositoryOwner.login')
        repo_name=$(echo "$pr" | jq -r '.headRepository.name')

        # Call the conflict resolution script
        if [ -f "$SCRIPT_DIR/resolve-merge-conflicts.sh" ]; then
            # Capture output to a temporary file
            ERROR_LOG=$(mktemp)
            if "$SCRIPT_DIR/resolve-merge-conflicts.sh" "$repo_owner" "$repo_name" "$number" "$head_ref" 2>&1 | tee "$ERROR_LOG"; then
                log "Successfully resolved conflicts for PR #$number"
                rm -f "$ERROR_LOG"
            else
                error "Failed to resolve conflicts for PR #$number"

                # Strip ANSI color codes from the log
                CLEAN_LOG=$(cat "$ERROR_LOG" | sed 's/\x1b\[[0-9;]*m//g')

                # Extract the last error and command from the cleaned log
                ERROR_SUMMARY=$(echo "$CLEAN_LOG" | grep -E "ERROR:|fatal:|error:" | tail -5 || echo "Unknown error occurred")
                LAST_COMMAND=$(echo "$CLEAN_LOG" | grep -B 2 -E "ERROR:|fatal:|error:" | grep -v "ERROR:" | grep -v "fatal:" | grep -v "error:" | tail -1 || echo "Command not captured")

                # Change label from automerge to automerge-error
                if [ "$has_automerge_label" = "true" ]; then
                    log "Changing label from '$AUTOMERGE_LABEL' to 'automerge-error'"
                    gh pr edit "$number" --repo "$pr_repo" --remove-label "$AUTOMERGE_LABEL" --add-label "automerge-error" 2>/dev/null || true
                fi

                # Add a detailed comment to the PR
                COMMENT_BODY="## ⚠️ Automatic Conflict Resolution Failed

**Summary:** The auto-merge script attempted to resolve merge conflicts but encountered an error.

**Error Details:**
\`\`\`
$ERROR_SUMMARY
\`\`\`

**Last Command:**
\`\`\`
$LAST_COMMAND
\`\`\`

**Full Log:**
<details>
<summary>Click to expand full error log</summary>

\`\`\`
$CLEAN_LOG
\`\`\`
</details>

Please resolve the conflicts manually or investigate the error above."

                gh pr comment "$number" --repo "$pr_repo" --body "$COMMENT_BODY" 2>/dev/null || true
                rm -f "$ERROR_LOG"
            fi
        else
            error "Conflict resolution script not found: $SCRIPT_DIR/resolve-merge-conflicts.sh"
        fi
    elif [ "$mergeable" = "UNKNOWN" ]; then
        warn "PR #$number mergeable status is still being calculated by GitHub. Will check again next run."
    else
        warn "PR #$number has unexpected mergeable status: $mergeable. Skipping."
    fi

    echo ""
done

log "Finished processing PRs."
