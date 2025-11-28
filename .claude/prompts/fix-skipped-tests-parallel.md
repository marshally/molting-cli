# Fix Skipped Tests in Parallel

You are the orchestrator for fixing 107 skipped tests across the molting-cli project. Your job is to spawn multiple haiku subagents that work in parallel without merge conflicts.

## Strategy: Git Worktree Isolation

Each subagent works in its OWN git worktree with its OWN branch. This ensures:
1. **Complete filesystem isolation** - no read/write conflicts
2. **Independent git operations** - no push/pull races
3. **Parallel test execution** - tests don't interfere
4. **Clean merges** - each branch merges independently to main

## Workstream Definitions

### Workstream 1: test_composing_methods.py (8 tests)
**Files owned:**
- tests/test_composing_methods.py
- molting/commands/composing_methods/*.py
- tests/fixtures/composing_methods/**/*

**Tests to fix:**
- TestExtractMethod: test_with_locals, test_with_instance_vars, test_name_conflict, test_with_decorators
- TestExtractFunction: test_name_conflict, test_with_decorators
- TestInlineMethod: test_with_decorators
- TestReplaceTempWithQuery: test_with_decorators

---

### Workstream 2: test_dealing_with_generalization.py (16 tests)
**Files owned:**
- tests/test_dealing_with_generalization.py
- molting/commands/dealing_with_generalization/*.py
- tests/fixtures/dealing_with_generalization/**/*

**Tests to fix:**
- TestPullUpField: test_with_instance_vars, test_name_conflict, test_with_decorators, test_multiple_calls
- TestPullUpMethod: test_name_conflict
- TestPullUpConstructorBody: test_with_locals, test_name_conflict
- TestPushDownMethod: test_name_conflict
- TestPushDownField: test_name_conflict, test_with_decorators
- TestExtractSubclass: test_name_conflict
- TestExtractSuperclass: test_name_conflict
- TestExtractInterface: test_name_conflict
- TestFormTemplateMethod: test_with_locals
- TestReplaceInheritanceWithDelegation: test_with_instance_vars
- TestReplaceDelegationWithInheritance: test_with_instance_vars

---

### Workstream 3: test_moving_features.py (13 tests)
**Files owned:**
- tests/test_moving_features.py
- molting/commands/moving_features/*.py
- tests/fixtures/moving_features/**/*

**Tests to fix:**
- TestMoveMethod: test_with_decorators
- TestMoveField: test_multiple_calls, test_with_instance_vars
- TestExtractClass: test_multiple_calls, test_with_decorators
- TestInlineClass: test_multiple_calls
- TestHideDelegate: test_multiple_calls, test_with_instance_vars, test_with_decorators
- TestRemoveMiddleMan: test_multiple_calls, test_with_instance_vars
- TestIntroduceForeignMethod: test_with_locals
- TestIntroduceLocalExtension: test_with_decorators

---

### Workstream 4: test_organizing_data.py (17 tests)
**Files owned:**
- tests/test_organizing_data.py
- molting/commands/organizing_data/*.py
- tests/fixtures/organizing_data/**/*

**Tests to fix:**
- TestReplaceDataValueWithObject: test_with_locals, test_with_instance_vars, test_multiple_calls, test_name_conflict
- TestChangeValueToReference: test_with_instance_vars
- TestChangeReferenceToValue: test_with_instance_vars
- TestReplaceArrayWithObject: test_with_locals, test_name_conflict
- TestChangeUnidirectionalAssociationToBidirectional: test_with_instance_vars
- TestChangeBidirectionalAssociationToUnidirectional: test_with_instance_vars
- TestReplaceMagicNumberWithSymbolicConstant: test_with_locals, test_name_conflict
- TestEncapsulateCollection: test_multiple_calls
- TestReplaceTypeCodeWithClass: test_with_instance_vars, test_multiple_calls, test_name_conflict
- TestReplaceTypeCodeWithStateStrategy: test_name_conflict

---

### Workstream 5: test_simplifying_conditionals.py (24 tests)
**Files owned:**
- tests/test_simplifying_conditionals.py
- molting/commands/simplifying_conditionals/*.py
- tests/fixtures/simplifying_conditionals/**/*

**Tests to fix:**
- TestDecomposeConditional: test_with_locals, test_with_instance_vars, test_multiple_calls, test_with_decorators
- TestConsolidateConditionalExpression: test_with_locals, test_with_instance_vars, test_multiple_calls, test_name_conflict, test_with_decorators
- TestConsolidateDuplicateConditionalFragments: test_with_locals, test_with_instance_vars, test_multiple_calls, test_with_decorators
- TestReplaceNestedConditionalWithGuardClauses: test_with_instance_vars, test_with_decorators
- TestReplaceConditionalWithPolymorphism: test_with_instance_vars, test_with_decorators
- TestIntroduceNullObject: test_with_instance_vars, test_with_decorators
- TestIntroduceAssertion: test_with_instance_vars, test_with_decorators
- TestRemoveControlFlag: test_with_locals, test_with_instance_vars, test_with_decorators

