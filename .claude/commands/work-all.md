---
description: Execute all ready beads issues in parallel using up to 4 subagents
---

## Your Role

Continuously process all ready beads issues by spawning up to 4 parallel subagents. Each subagent works on one issue independently in its own worktree. Keep going until all issues are completed.

## Multi-Agent Architecture

This workflow uses:
- **Agent Mail** - Real-time coordination to prevent collisions (<100ms vs 2-5s git-based)
- **Git Worktrees** - Isolated working directories per issue
- **Protected Branch** - Issues sync to `beads-metadata` branch (not main)
- **No-Daemon Mode** - Required for worktree compatibility

### Environment Configuration

Each subagent MUST set these environment variables at the start:
```bash
export BEADS_AGENT_MAIL_URL=http://127.0.0.1:8765
export BEADS_AGENT_NAME=claude-{issue_id}  # Unique per agent
export BEADS_PROJECT_ID=molting-cli
export BEADS_NO_DAEMON=1  # Required for worktrees
```

## Workflow

### Step 0: Ensure Proper Branch Setup

Before starting work, ensure we're on the correct branch:

```bash
cd /Users/marshallyount/code/marshally/molting-cli && git branch --show-current
```

**Case A: Currently on main branch**
- Create and checkout a new working branch:
```bash
cd /Users/marshallyount/code/marshally/molting-cli && git checkout -b working-branch
```

**Case B: Currently on a working branch (not main)**
- Push the branch to origin if it hasn't been pushed yet (this ensures the branch is tracked):
```bash
cd /Users/marshallyount/code/marshally/molting-cli && git push -u origin $(git branch --show-current)
```

This may fail if the branch already exists on remote - that's okay, it means it's already set up correctly.

### Step 0.5: Verify Agent Mail Server

Check that Agent Mail is running:
```bash
curl -s http://127.0.0.1:8765/mail/ | head -5 || echo "Agent Mail not running - start with: cd /tmp/mcp_agent_mail && source .venv/bin/activate && python -m mcp_agent_mail.cli serve-http --port 8765"
```

### Step 1: Fetch All Ready Issues

First, ensure we have the latest beads data from the protected branch:
```bash
cd /Users/marshallyount/code/marshally/molting-cli && BEADS_NO_DAEMON=1 bd sync --import-only
```

This imports the latest issue statuses from the beads-metadata branch.

Then set the beads context (call this tool directly, not via bash):
- Use the `mcp__plugin_beads_beads__set_context` tool with workspace_root: `/Users/marshallyount/code/marshally/molting-cli`

Then get ready issues (call this tool directly, not via bash):
- Use the `mcp__plugin_beads_beads__ready` tool with limit: 50

**IMPORTANT**: Filter and sort the results:
1. Filter out any issues that are epics (type: "epic"). Epics should not be worked on directly - only their sub-tasks.
2. Sort filtered issues by priority (ascending - priority 0 is highest, priority 5 is lowest)

If no ready issues after filtering, try open issues:
- Use the `mcp__plugin_beads_beads__list` tool with status: "open", limit: 50
- Apply the same filtering (exclude epics by issue_type)
- Sort by priority (ascending)

Create a list of all issues to process.

### Step 2: Process Issues in Batches of 4

**CRITICAL: Maximum 4 concurrent subagents at any time.**

For each batch of up to 4 issues:

#### 2a. Claim Issues Atomically

For EACH issue in the batch, update status to "in_progress":
- Use the `mcp__plugin_beads_beads__update` tool with:
  - issue_id: "{issue_id}"
  - status: "in_progress"
  - assignee: "Claude"

The MCP tool updates the local database directly.

#### 2b. Create Worktrees

For each issue, check if a worktree exists:
```bash
git worktree list | grep {issue_id}
```

If NOT exists, fetch latest from origin and create worktree:
```bash
cd ~/code/marshally/molting-cli && git fetch origin && git worktree add ~/code/worktrees/molting-cli/{issue_id} -b {issue_id} origin/main
```

