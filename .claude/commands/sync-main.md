---
description: Sync current branch with main (fetch, rebase, fix conflicts, lint, push)
---

## Your Role

Synchronize the current branch with the latest main branch by fetching updates, rebasing, resolving any conflicts, fixing lint issues, and pushing the changes.

## Workflow

### Step 1: Verify Current Branch

Check that we're not on the main branch:
```bash
git branch --show-current
```

If on main branch:
- STOP and warn the user that this command should be run from a feature branch
- Suggest checking out or creating a feature branch first

### Step 2: Fetch Latest Changes

Fetch the latest changes from origin:
```bash
git fetch origin
```

### Step 3: Rebase on Main

Attempt to rebase the current branch on origin/main:
```bash
git rebase origin/main
```

**If rebase succeeds without conflicts:**
- Continue to Step 4

**If there are merge conflicts:**
- Show the conflicted files:
  ```bash
  git status
  ```
- Read each conflicted file to understand the conflicts
- Resolve conflicts by:
  - Analyzing the conflict markers (<<<<<<, ======, >>>>>>)
  - Understanding the intent of both changes
  - Keeping the appropriate changes or merging them intelligently
  - Removing conflict markers
- After resolving all conflicts in a file, stage it:
  ```bash
  git add <file>
  ```
- Once ALL conflicts are resolved and staged, continue the rebase:
  ```bash
  git rebase --continue
  ```
- If additional conflicts appear in subsequent commits, repeat conflict resolution
- If conflicts are too complex or unclear, STOP and ask the user for guidance

### Step 4: Run Code Quality Checks

Run formatting and linting:
```bash
make format
```

Check if formatting made any changes:
```bash
git status
```

**If there are changes:**
- Stage and commit them:
  ```bash
  git add -A && git commit -m "Fix linting and formatting issues after rebase"
  ```

### Step 5: Run Tests

Verify that all tests still pass after the rebase:
```bash
make test
```

**If tests fail:**
- Show the failure details
- STOP and report the test failures to the user
- Suggest investigating the failures before pushing

**If tests pass:**
- Continue to Step 6

### Step 6: Push Changes

Force push the rebased branch (safe because we're using --force-with-lease):
```bash
git push --force-with-lease
```

**If push fails:**
- This likely means the remote branch has new commits
- Inform the user and suggest running the command again
- STOP

**If push succeeds:**
- Continue to Step 7

### Step 7: Report Results

Provide a summary to the user:
- Branch name
- Number of commits rebased
- Whether conflicts were resolved
- Whether lint fixes were needed
- Test status
- Push status

Example format:
```
✅ Branch sync complete!

Branch: feature-branch
Commits rebased: 5
Conflicts resolved: Yes (2 files)
Lint fixes applied: Yes
Tests: All passing
Push: Successful

Your branch is now up-to-date with main.
```

## Important Notes

- Always use `--force-with-lease` instead of `--force` for safety
- Never skip test runs after resolving conflicts
- If unsure about conflict resolution, ask the user
- This command is designed for feature branches, not main
- The rebase rewrites history, so force push is required
