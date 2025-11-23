# Auto-Merge PRs

Automated PR management system that checks for approved PRs with passing builds and automatically merges them or resolves merge conflicts.

## Features

- Runs every 5 minutes (configurable)
- Checks all open PRs for:
  - Approval status OR special label
  - Passing CI/status checks
  - Merge conflicts
- Automatically merges PRs using "rebase and merge" when ready
- Resolves merge conflicts using Claude Code when needed
- Supports label-based approval override (useful for personal repos where you can't self-approve)

## Approval Methods

The script will auto-merge a PR if it meets **either** of these conditions:

1. **Approved by a reviewer** - Traditional GitHub approval workflow
2. **Has the `automerge` label** - Useful when you can't approve your own PRs

To use the label method, simply add the `automerge` label to your PR when it's ready to merge.

You can customize the label name by setting the `AUTOMERGE_LABEL` environment variable:
```bash
export AUTOMERGE_LABEL="ready-to-merge"
```

## Prerequisites

1. **GitHub CLI (`gh`)**
   ```bash
   brew install gh
   gh auth login
   ```

2. **Claude Code CLI**
   - Install Claude Code from: https://claude.com/claude-code
   - Ensure the `claude` command is available in your PATH

3. **jq** (JSON processor)
   ```bash
   brew install jq
   ```

## Installation

1. Run the setup script:
   ```bash
   ./scripts/setup-cron.sh
   ```

   This will:
   - On macOS: Create a launchd job that runs every 5 minutes
   - On Linux: Add a cron job that runs every 5 minutes

## Scripts

### auto-merge-prs.sh

Main script that:
1. Fetches all open PRs using `gh pr list`
2. Filters for:
   - Non-draft PRs
   - Approved PRs
   - PRs with passing status checks
3. For each qualifying PR:
   - If mergeable: merges with rebase and merge
   - If has conflicts: calls `resolve-merge-conflicts.sh`

### resolve-merge-conflicts.sh

Conflict resolution script that:
1. Creates a temporary directory in `/tmp`
2. Shallow clones the repository
3. Fetches the base branch and attempts to rebase
4. If conflicts occur:
   - Invokes Claude Code to resolve them
   - Pushes the resolved changes
5. Cleans up the temporary directory

### setup-cron.sh

Installation script that sets up the scheduled job:
- **macOS**: Creates a launchd plist in `~/Library/LaunchAgents/`
- **Linux**: Adds a cron job to your crontab

## Quick Start Guide

### For Personal Repos (Can't Self-Approve)

1. Install the cron job:
   ```bash
   ./scripts/setup-cron.sh
   ```

2. When you have a PR ready to merge:
   - Ensure all CI checks pass
   - Add the `automerge` label to the PR
   - Wait up to 5 minutes for automatic merge

3. Create the `automerge` label in your repo (one-time setup):
   ```bash
   gh label create automerge --description "Auto-merge this PR when checks pass" --color 0e8a16
   ```

## Manual Testing

To test the scripts manually:

```bash
# Test the main auto-merge script
./scripts/auto-merge-prs.sh

# Test conflict resolution for a specific PR
./scripts/resolve-merge-conflicts.sh <repo_owner> <repo_name> <pr_number> <head_ref>
```

## Logs

### macOS (launchd)
- Standard output: `~/Library/Logs/auto-merge-prs.log`
- Errors: `~/Library/Logs/auto-merge-prs-error.log`

### Linux (cron)
- Combined output: `~/auto-merge-prs.log`

## Uninstallation

### macOS
```bash
launchctl unload ~/Library/LaunchAgents/com.automerge.prs.plist
rm ~/Library/LaunchAgents/com.automerge.prs.plist
```

### Linux
```bash
crontab -e
# Remove the line containing: auto-merge-prs.sh
```

## Configuration

### Change Frequency

**macOS**: Edit `~/Library/LaunchAgents/com.automerge.prs.plist`
```xml
<key>StartInterval</key>
<integer>300</integer>  <!-- seconds (300 = 5 minutes) -->
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.automerge.prs.plist
launchctl load ~/Library/LaunchAgents/com.automerge.prs.plist
```

**Linux**: Edit crontab
```bash
crontab -e
# Change */5 to your desired interval (e.g., */10 for every 10 minutes)
```

## How It Works

### Merge Flow

```
┌─────────────────────────────┐
│  auto-merge-prs.sh runs     │
│  (every 5 minutes)          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Fetch open PRs via gh CLI  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  For each PR:               │
│  - Check if draft           │
│  - Check if approved        │
│  - Check status checks      │
└──────────┬──────────────────┘
           │
           ▼
      ┌────┴────┐
      │Mergeable?│
      └────┬────┘
           │
     ┌─────┴─────┐
     │           │
    Yes         No (conflicts)
     │           │
     ▼           ▼
┌─────────┐  ┌─────────────────────────┐
│ gh pr   │  │ resolve-merge-          │
│ merge   │  │ conflicts.sh            │
│ --rebase│  │                         │
└─────────┘  │ 1. Clone in /tmp        │
             │ 2. Rebase               │
             │ 3. Claude resolves      │
             │ 4. Push                 │
             │ 5. Cleanup              │
             └─────────────────────────┘
```

### Conflict Resolution Flow

1. **Clone**: Shallow clone the PR branch in `/tmp`
2. **Fetch**: Fetch the target base branch
3. **Rebase**: Attempt `git rebase base_branch`
4. **Conflicts?**:
   - If no conflicts: Push and done
   - If conflicts: Invoke Claude Code
5. **Claude Session**: Claude analyzes conflicts and resolves them
6. **Continue**: Complete the rebase with `git rebase --continue`
7. **Push**: Force push with lease to update PR
8. **Cleanup**: Remove temporary directory

## Security Considerations

- The scripts use `--force-with-lease` for pushing to prevent data loss
- Temporary repositories are created with unique names to avoid conflicts
- Cleanup is guaranteed via trap handlers
- Git commits are made with a bot identity ("Auto-merge Bot")
- **Concurrency protection**: PID-based locking prevents multiple instances from running simultaneously
  - If a script is already running, new instances exit gracefully
  - Stale lock files (from crashed processes) are automatically cleaned up
  - Lock file location: `/tmp/auto-merge-prs.lock`

## Troubleshooting

### gh CLI not authenticated
```bash
gh auth status
gh auth login
```

### Claude CLI not found
Ensure Claude Code is installed and the `claude` command is in your PATH:
```bash
which claude
```

### Logs show errors
Check the log files for detailed error messages:
```bash
# macOS
tail -f ~/Library/Logs/auto-merge-prs.log
tail -f ~/Library/Logs/auto-merge-prs-error.log

# Linux
tail -f ~/auto-merge-prs.log
```

### Job not running
**macOS**:
```bash
launchctl list | grep automerge
```

**Linux**:
```bash
crontab -l
```

### Script appears stuck or blocked
If you see "Another instance is already running" but believe no instance is running:

1. Check if a process is actually running:
   ```bash
   cat /tmp/auto-merge-prs.lock  # Shows PID
   ps -p <PID>  # Check if that process exists
   ```

2. If the process is truly stuck, kill it:
   ```bash
   kill <PID>
   ```

3. If it's a stale lock file, remove it manually:
   ```bash
   rm /tmp/auto-merge-prs.lock
   ```