#### 2c. Determine Task Types

For each issue, check the title to determine task type:

**Type A: Standard Refactoring Task**
- Title matches pattern: "Implement {RefactoringName} refactoring"
- Example: "Implement Extract Method refactoring"
- Use TEMPLATE A

For Type A, extract these variables:
- refactoring_name: The refactoring name (e.g., "Extract Method")
- test_class: Convert to PascalCase with "Test" prefix (e.g., "TestExtractMethod")
- refactoring_dir: Convert to snake_case (e.g., "extract_method")

Then find the test structure in the worktree:
```bash
cd ~/code/worktrees/molting-cli/{issue_id} && grep -l "class {test_class}" tests/test_*.py
```
This gives you:
- test_file_path: The test file (e.g., "tests/test_composing_methods.py")
- fixture_category: Extract from path (e.g., "composing_methods")

**Type B: General Task**
- Title does NOT match the "Implement X refactoring" pattern
- Example: "Add naming conversion utilities to ast_utils.py"
- Use TEMPLATE B

For Type B, extract:
- title: The full issue title
- description: The issue description
- acceptance_criteria: The issue acceptance criteria (if present)

#### 2d. Spawn Subagents IN PARALLEL

**CRITICAL: Send ALL Task tool calls for this batch in a SINGLE message to run them in parallel.**

Use the Task tool with:
- subagent_type: "general-purpose"
- model: "sonnet" (use sonnet for reliability in parallel execution)
- description: Brief description from the issue title
- prompt: Fill in the appropriate template below with all extracted variables

---

## TEMPLATE A: Subagent Prompt for Standard Refactoring Tasks

You are implementing issue {issue_id}: Implement {refactoring_name} refactoring using strict TDD (Red-Green-Refactor) methodology.

CRITICAL: You MUST complete ALL 7 steps below. Do NOT stop after any intermediate step. You are not done until you have completed STEP 7 and provided the final report.

### STEP 0: Environment Setup (MANDATORY - DO THIS FIRST)

Set these environment variables BEFORE any beads commands:
```bash
export BEADS_AGENT_MAIL_URL=http://127.0.0.1:8765
export BEADS_AGENT_NAME=claude-{issue_id}
export BEADS_PROJECT_ID=molting-cli
export BEADS_NO_DAEMON=1
```

These enable:
- Agent Mail coordination (prevents collisions with other agents)
- No-daemon mode (required for git worktrees)

### CRITICAL: Review Base Classes and Utilities FIRST

Before writing ANY code, you MUST read and understand the shared functionality available in this codebase. This is NON-NEGOTIABLE.

**Required Reading (in this order):**

1. **Base Command Class** - `molting/commands/base.py`
   - `BaseCommand` abstract class
   - `validate_required_params()` helper
   - `apply_libcst_transform()` and `apply_ast_transform()` methods

2. **AST Utilities** - `molting/core/ast_utils.py`
   - `parse_target()`, `parse_line_number()`, `parse_line_range()`
   - `find_method_in_tree()`, `find_class_in_module()`
   - `extract_all_methods()`, `extract_init_field_assignments()`
   - `camel_to_snake_case()`, `generate_field_name_from_class()`
   - `insert_class_after_imports()`

3. **Code Generation Utilities** - `molting/core/code_generation_utils.py`
   - `create_super_init_call()`, `create_field_assignment()`
   - `create_init_method()`, `create_parameter()`

4. **Import Utilities** - `molting/core/import_utils.py`
   - `has_import()`, `ensure_import()`

5. **Visitor Classes** - `molting/core/visitors.py`
   - `SelfFieldCollector`, `SelfFieldChecker`

6. **Similar Commands** - Look at existing commands in `molting/commands/` for patterns:
   - Check commands in the same category as your task
   - See how they inherit from BaseCommand
   - Note how they use transformers and utilities

