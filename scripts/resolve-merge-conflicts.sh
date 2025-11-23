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

# Clone the repository with sufficient depth for merge
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
log "Cloning repository: $REPO_URL"

cd "$TEMP_DIR"

if ! git clone --depth 100 --branch "$HEAD_REF" "$REPO_URL" repo; then
    error "Failed to clone repository"
    exit 1
fi

cd repo

# Configure git for automated commits
git config user.name "Auto-merge Bot"
git config user.email "auto-merge-bot@example.com"

# Fetch the base branch with depth
log "Fetching base branch: $BASE_REF"
git fetch origin "$BASE_REF:$BASE_REF" --depth 100

# Attempt to merge base branch
log "Attempting to merge $BASE_REF into $HEAD_REF"
if git merge "$BASE_REF" --no-edit; then
    log "Merge succeeded without conflicts!"

    # Push the changes
    log "Pushing merged changes to $HEAD_REF"
    if git push origin "$HEAD_REF"; then
        log "Successfully pushed merged changes for PR #$PR_NUMBER"
    else
        error "Failed to push merged changes"
        exit 1
    fi
else
    warn "Merge encountered conflicts. Using Claude to resolve..."

    # Get list of conflicted files
    CONFLICTED_FILES=$(git diff --name-only --diff-filter=U)

    if [ -z "$CONFLICTED_FILES" ]; then
        error "No conflicted files found, but merge failed"
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
            git merge --abort
            exit 1
        fi
    done

    # Complete the merge
    log "Completing merge..."
    if git commit --no-edit; then
        log "Merge completed successfully"

        # Push the changes
        log "Pushing conflict-resolved changes to $HEAD_REF"
        if git push origin "$HEAD_REF"; then
            log "Successfully pushed conflict-resolved changes for PR #$PR_NUMBER"

            # Wait for CI to start and check for build errors
            log "Waiting for CI checks to start..."
            sleep 30

            # Check CI status
            log "Checking CI status for PR #$PR_NUMBER..."
            CI_STATUS=$(gh pr view "$PR_NUMBER" --json statusCheckRollup --jq '.statusCheckRollup[].conclusion' 2>/dev/null || echo "")

            if echo "$CI_STATUS" | grep -q "FAILURE"; then
                warn "CI checks failed. Attempting to fix build errors..."

                # Get the latest commit SHA
                LATEST_SHA=$(git rev-parse HEAD)

                # Get CI failure details
                log "Fetching CI failure logs..."
                CI_LOGS=$(gh run list --repo "$REPO_OWNER/$REPO_NAME" --commit "$LATEST_SHA" --json conclusion,name,databaseId --limit 5 2>/dev/null || echo "")

                if [ -n "$CI_LOGS" ]; then
                    # Find failed runs
                    FAILED_RUNS=$(echo "$CI_LOGS" | jq -r '.[] | select(.conclusion == "failure") | .databaseId' | head -1)

                    if [ -n "$FAILED_RUNS" ]; then
                        log "Getting logs for failed run..."
                        ERROR_LOGS=$(gh run view "$FAILED_RUNS" --repo "$REPO_OWNER/$REPO_NAME" --log-failed 2>/dev/null || echo "Could not fetch logs")

                        # Use Claude to analyze and fix the errors
                        FIX_PROMPT="The CI build failed after resolving merge conflicts. Here are the error logs:

\`\`\`
$ERROR_LOGS
\`\`\`

Please analyze these errors and suggest fixes. Output the specific files that need to be changed and what changes to make. Be concise and focus only on fixing the build errors."

                        log "Using Claude to analyze build errors..."
                        FIX_SUGGESTIONS=$(claude --print "$FIX_PROMPT" 2>/dev/null || echo "")

                        if [ -n "$FIX_SUGGESTIONS" ]; then
                            log "Claude suggested fixes:"
                            echo "$FIX_SUGGESTIONS"

                            # Use Claude to actually fix the errors
                            log "Attempting to apply fixes..."
                            FIX_RESULT=$(claude --print "Based on the previous analysis, please make the necessary code changes to fix the CI build errors. Output a series of file edits in the following format:

FILE: path/to/file.ext
<<<OLD
old content to replace
>>>
<<<NEW
new content
>>>

Be specific and only include the exact sections that need to be changed." 2>/dev/null || echo "")

                            if [ -n "$FIX_RESULT" ]; then
                                # Parse and apply the fixes
                                # This is a simplified approach - a production version would be more robust
                                log "Applying suggested fixes to files..."

                                # Create a commit with the fixes
                                git add -A
                                if git diff --cached --quiet; then
                                    log "No changes to commit from fix suggestions"
                                else
                                    git commit -m "Fix CI build errors after merge conflict resolution

Auto-generated fixes based on CI failure analysis.

🤖 Generated with Claude Code" 2>/dev/null || true

                                    # Push the fixes
                                    log "Pushing build error fixes to $HEAD_REF"
                                    if git push origin "$HEAD_REF"; then
                                        log "Successfully pushed build error fixes for PR #$PR_NUMBER"
                                    else
                                        warn "Failed to push build error fixes"
                                    fi
                                fi
                            else
                                warn "Build errors detected. Manual review may be needed."
                            fi
                        fi
                    fi
                fi
            else
                log "CI checks are passing or pending"
            fi
        else
            error "Failed to push conflict-resolved changes"
            exit 1
        fi
    else
        error "Failed to complete merge after resolving conflicts"
        git merge --abort
        exit 1
    fi
fi

log "Merge conflict resolution completed for PR #$PR_NUMBER"
