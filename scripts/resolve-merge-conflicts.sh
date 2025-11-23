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

    # Use Claude to resolve each conflicted file
    log "Using Claude to resolve conflicts..."

    echo "$CONFLICTED_FILES" | while read -r file; do
        if [ -z "$file" ]; then
            continue
        fi

        log "Resolving conflicts in: $file"

        # Read the conflicted file
        CONFLICTED_CONTENT=$(cat "$file")

        # Create prompt for Claude
        PROMPT="This file has git merge conflicts. Please resolve them by choosing the correct code and removing all conflict markers (<<<<<<, ======, >>>>>>).

File: $file

Conflicted content:
\`\`\`
$CONFLICTED_CONTENT
\`\`\`

Please output ONLY the resolved file content with all conflicts resolved and conflict markers removed. Do not include any explanations, markdown formatting, or code fences in your response - just the raw resolved file content."

        # Use Claude in non-interactive mode to get resolution
        RESOLVED_CONTENT=$(claude --print "$PROMPT" 2>/dev/null)

        if [ $? -eq 0 ] && [ -n "$RESOLVED_CONTENT" ]; then
            # Write resolved content back to file
            echo "$RESOLVED_CONTENT" > "$file"
            git add "$file"
            log "Resolved and staged: $file"
        else
            error "Failed to resolve conflicts in: $file"
            git rebase --abort
            exit 1
        fi
    done

    # Continue the rebase
    log "Continuing rebase..."
    if git rebase --continue; then
        log "Rebase completed successfully"

        # Push the changes
        log "Pushing conflict-resolved changes to $HEAD_REF"
        if git push origin "$HEAD_REF" --force-with-lease; then
            log "Successfully pushed conflict-resolved changes for PR #$PR_NUMBER"
        else
            error "Failed to push conflict-resolved changes"
            exit 1
        fi
    else
        error "Failed to continue rebase after resolving conflicts"
        git rebase --abort
        exit 1
    fi
fi

log "Merge conflict resolution completed for PR #$PR_NUMBER"