**YOU MUST USE THESE UTILITIES** instead of reimplementing functionality. If a utility exists for what you need, USE IT.

### Setup

Work in this worktree: ~/code/worktrees/molting-cli/{issue_id}
Branch: {issue_id}
All commands must be run from this worktree.

**IMPORTANT: For all beads MCP tool calls, you MUST first call `mcp__plugin_beads_beads__set_context` with workspace_root set to the worktree path: `/Users/marshallyount/code/worktrees/molting-cli/{issue_id}`**

### Your Task

Implement the {refactoring_name} refactoring by following these exact steps:

### STEP 1: Preflight Checks (MANDATORY)

Run in the worktree directory:

a. Fetch and rebase from origin/main:
```bash
git fetch origin
git rebase origin/main
```

If there are merge conflicts:
- Resolve them carefully
- Run tests to ensure conflicts were resolved correctly
- Continue rebase: `git rebase --continue`
- If conflicts cannot be resolved: STOP and report

   After successful rebase, force push:
```bash
git push --force-with-lease
```

b. Check git status - STOP if uncommitted changes:
```bash
git status
```

c. Run code quality checks:
```bash
make check
```

   If there are any errors: STOP and report
   If there are auto-fixable issues, run:
```bash
make format
```

   Then commit the fixes with message "Fix linting and formatting issues" and push immediately:
```bash
git add -A && git commit -m "Fix linting and formatting issues" && git push
```

d. Run all tests:
```bash
pytest
```

   If any tests fail: STOP and report

### STEP 2: Read Base Classes and Utilities (MANDATORY)

Before writing any code, read these files:
```bash
cat molting/commands/base.py
cat molting/core/ast_utils.py
cat molting/core/code_generation_utils.py
cat molting/core/import_utils.py
cat molting/core/visitors.py
```

Also look at similar existing commands:
```bash
ls molting/commands/*/
```

Take note of what helper functions already exist that you can reuse.

### STEP 3: RED Stage

a. Read the test file to find the test for this refactoring:
   {test_file_path}
   Look for class {test_class}

b. Read the fixture files to understand what transformation is needed:
   tests/fixtures/{fixture_category}/{refactoring_dir}/simple/input.py
   tests/fixtures/{fixture_category}/{refactoring_dir}/simple/expected.py

c. Unskip the test by removing this decorator from the test class:
   `@pytest.mark.skip(reason="No implementation yet")`

d. Run the test to ensure it fails:
```bash
pytest {test_file_path}::{test_class}::test_simple -v
```

e. Format, commit, and push the failing test:
```bash
make format && git add -A && git commit -m "RED: Unskip {test_class}::test_simple

Command: pytest {test_file_path}::{test_class}::test_simple -v

Result: FAILED -

The test correctly fails because {refactoring_name} refactoring is not implemented.
This is the expected behavior for the RED phase of TDD." && git push
```

### STEP 4: GREEN Stage

a. Implement the MINIMUM code needed to make the test pass:
   - Create a new command class in molting/commands/{fixture_category}/{refactoring_dir}.py
   - Follow the Command Pattern established in the codebase
   - **USE existing base classes and utilities** - don't reinvent the wheel
   - Look at existing commands as reference (check molting/commands/<category>/<name>.py)
   - Register the command in the registry
   - Import the command in molting/cli.py
   - Keep it simple - just make the test pass

   Note: Determine which library to use (rope vs libCST):
   - Check existing commands to see what they use
   - libCST is used for more complex AST transformations
   - rope is used for simpler refactorings
   - Study the fixture files carefully to understand the exact transformation needed

b. Run the test to verify it passes:
```bash
pytest {test_file_path}::{test_class}::test_simple -v
```

c. If test fails: fix the implementation and try again
   If test passes: format, commit, and push the implementation

```bash
make format && git add -A && git commit -m "GREEN: Implement {refactoring_name} command

Command: pytest {test_file_path}::{test_class}::test_simple -v

Result: PASSED (1 passed, X warnings in Y.YYs)

Implemented the minimum code required to make the test pass:
- Created {test_class}Command class
- Registered command in registry
- " && git push
```

