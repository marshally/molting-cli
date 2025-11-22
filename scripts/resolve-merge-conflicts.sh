#!/usr/bin/env bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"
}

# Validate arguments
if [ $# -lt 4 ]; then
    error "Usage: $0 <repo_owner> <repo_name> <pr_number> <head_ref>"
    exit 1
fi

REPO_OWNER="$1"
REPO_NAME="$2"
PR_NUMBER="$3"
HEAD_REF="$4"

# Check if claude CLI is available
if ! command -v claude &> /dev/null; then
    error "claude CLI is not installed. Please install Claude Code CLI first."
    exit 1
fi

# Create a unique temporary directory
TEMP_DIR="/tmp/pr-${REPO_NAME}-${PR_NUMBER}-$(date +%s)"
log "Creating temporary directory: $TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Cleanup function
cleanup() {
    log "Cleaning up temporary directory: $TEMP_DIR"
    rm -rf "$TEMP_DIR"
}

# Register cleanup on exit
trap cleanup EXIT

# Get PR details
log "Fetching PR details for #$PR_NUMBER..."
PR_DATA=$(gh pr view "$PR_NUMBER" --json baseRefName,headRefName,headRepository,headRepositoryOwner)
BASE_REF=$(echo "$PR_DATA" | jq -r '.baseRefName')
HEAD_REPOSITORY=$(echo "$PR_DATA" | jq -r '.headRepository.nameWithOwner')

log "PR #$PR_NUMBER: $HEAD_REF -> $BASE_REF"

# Shallow clone the repository
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
log "Shallow cloning repository: $REPO_URL"

cd "$TEMP_DIR"

if ! git clone --depth 1 --branch "$HEAD_REF" "$REPO_URL" repo; then
    error "Failed to clone repository"
    exit 1
fi

cd repo

# Configure git for automated commits
git config user.name "Auto-merge Bot"
git config user.email "auto-merge-bot@example.com"

# Fetch the base branch with depth
log "Fetching base branch: $BASE_REF"
git fetch origin "$BASE_REF:$BASE_REF" --depth 1

# Attempt to rebase onto base branch
log "Attempting to rebase $HEAD_REF onto $BASE_REF"
if git rebase "$BASE_REF"; then
    log "Rebase succeeded without conflicts!"

    # Push the changes
    log "Pushing rebased changes to $HEAD_REF"
    if git push origin "$HEAD_REF" --force-with-lease; then
        log "Successfully pushed rebased changes for PR #$PR_NUMBER"
    else
        error "Failed to push rebased changes"
        exit 1
    fi
else
    warn "Rebase encountered conflicts. Using Claude to resolve..."

    # Get list of conflicted files
    CONFLICTED_FILES=$(git diff --name-only --diff-filter=U)

    if [ -z "$CONFLICTED_FILES" ]; then
        error "No conflicted files found, but rebase failed"
        exit 1
    fi

    log "Conflicted files:"
    echo "$CONFLICTED_FILES"

    # Create a prompt for Claude
    CONFLICT_INFO=$(mktemp)
    cat > "$CONFLICT_INFO" <<EOF
I need help resolving merge conflicts for PR #${PR_NUMBER}.

The following files have merge conflicts:
$(echo "$CONFLICTED_FILES" | sed 's/^/  - /')

Please resolve these conflicts by:
1. Reading each conflicted file
2. Understanding the changes from both branches
3. Resolving the conflicts appropriately
4. Staging the resolved files with 'git add'

After resolving all conflicts:
- Run: git rebase --continue
- Then commit the resolution

When you're done, confirm that all conflicts are resolved.
EOF

    log "Invoking Claude to resolve conflicts..."

    # Use Claude in the repo directory
    # Note: This will open an interactive session
    if claude --dangerously-disable-sandbox --message "$(cat "$CONFLICT_INFO")"; then
        log "Claude session completed."

        # Check if rebase is still in progress
        if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
            error "Rebase is still in progress. Conflicts may not be fully resolved."
            git rebase --abort
            exit 1
        fi

        # Push the changes
        log "Pushing conflict-resolved changes to $HEAD_REF"
        if git push origin "$HEAD_REF" --force-with-lease; then
            log "Successfully pushed conflict-resolved changes for PR #$PR_NUMBER"
        else
            error "Failed to push conflict-resolved changes"
            exit 1
        fi
    else
        error "Claude session failed or was cancelled"
        git rebase --abort
        exit 1
    fi

    rm -f "$CONFLICT_INFO"
fi

log "Merge conflict resolution completed for PR #$PR_NUMBER"
