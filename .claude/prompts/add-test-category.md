# Add Test Category Prompt

Use this prompt to spawn subagents that add a specific test category (e.g., `with_locals`, `with_instance_vars`, `name_conflict`) to refactoring test files.

## Variables to Replace

- `{TEST_FILE}` - The test file path (e.g., `tests/test_composing_methods.py`)
- `{TEST_CATEGORY}` - The test case category name (e.g., `with_locals`, `with_instance_vars`)
- `{WORKTREE_BASE}` - Base directory for worktrees (e.g., `~/code/worktrees/molting-cli`)
- `{BRANCH_NAME}` - Branch name for this work (e.g., `add-with-locals-composing-methods`)

---

## Subagent Prompt

```
You are adding `{TEST_CATEGORY}` test cases to `{TEST_FILE}`.

## Setup

1. Load the git-worktree skill
2. Create a new worktree at `{WORKTREE_BASE}/{BRANCH_NAME}` from the `main` branch
3. Change to the worktree directory for all subsequent work
4. Fetch origin and rebase from origin/main to ensure you have the latest code:
   ```bash
   git fetch origin && git rebase origin/main
   ```

## Context

Review the test strategy documentation at `docs/test-strategy.md` to understand:
- What `{TEST_CATEGORY}` tests should cover
- Which refactorings in `{TEST_FILE}` this category applies to

Review `{TEST_FILE}` to understand:
- The test class structure (each class tests one refactoring)
- The `fixture_category` for each test class
- How existing tests use `self.refactor()` with target and other params

Review existing `{TEST_CATEGORY}` fixtures (if any) at:
- `tests/fixtures/**/{TEST_CATEGORY}/input.py`
- `tests/fixtures/**/{TEST_CATEGORY}/expected.py`

## For Each Refactoring Test Class

For each test class in `{TEST_FILE}` where `{TEST_CATEGORY}` applies:

### 1. Create Fixture Files

Create the fixture directory and files:
- `tests/fixtures/{fixture_category}/{TEST_CATEGORY}/input.py`
- `tests/fixtures/{fixture_category}/{TEST_CATEGORY}/expected.py`

The `input.py` should:
- Have a docstring: `"""Example code for {refactoring} with {test_category}."""`
- Contain realistic code that exercises the `{TEST_CATEGORY}` scenario
- Follow patterns from existing fixtures in that category

The `expected.py` should:
- Have a docstring: `"""Expected output after {refactoring} with {test_category}."""`
- Show the correct transformation result

### 2. Add Test Method

Add a test method to the appropriate test class:

```python
def test_{TEST_CATEGORY}(self) -> None:
    """Test {refactoring} with {test_category_description}."""
    self.refactor("{refactoring-command}", target="...", ...)
```

### 3. Run the Test

Run ONLY the new test:
```bash
bin/rspec tests/{test_file}::TestClassName::test_{TEST_CATEGORY} -v
```

### 4. Commit Based on Result

**If the test PASSES:**
```bash
git add tests/fixtures/{fixture_category}/{TEST_CATEGORY}/ {TEST_FILE}
git commit -m "$(cat <<'EOF'
🧪 Add {TEST_CATEGORY} test for {refactoring}

Test command:
bin/rspec tests/{test_file}::TestClassName::test_{TEST_CATEGORY} -v

Result: PASSED
{paste actual test output here}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**If the test FAILS:**

First, mark the test as skipped:
```python
import pytest

@pytest.mark.skip(reason="Implementation needed for {TEST_CATEGORY}")
def test_{TEST_CATEGORY}(self) -> None:
    ...
```

Then commit:
```bash
git add tests/fixtures/{fixture_category}/{TEST_CATEGORY}/ {TEST_FILE}
git commit -m "$(cat <<'EOF'
❌ Add skipped {TEST_CATEGORY} test for {refactoring}

Test command:
bin/rspec tests/{test_file}::TestClassName::test_{TEST_CATEGORY} -v

Result: FAILED (marked as skipped)
{paste actual test output/error here}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 5. Repeat for Each Applicable Refactoring

Work through each test class in `{TEST_FILE}` one at a time:
- Create fixtures
- Add test
- Run test
- Commit appropriately
- Move to next refactoring

## Finalize

After all tests are added and committed:

1. Push the branch:
```bash
git push -u origin {BRANCH_NAME}
```

2. Create a PR:
```bash
gh pr create --title "Add {TEST_CATEGORY} tests to {TEST_FILE}" --body "$(cat <<'EOF'
## Summary
- Adds `{TEST_CATEGORY}` test cases for refactorings in `{TEST_FILE}`
- Each test has corresponding fixtures in `tests/fixtures/`

## Test Results
🧪 = passing test
❌ = skipped test (implementation needed)

[List each test added with its emoji status]

## Test Category: `{TEST_CATEGORY}`
{Description from docs/test-strategy.md}

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

3. Return the PR URL and a summary of:
   - How many tests were added
   - How many passed vs skipped
   - Any issues encountered
```

---

## Example Usage

To add `with_locals` tests to `tests/test_composing_methods.py`:

```
Spawn a subagent with:
- TEST_FILE = tests/test_composing_methods.py
- TEST_CATEGORY = with_locals
- WORKTREE_BASE = ~/code/worktrees/molting-cli
- BRANCH_NAME = add-with-locals-composing-methods
```

## Test Files to Process

The main refactoring test files are:
- `tests/test_composing_methods.py` - Extract Method, Inline Method, etc.
- `tests/test_organizing_data.py` - Self Encapsulate Field, Replace Data Value, etc.
- `tests/test_simplifying_conditionals.py` - Decompose Conditional, etc.
- `tests/test_simplifying_method_calls.py` - Rename Method, Add Parameter, etc.
- `tests/test_moving_features.py` - Move Method, Move Field, etc.
- `tests/test_dealing_with_generalization.py` - Pull Up Method, Push Down Method, etc.