### STEP 5: REFACTOR Stage

IMPORTANT: After completing the code review in this step, you MUST continue to STEP 6. Do NOT stop here.

a. Review your implementation against Clean Code principles:
   - Read the command file you just created
   - Manually identify issues with:
     - Naming (meaningful names, avoid abbreviations)
     - Function length (keep functions small and focused)
     - Comments (code should be self-documenting)
     - Error handling (proper validation and error messages)
     - Duplication (DRY principle)
     - Code organization (single responsibility)

b. For EACH issue identified (critical, important, minor):
   - Make ONE fix at a time
   - Run the test after each fix to ensure it still passes
   - Format, commit, and push each fix separately:

```bash
make format && git add -A && git commit -m "Refactor: <description>

Test command: pytest {test_file_path}::{test_class}::test_simple -v
Result: PASSED (1 passed, X warnings in Y.YYs)" && git push
```

   Examples:
   - "Refactor: Remove unused variable"
   - "Refactor: Add error handling for missing parameters"
   - "Refactor: Extract validation to helper function"

c. Continue until all major issues are addressed

NOW CONTINUE TO STEP 6 - DO NOT STOP HERE

### STEP 6: Create PR and Wait for CI

a. Rebase on latest main to ensure branch is up-to-date:
```bash
git fetch origin
git rebase origin/main
```

If there are merge conflicts:
- Resolve them carefully
- Run tests to ensure conflicts were resolved correctly: `pytest`
- Continue rebase: `git rebase --continue`
- If conflicts cannot be resolved: STOP and report

After successful rebase, force push:
```bash
git push --force-with-lease
```

b. Verify branch is pushed:
```bash
git push -u origin {issue_id}
```

c. Create pull request:
```bash
gh pr create --title "Implement {refactoring_name} ({issue_id})" --body "$(cat <<'EOF'
## Summary

Implemented the {refactoring_name} refactoring using strict TDD methodology (Red-Green-Refactor cycle):
- RED: Unskipped test for {test_class}::test_simple and verified it failed
- GREEN: Implemented minimum code to pass the test using Command Pattern
- REFACTOR: Applied Clean Code principles with N refactoring commits

This completes issue {issue_id}.

## Implementation Details

Created {test_class}Command class following the established Command Pattern architecture.

## Refactoring Improvements

[List improvements made during refactor stage]

## Test Plan

- Test passes: pytest {test_file_path}::{test_class}::test_simple -v
- All refactorings maintain passing tests
- Code reviewed against Clean Code principles

Generated with https://claude.com/claude-code
EOF
)" --base main
```

d. Wait for CI to start, then check status:
```bash
sleep 5 && gh pr checks
```

e. If any CI checks fail:
   - Investigate the failure
   - Fix the issue
   - Format, commit, and push the fix:
```bash
make format && git add -A && git commit -m "Fix CI failure: <description>" && git push
```
   - Wait and recheck CI status:
```bash
sleep 5 && gh pr checks
```
   - Repeat until all checks pass

f. Once all CI checks are passing, close the issue.

Close the issue (call this tool directly, not via bash):
- Use the `mcp__plugin_beads_beads__close` tool with:
  - issue_id: "{issue_id}"
  - reason: "Completed with passing tests and CI"

### STEP 7: Final Report (REQUIRED)

YOU MUST PROVIDE THIS FINAL REPORT - THIS IS YOUR DELIVERABLE:

Report back with:
1. Issue ID and name: {issue_id} - {refactoring_name}
2. PR URL: (the URL from gh pr create)
3. Commit count: X commits total (1 RED + 1 GREEN + N REFACTOR + M CI fixes)
4. CI status: All checks passing / Some checks failed (with details)
5. Brief summary: What was implemented and any notable details
6. Beads issue status: Closed (if CI passed) / Still open (if CI failed)