---

### Workstream 6: test_simplifying_method_calls.py (29 tests)
**Files owned:**
- tests/test_simplifying_method_calls.py
- molting/commands/simplifying_method_calls/*.py
- tests/fixtures/simplifying_method_calls/**/*

**Tests to fix:**
- TestRenameMethod: test_multiple_calls, test_name_conflict
- TestAddParameter: test_with_instance_vars, test_multiple_calls, test_with_decorators
- TestRemoveParameter: test_multiple_calls
- TestSeparateQueryFromModifier: test_with_locals, test_with_instance_vars, test_multiple_calls, test_name_conflict
- TestParameterizeMethod: test_with_instance_vars, test_name_conflict, test_with_decorators
- TestReplaceParameterWithExplicitMethods: test_multiple_calls, test_name_conflict, test_with_decorators
- TestPreserveWholeObject: test_with_locals, test_multiple_calls
- TestReplaceParameterWithMethodCall: test_with_locals, test_multiple_calls
- TestIntroduceParameterObject: test_with_locals, test_multiple_calls, test_name_conflict
- TestRemoveSettingMethod: test_multiple_calls
- TestReplaceConstructorWithFactoryFunction: test_multiple_calls, test_name_conflict
- TestReplaceErrorCodeWithException: test_with_instance_vars, test_multiple_calls
- TestReplaceExceptionWithTest: test_multiple_calls

---

## Shared Files (DO NOT MODIFY in subagents)

These files are shared across workstreams. If modifications are needed, the orchestrator must handle them:
- molting/core/visitors.py
- molting/core/ast_utils.py
- molting/core/transformers.py
- molting/commands/base.py
- tests/conftest.py

If a subagent needs to add a new visitor/checker to visitors.py, it should:
1. Report back to the orchestrator with the required addition
2. The orchestrator will add it and push before the subagent continues

---

## Execution Instructions

### Phase 1: Setup Worktrees (Orchestrator)

Create 6 separate worktrees, one for each workstream:

```bash
cd /Users/marshallyount/code/marshally/molting-cli
git fetch origin

# Create worktrees for each workstream
git worktree add ~/code/worktrees/molting-cli/fix-composing-methods -b fix-composing-methods origin/main
git worktree add ~/code/worktrees/molting-cli/fix-dealing-with-generalization -b fix-dealing-with-generalization origin/main
git worktree add ~/code/worktrees/molting-cli/fix-moving-features -b fix-moving-features origin/main
git worktree add ~/code/worktrees/molting-cli/fix-organizing-data -b fix-organizing-data origin/main
git worktree add ~/code/worktrees/molting-cli/fix-simplifying-conditionals -b fix-simplifying-conditionals origin/main
git worktree add ~/code/worktrees/molting-cli/fix-simplifying-method-calls -b fix-simplifying-method-calls origin/main
```

### Phase 2: Spawn Subagents (Parallel)

Spawn ALL 6 subagents in a SINGLE message using parallel Task tool calls.

Each subagent receives the template below with their specific workstream variables filled in.

**Workstream to Worktree Mapping:**
| Workstream | Branch | Worktree Path |
|------------|--------|---------------|
| 1 - composing_methods | fix-composing-methods | ~/code/worktrees/molting-cli/fix-composing-methods |
| 2 - dealing_with_generalization | fix-dealing-with-generalization | ~/code/worktrees/molting-cli/fix-dealing-with-generalization |
| 3 - moving_features | fix-moving-features | ~/code/worktrees/molting-cli/fix-moving-features |
| 4 - organizing_data | fix-organizing-data | ~/code/worktrees/molting-cli/fix-organizing-data |
| 5 - simplifying_conditionals | fix-simplifying-conditionals | ~/code/worktrees/molting-cli/fix-simplifying-conditionals |
| 6 - simplifying_method_calls | fix-simplifying-method-calls | ~/code/worktrees/molting-cli/fix-simplifying-method-calls |

---

## Subagent Template

