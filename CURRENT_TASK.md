# Replace Exception with Test Refactoring - TDD Task

## Feature Description
Implement the "replace-exception-with-test" refactoring that transforms try-except blocks into explicit condition checks.

## Acceptance Criteria

- [ ] AC1: Implementation file exists at molting/refactorings/simplifying_method_calls/replace_exception_with_test.py
- [ ] AC2: Class extends RefactoringBase with apply() and validate() methods
- [ ] AC3: Can parse target specification (function name with optional line ranges)
- [ ] AC4: Transform try-except IndexError blocks into explicit length checks
- [ ] AC5: Test simple case passes (input.py -> expected.py)
- [ ] AC6: Register refactoring in REFACTORING_REGISTRY in cli.py
- [ ] AC7: All linters pass (ruff check and ruff format)
- [ ] AC8: Push to GitHub and create PR

## Current Status
Starting with RED phase - no implementation yet.