Example report format:
```
FINAL REPORT - IMPLEMENTATION COMPLETE

1. Issue: molting-cli-abc.2 - Implement Extract Method
2. PR URL: https://github.com/marshally/molting-cli/pull/123
3. Commits: 5 total (1 RED + 1 GREEN + 2 REFACTOR + 1 CI fix)
4. CI Status: All checks passing
5. Summary: Implemented ExtractMethod command using libCST for AST transformation. Added validation for method name format and error handling for invalid selections.
6. Beads Issue: Closed
```

IMPORTANT NOTES:
- Run ALL commands from the worktree directory: ~/code/worktrees/molting-cli/{issue_id}
- Use the FULL issue_id (e.g., "molting-cli-357.2") everywhere, NOT just the epic prefix
- NEVER skip preflight checks
- **READ BASE CLASSES AND UTILITIES BEFORE WRITING CODE**
- **USE EXISTING UTILITIES** - don't reimplement functionality
- ALWAYS run make format before committing any code
- ALWAYS push immediately after every commit using git push
- NEVER combine RED/GREEN/REFACTOR commits
- Test after EVERY commit
- Follow the Command Pattern architecture (see existing commands as examples)
- Add type annotations (from typing import Any)
- ONLY close the beads issue after ALL CI checks pass
- DO NOT STOP after the code review - continue through STEP 6 and STEP 7
- Your task is NOT complete until you provide the STEP 7 final report
- If you encounter complex issues, report them - don't get stuck
- **CRITICAL: All beads MCP tools must be called directly as tool invocations, NOT as bash commands. Always call `mcp__plugin_beads_beads__set_context` first before any other beads operations.**

---

## TEMPLATE B: Subagent Prompt for General Tasks

You are implementing issue {issue_id}: {title}

**Issue Description:**
{description}

**Acceptance Criteria:**
{acceptance_criteria}

### STEP 0: Environment Setup (MANDATORY - DO THIS FIRST)

Set these environment variables BEFORE any beads commands:
```bash
export BEADS_AGENT_MAIL_URL=http://127.0.0.1:8765
export BEADS_AGENT_NAME=claude-{issue_id}
export BEADS_PROJECT_ID=molting-cli
export BEADS_NO_DAEMON=1
```

These enable:
- Agent Mail coordination (prevents collisions with other agents)
- No-daemon mode (required for git worktrees)

### CRITICAL: Review Base Classes and Utilities FIRST

Before writing ANY code, you MUST read and understand the shared functionality available in this codebase. This is NON-NEGOTIABLE.

**Required Reading (in this order):**

1. **Base Command Class** - `molting/commands/base.py`
   - `BaseCommand` abstract class
   - `validate_required_params()` helper
   - `apply_libcst_transform()` and `apply_ast_transform()` methods

2. **AST Utilities** - `molting/core/ast_utils.py`
   - `parse_target()`, `parse_line_number()`, `parse_line_range()`
   - `find_method_in_tree()`, `find_class_in_module()`
   - `extract_all_methods()`, `extract_init_field_assignments()`
   - `camel_to_snake_case()`, `generate_field_name_from_class()`
   - `insert_class_after_imports()`

3. **Code Generation Utilities** - `molting/core/code_generation_utils.py`
   - `create_super_init_call()`, `create_field_assignment()`
   - `create_init_method()`, `create_parameter()`

4. **Import Utilities** - `molting/core/import_utils.py`
   - `has_import()`, `ensure_import()`

5. **Visitor Classes** - `molting/core/visitors.py`
   - `SelfFieldCollector`, `SelfFieldChecker`

6. **Similar Commands** - Look at existing commands in `molting/commands/` for patterns

**YOU MUST USE THESE UTILITIES** instead of reimplementing functionality. If a utility exists for what you need, USE IT.

### Setup

Work in this worktree: ~/code/worktrees/molting-cli/{issue_id}
Branch: {issue_id}
All commands must be run from this worktree.