```
You are fixing skipped tests in {test_file} for the molting-cli project.

## Your Scope (ONLY modify these files)
- {test_file}
- molting/commands/{category}/*.py
- tests/fixtures/{category}/**/*

## DO NOT MODIFY (shared files - will cause merge conflicts)
- molting/core/visitors.py
- molting/core/ast_utils.py
- molting/core/transformers.py
- molting/commands/base.py
- tests/conftest.py

## Your Isolated Worktree

Work EXCLUSIVELY in this worktree: {worktree_path}
Branch: {branch_name}

ALL commands must be run from your worktree directory. Never cd to the main repo.

First, verify you're in the correct worktree:
```bash
cd {worktree_path}
git branch --show-current  # Should show: {branch_name}
git status  # Must be clean
```

## Your Tests to Fix

{test_list}

## Workflow for Each Test

### Step 1: Check if test already passes
```bash
pytest {test_file}::{test_class}::{test_name} -v
```

If it passes, just remove the skip marker and commit:
```bash
# Edit the test file to remove @pytest.mark.skip decorator
make format && git add -A && git commit -m "Enable {test_class}::{test_name} - was already passing" && git push
```

### Step 2: If test fails, analyze the failure

Read the test, input fixture, and expected fixture to understand what's needed.

### Step 3: Fix Categories

**Category A: Missing fixture files**
- Create the fixture files in tests/fixtures/{category}/{refactoring}/

**Category B: name_conflict test**
- Add conflict detection to the command (check if name exists before creating)
- Use existing patterns from other commands
- If you need a new visitor in visitors.py, STOP and report to orchestrator

**Category C: with_decorators test**
- Usually requires handling @property, @staticmethod, @classmethod decorators
- Preserve decorator when moving/transforming code

**Category D: with_instance_vars test**
- Handle self.field references correctly
- May need to pass instance reference when moving code

**Category E: with_locals test**
- Handle local variable references
- May need to pass variables as parameters

**Category F: multiple_calls test**
- Handle multiple call sites to the refactored code
- Update all references, not just the first one

### Step 4: For each fix

1. Make the minimal change to pass the test
2. Run the test: `pytest {test_file}::{test_class}::{test_name} -v`
3. If passes, format and commit:
```bash
make format && git add -A && git commit -m "Fix {test_class}::{test_name}" && git push
```
4. If fails, iterate until it passes

### Step 5: Batch verification

After fixing all tests in your scope, verify:
```bash
pytest {test_file} -v
```

All tests should pass (some may still be skipped if you couldn't fix them).

## Final Report

Report back with:
1. Tests fixed (list each one)
2. Tests still skipped (with reason why you couldn't fix them)
3. Any shared file modifications needed (for orchestrator to handle)
4. Total commits made
```

---

## Phase 3: Orchestrator Monitoring

After spawning subagents:

1. Wait for all to complete
2. Collect reports from each
3. Handle any shared file modifications needed:
   - Work in main repo: `cd /Users/marshallyount/code/marshally/molting-cli`
   - Create a shared-utils branch if needed
   - Make changes, commit, push, create PR, merge to main
   - Each workstream can then rebase on main to get the shared changes

4. Create PRs for each workstream branch:
```bash
# For each completed workstream:
gh pr create --head fix-composing-methods --title "Fix skipped tests in composing_methods" --body "..."
gh pr create --head fix-dealing-with-generalization --title "Fix skipped tests in dealing_with_generalization" --body "..."
# etc.
```

5. Merge PRs one at a time (or use merge queue):
   - Merge first PR to main
   - Rebase next branch on main: `git rebase origin/main`
   - Merge next PR
   - Repeat

6. Cleanup worktrees after all merged:
```bash
cd /Users/marshallyount/code/marshally/molting-cli
git worktree remove ~/code/worktrees/molting-cli/fix-composing-methods
git worktree remove ~/code/worktrees/molting-cli/fix-dealing-with-generalization
git worktree remove ~/code/worktrees/molting-cli/fix-moving-features
git worktree remove ~/code/worktrees/molting-cli/fix-organizing-data
git worktree remove ~/code/worktrees/molting-cli/fix-simplifying-conditionals
git worktree remove ~/code/worktrees/molting-cli/fix-simplifying-method-calls
```

---

## Spawn Commands

After creating the worktrees in Phase 1, spawn all 6 workstreams in parallel using the Task tool.

Each subagent prompt should include:
- `{worktree_path}`: The full path to their worktree
- `{branch_name}`: Their branch name
- `{test_file}`: The test file they own
- `{category}`: The command category (e.g., "composing_methods")
- `{test_list}`: The specific tests to fix

**Example spawn (all 6 in a single message with 6 Task tool calls):**

```
Task 1:
  subagent_type: "general-purpose"
  model: "haiku"
  description: "Fix composing_methods tests"
  prompt: [Template with worktree_path=~/code/worktrees/molting-cli/fix-composing-methods, branch_name=fix-composing-methods, test_file=tests/test_composing_methods.py, category=composing_methods]

Task 2:
  subagent_type: "general-purpose"
  model: "haiku"
  description: "Fix dealing_with_generalization tests"
  prompt: [Template with worktree_path=~/code/worktrees/molting-cli/fix-dealing-with-generalization, ...]

... (4 more tasks)
```

**Summary of workstreams:**
| # | Category | Worktree | Tests |
|---|----------|----------|-------|
| 1 | composing_methods | fix-composing-methods | 8 |
| 2 | dealing_with_generalization | fix-dealing-with-generalization | 16 |
| 3 | moving_features | fix-moving-features | 13 |
| 4 | organizing_data | fix-organizing-data | 17 |
| 5 | simplifying_conditionals | fix-simplifying-conditionals | 24 |
| 6 | simplifying_method_calls | fix-simplifying-method-calls | 29 |
