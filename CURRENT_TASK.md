# Push Down Method - TDD Task (COMPLETED)

## Overview
Implement the "push-down-method" refactoring that moves a method from a superclass to specific subclasses that need it.

## Acceptance Criteria

### 1. RED: Create failing test fixture and test
- [x] Create fixture directory: `tests/fixtures/dealing_with_generalization/push_down_method/simple/`
  - input.py: Contains Employee superclass with get_quota() method, with Salesman and Engineer subclasses
  - expected.py: Contains refactored code with get_quota() only in Salesman subclass
- [x] Create `tests/test_dealing_with_generalization.py` with TestPushDownMethod class
- [x] Add test method that calls refactor("push-down-method", target="Employee::get_quota", to="Salesman")
- [x] Run test to confirm it fails

### 2. GREEN: Implement PushDownMethod class
- [x] Create `molting/refactorings/dealing_with_generalization/push_down_method.py`
- [x] Implement initialization with target and to parameters
- [x] Implement apply() method to move method from superclass to subclass(es)
- [x] Implement validate() method to check superclass and method exist
- [x] Run test to confirm it passes

### 3. REFACTOR: Add to CLI registry
- [x] Create `molting/refactorings/dealing_with_generalization/__init__.py`
- [x] Add import to `molting/cli.py`
- [x] Add entry to REFACTORING_REGISTRY: `"push-down-method": (PushDownMethod, ["target", "to"])`
- [x] Verify all tests pass

### 4. FINAL: Code quality and commits
- [x] Run linter and fix any style issues
- [x] Ensure all tests pass
- [x] Create appropriate commits for each phase
- [x] Create PR with summary

## Completion Status
✓ ALL CRITERIA MET - Task completed successfully!

## Commits Created
1. adc4ac9 - 🔴 Add failing test and fixtures for push-down-method refactoring
2. 3961ea0 - 🟢 Implement PushDownMethod refactoring class
3. 2e5ffd3 - 🔧 Register push-down-method refactoring in REFACTORING_REGISTRY

## Pull Request
https://github.com/marshally/molting-cli/pull/43

## Test Results
✓ tests/test_dealing_with_generalization.py::TestPushDownMethod::test_simple PASSED
✓ All linter checks passed
✓ No remaining issues