**IMPORTANT: For all beads MCP tool calls, you MUST first call `mcp__plugin_beads_beads__set_context` with workspace_root set to the worktree path: `/Users/marshallyount/code/worktrees/molting-cli/{issue_id}`**

### Your Task

Complete this task by following these steps:

### STEP 1: Preflight Checks (MANDATORY)

Run in the worktree directory:

a. Fetch and rebase from origin/main:
```bash
git fetch origin
git rebase origin/main
```

If there are merge conflicts:
- Resolve them carefully
- Run tests to ensure conflicts were resolved correctly
- Continue rebase: `git rebase --continue`
- If conflicts cannot be resolved: STOP and report

After successful rebase, force push:
```bash
git push --force-with-lease
```

b. Check git status - STOP if uncommitted changes:
```bash
git status
```

c. Run code quality checks:
```bash
make check
```

If there are any errors: STOP and report
If there are auto-fixable issues, run:
```bash
make format
```

Then commit the fixes with message "Fix linting and formatting issues" and push immediately:
```bash
git add -A && git commit -m "Fix linting and formatting issues" && git push
```

d. Run all tests:
```bash
pytest
```

If any tests fail: STOP and report

### STEP 2: Read Base Classes and Utilities (MANDATORY)

Before writing any code, read these files:
```bash
cat molting/commands/base.py
cat molting/core/ast_utils.py
cat molting/core/code_generation_utils.py
cat molting/core/import_utils.py
cat molting/core/visitors.py
```

Also look at similar existing commands:
```bash
ls molting/commands/*/
```

Take note of what helper functions already exist that you can reuse.

### STEP 3: Understand the Task

Read the issue description and acceptance criteria carefully. Identify:
- What files need to be modified or created
- What the expected behavior/output should be
- Whether tests need to be added or modified

### STEP 4: Implement the Task

Follow TDD principles where applicable:
1. Write or identify existing tests that verify the behavior
2. Implement the minimal code to make tests pass
3. Refactor for clean code

**USE existing base classes and utilities** - don't reinvent the wheel.

For each logical change:
- Make the change
- Run relevant tests: `pytest <test_file>` or `make test`
- Run code quality checks: `make check`
- Format code: `make format`
- Commit with a descriptive message and push immediately:
```bash
git add -A && git commit -m "<clear description of change>" && git push
```

Use commit prefixes:
- "Add" for new features/functions
- "Fix" for bug fixes
- "Refactor" for code improvements
- "Update" for modifications to existing code
- "Remove" for deletions

### STEP 5: Verify Acceptance Criteria

Review the acceptance criteria from the issue description and verify each one is met:
- Run all relevant tests
- Check that the implementation matches requirements
- Ensure code quality standards are met

### STEP 6: Create PR and Wait for CI

a. Rebase on latest main to ensure branch is up-to-date:
```bash
git fetch origin
git rebase origin/main
```

If there are merge conflicts:
- Resolve them carefully
- Run tests to ensure conflicts were resolved correctly: `pytest`
- Continue rebase: `git rebase --continue`
- If conflicts cannot be resolved: STOP and report

After successful rebase, force push:
```bash
git push --force-with-lease
```

b. Verify branch is pushed:
```bash
git push -u origin {issue_id}
```

c. Create pull request with a clear summary:
```bash
gh pr create --title "{title} ({issue_id})" --body "$(cat <<'EOF'
## Summary

[Describe what was implemented and how]

This completes issue {issue_id}.

## Changes

[List key changes made]

## Test Plan

- [Describe how you tested the changes]
- All tests passing: pytest [relevant test command]

Generated with https://claude.com/claude-code
EOF
)" --base main
```

d. Wait for CI to start, then check status:
```bash
sleep 5 && gh pr checks
```

e. If any CI checks fail:
- Investigate the failure
- Fix the issue
- Format, commit, and push the fix:
```bash
make format && git add -A && git commit -m "Fix CI failure: <description>" && git push
```
- Wait and recheck CI status:
```bash
sleep 5 && gh pr checks
```
- Repeat until all checks pass

