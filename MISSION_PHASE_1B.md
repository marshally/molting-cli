## Mission: Implement Phase 1b - DelegateMemberDiscovery

You are implementing Phase 1b of the plan. This phase focuses on implementing the `DelegateMemberDiscovery` utility to fix 2 skipped tests for the `hide_delegate` refactoring.

## Setup

1.  **Adopt TDD and Refactoring Mindset:**
    -   Approach the task with strict Test-Driven Development (Red -> Green -> Refactor).
    -   Ensure all code is clean, idiomatic, and matches the existing project style.

2.  **Review Base Classes and Utilities:**
    -   Review `molting/core/` to understand existing patterns.
    -   Pay special attention to the `CallSiteUpdater` infrastructure in `molting/core/call_site_updater.py`.
    -   Analyze `molting/refactorings/moving_features/hide_delegate.py` to understand the current implementation.
    -   *Note: `molting/core/delegate_member_discovery.py` and `tests/core/test_delegate_member_discovery.py` already exist in the file tree. Check their current state.*

3.  **Understand Expected Output (Fixtures):**
    -   `tests/fixtures/moving_features/hide_delegate/with_instance_vars/input.py`
    -   `tests/fixtures/moving_features/hide_delegate/with_instance_vars/expected.py`
    -   `tests/fixtures/moving_features/hide_delegate/with_decorators/input.py`
    -   `tests/fixtures/moving_features/hide_delegate/with_decorators/expected.py`

## Problem Statement

The `hide_delegate` tests `with_instance_vars` and `with_decorators` require **auto-discovery** of members to delegate.

| Test | Input Target | Required Output |
|------|--------------|-----------------|
| `with_instance_vars` | `Employee::compensation` | Generate 7 delegating methods (4 fields + 3 methods) |
| `with_decorators` | `Employee::compensation` | Generate 2 delegating `@property` methods |

**Requirements:**
1.  Find the delegate class definition (e.g., `Compensation`).
2.  Enumerate ALL public members (fields, methods, properties).
3.  Generate a delegating method for EACH member on the server class.

## Workflow

Work through the requirements one at a time using strict TDD.

### Part 1: Implement DelegateMemberDiscovery Utility

1.  **RED**: Write/Ensure a failing test in `tests/core/test_delegate_member_discovery.py`.
2.  **GREEN**: Write minimal code in `molting/core/delegate_member_discovery.py` to make the test pass.
3.  **REFACTOR**: Clean up while keeping tests green.
4.  **COMMIT**: Create a commit for this piece of work.

**Acceptance Criteria to work through:**
- [ ] Find delegate class from `__init__` parameter type or assignment.
- [ ] Enumerate fields defined in `__init__` (`self.x = ...`).
- [ ] Enumerate regular methods (non-dunder, public).
- [ ] Enumerate `@property` methods with setter/deleter detection.
- [ ] Generate correct delegating methods for each member type.
- [ ] Preserve `@property` decorator on property delegations.

### Part 2: Fix Skipped Tests

For each test below:
1.  Unskip the test (remove `@pytest.mark.skip`).
2.  Run the test to confirm it fails.
3.  Update `molting/refactorings/moving_features/hide_delegate.py` to use `DelegateMemberDiscovery`.
4.  Run the test to confirm it passes.
5.  Commit the unskipped test + code changes together.

**Tests to Fix (in order):**
1.  `tests/moving_features/test_hide_delegate.py::test_with_instance_vars`
2.  `tests/moving_features/test_hide_delegate.py::test_with_decorators`

## Critical Rules

-   **NEVER CHANGE FIXTURES** to make tests pass - only change the implementation code.
-   Follow existing code patterns in `molting/core/`.
-   Use `libcst` for all AST operations (not the standard `ast` module).
-   All new files/functions need proper docstrings.
-   Run tests frequently with: `python -m pytest tests/ -v --tb=short`
-   Create atomic commits - one logical change per commit.

## Commit Message Format

Use this format for TDD commits:
```text
🧪 TDD: Implement <Feature Name> with tests

🤖 Generated with Gemini
Co-Authored-By: Gemini <noreply@google.com>
```

For test fixes:
```text
♻️ Fix: Enable <Test Name> for hide_delegate

- Unskipped test
- Integrated DelegateMemberDiscovery into hide_delegate

🤖 Generated with Gemini
Co-Authored-By: Gemini <noreply@google.com>
```

## Report Back

When complete, report:
1.  Summary of what was implemented.
2.  Number of commits made.
3.  Number of tests fixed (target: 2).
4.  Any issues encountered or deferred.
