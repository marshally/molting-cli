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
CLAUDE_CLI="${CLAUDE_CLI:-$HOME/.local/bin/claude}"
if ! command -v "$CLAUDE_CLI" &> /dev/null; then
    error "claude CLI is not installed at $CLAUDE_CLI. Please install Claude Code CLI first or set CLAUDE_CLI environment variable."
    exit 1
fi

# Create a unique temporary directory
TEMP_DIR="/tmp/pr-fix-${REPO_NAME}-${PR_NUMBER}-$(date +%s)"
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

# Clone the repository
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
log "Cloning repository: $REPO_URL"

cd "$TEMP_DIR"

if ! git clone --depth 50 --branch "$HEAD_REF" "$REPO_URL" repo; then
    error "Failed to clone repository"
    exit 1
fi

cd repo

# Configure git for automated commits
git config user.name "Auto-merge Bot"
git config user.email "auto-merge-bot@example.com"

# Check if poetry is available
if command -v poetry &> /dev/null; then
    log "Installing dependencies with poetry..."
    if ! poetry install --no-interaction 2>&1 | tee /tmp/install.log; then
        warn "Poetry install had warnings, continuing..."
    fi
else
    warn "Poetry not found, skipping dependency installation"
fi

# Run format first to fix auto-fixable issues
log "Running make format to auto-fix formatting issues..."
FORMAT_OUTPUT=$(make format 2>&1 || true)
echo "$FORMAT_OUTPUT"

# Check if any files were modified
if ! git diff --quiet; then
    log "Formatting made changes, committing..."
    git add -A
    git commit -m "Fix formatting issues

Automatically fixed by auto-merge bot" || true

    MADE_CHANGES=true
else
    log "No formatting changes needed"
    MADE_CHANGES=false
fi

# Run typecheck to see if there are type errors
log "Running make typecheck to check for type errors..."
TYPECHECK_OUTPUT=$(make typecheck 2>&1 || true)
TYPECHECK_EXIT=$?

if [ $TYPECHECK_EXIT -ne 0 ]; then
    warn "Type checking failed, attempting to fix with Claude..."

    # Save the typecheck output
    echo "$TYPECHECK_OUTPUT" > /tmp/typecheck_errors.txt

    # Use Claude to fix type errors
    PROMPT="The following type checking errors were found in this Python project:

\`\`\`
$TYPECHECK_OUTPUT
\`\`\`

Please fix all type checking errors. Use the Read tool to read the files that have errors, then use the Edit tool to fix them. Make sure to:
1. Add proper type annotations
2. Fix any type mismatches
3. Import necessary types from typing module
4. Ensure all fixes are minimal and focused

After making all fixes, run 'make typecheck' to verify the errors are resolved."

    log "Invoking Claude to fix type errors..."
    if "$CLAUDE_CLI" --print "$PROMPT" > /dev/null 2>&1; then
        log "Claude finished attempting type error fixes"

        # Check if any files were modified
        if ! git diff --quiet; then
            log "Type error fixes made changes, committing..."
            git add -A
            git commit -m "Fix type checking errors

Automatically fixed by auto-merge bot with Claude assistance" || true
            MADE_CHANGES=true
        fi
    else
        warn "Claude failed to fix type errors, continuing..."
    fi
fi

# Run tests
log "Running make test to check for test failures..."
TEST_OUTPUT=$(make test 2>&1 || true)
TEST_EXIT=$?

if [ $TEST_EXIT -ne 0 ]; then
    warn "Tests failed, attempting to fix with Claude..."

    # Save the test output
    echo "$TEST_OUTPUT" > /tmp/test_errors.txt

    # Use Claude to fix test failures
    PROMPT="The following test failures were found in this Python project:

\`\`\`
$TEST_OUTPUT
\`\`\`

Please fix all test failures. Use the Read tool to read the test files and implementation files, then use the Edit tool to fix them. Make sure to:
1. Fix any bugs in the implementation that cause tests to fail
2. Update tests if they have incorrect expectations (only if clearly wrong)
3. Ensure all fixes are minimal and focused
4. Don't skip tests - fix the underlying issues

After making all fixes, run 'make test' to verify the tests pass."

    log "Invoking Claude to fix test failures..."
    if "$CLAUDE_CLI" --print "$PROMPT" > /dev/null 2>&1; then
        log "Claude finished attempting test failure fixes"

        # Check if any files were modified
        if ! git diff --quiet; then
            log "Test failure fixes made changes, committing..."
            git add -A
            git commit -m "Fix test failures

Automatically fixed by auto-merge bot with Claude assistance" || true
            MADE_CHANGES=true
        fi
    else
        warn "Claude failed to fix test failures, continuing..."
    fi
fi

# If we made any changes, push them
if [ "$MADE_CHANGES" = true ]; then
    log "Pushing fixes to $HEAD_REF"
    if git push origin "$HEAD_REF"; then
        log "Successfully pushed build fixes for PR #$PR_NUMBER"
        exit 0
    else
        error "Failed to push build fixes"
        exit 1
    fi
else
    log "No changes were made to fix build failures"
    exit 1
fi