f. Once all CI checks are passing, close the issue.

Close the issue (call this tool directly, not via bash):
- Use the `mcp__plugin_beads_beads__close` tool with:
  - issue_id: "{issue_id}"
  - reason: "Completed with passing tests and CI"

### STEP 7: Final Report (REQUIRED)

YOU MUST PROVIDE THIS FINAL REPORT - THIS IS YOUR DELIVERABLE:

Report back with:
1. Issue ID and name: {issue_id} - {title}
2. PR URL: (the URL from gh pr create)
3. Commit count: X commits total
4. CI status: All checks passing / Some checks failed (with details)
5. Brief summary: What was implemented and any notable details
6. Beads issue status: Closed (if CI passed) / Still open (if CI failed)

Example report format:
```
FINAL REPORT - IMPLEMENTATION COMPLETE

1. Issue: molting-3bi - Add naming conversion utilities to ast_utils.py
2. PR URL: https://github.com/marshally/molting-cli/pull/123
3. Commits: 3 total
4. CI Status: All checks passing
5. Summary: Added camel_to_snake_case and generate_field_name_from_class utility functions to ast_utils.py with comprehensive tests covering edge cases.
6. Beads Issue: Closed
```

IMPORTANT NOTES:
- Run ALL commands from the worktree directory: ~/code/worktrees/molting-cli/{issue_id}
- NEVER skip preflight checks
- **READ BASE CLASSES AND UTILITIES BEFORE WRITING CODE**
- **USE EXISTING UTILITIES** - don't reimplement functionality
- ALWAYS run make format before committing any code
- ALWAYS push immediately after every commit using git push
- Test after EVERY commit where applicable
- Add type annotations (from typing import Any)
- ONLY close the beads issue after ALL CI checks pass
- Your task is NOT complete until you provide the STEP 7 final report
- If you encounter complex issues, report them - don't get stuck
- **CRITICAL: All beads MCP tools must be called directly as tool invocations, NOT as bash commands. Always call `mcp__plugin_beads_beads__set_context` first before any other beads operations.**

---

### Step 3: Collect Results and Continue

After all subagents in a batch complete:

1. Collect their final reports
2. Track results:
   - Successful completions (PR created, CI passing, issue closed)
   - Failures (with reasons)
3. **Sync beads to protected branch**:
   ```bash
   cd /Users/marshallyount/code/marshally/molting-cli && BEADS_NO_DAEMON=1 bd sync -m "Batch complete: closed issues from parallel execution"
   ```
4. Check for more ready issues:
   - Use `mcp__plugin_beads_beads__ready` again
   - Filter out epics and already-processed issues
5. If more issues exist:
   - Repeat Step 2 with next batch (up to 4)
6. Continue until no ready issues remain

### Step 4: Final Summary

When all issues are processed, provide a summary:

```
PARALLEL EXECUTION COMPLETE

Total Issues Processed: X
Successful: Y
Failed: Z

Successful PRs:
- [issue_id]: [PR URL]
- ...

Failed Issues:
- [issue_id]: [reason]
- ...

Remaining Ready Issues: N
```

## Key Rules

1. **Maximum 4 concurrent subagents** - never spawn more than 4 at once
2. **Spawn in parallel** - use a SINGLE message with multiple Task tool calls
3. **Claim before spawning** - update beads status to prevent race conditions
4. **Keep going** - don't stop until all ready issues are processed
5. **Track results** - maintain a running tally of successes and failures
6. **Report failures** - don't hide issues that couldn't be completed
7. **Subagents MUST read utilities first** - ensure they use shared functionality
8. **Always use BEADS_NO_DAEMON=1** - daemon mode doesn't work with worktrees
9. **Agent Mail for coordination** - each subagent gets unique BEADS_AGENT_NAME
10. **Sync to protected branch** - use `bd sync` after each batch completes
