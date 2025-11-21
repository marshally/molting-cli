# Pull Up Field Refactoring - TDD Task

## Feature Description
Implement the "pull-up-field" refactoring that moves a field from subclasses to the superclass.

## Acceptance Criteria

- [ ] AC1: Directory `molting/refactorings/dealing_with_generalization/` exists with `__init__.py`
- [ ] AC2: Implementation file exists at `molting/refactorings/dealing_with_generalization/pull_up_field.py`
- [ ] AC3: Class `PullUpField` extends `RefactoringBase` with `apply()` and `validate()` methods
- [ ] AC4: Can parse target specification (ClassName::field_name, to=SuperclassName)
- [ ] AC5: Transform field assignments from subclasses to superclass __init__
- [ ] AC6: Update subclass __init__ to call super().__init__() with field values
- [ ] AC7: Test simple case passes (input.py -> expected.py)
- [ ] AC8: Register refactoring in REFACTORING_REGISTRY in cli.py
- [ ] AC9: All linters pass (ruff check and ruff format)
- [ ] AC10: Push to GitHub and create PR

## Current Status
Starting with RED phase - no implementation yet.
