# Replace Constructor with Factory Function - TDD Implementation

## Feature Requirements
Implement the "replace-constructor-with-factory-function" refactoring CLI command using rope's introduce factory refactoring.

## Acceptance Criteria

- [ ] 1. Test class target parsing (e.g., "Employee::__init__" or "Employee")
- [ ] 2. Test basic factory function creation
- [ ] 3. Test integration with CLI command "replace-constructor-with-factory-function"
- [ ] 4. Test refactoring applies to target class
- [ ] 5. Test validation of invalid targets
- [ ] 6. Test complete CLI integration

## Implementation Files
- Test: `tests/test_replace_constructor_with_factory_function.py`
- Implementation: `molting/refactorings/simplifying_method_calls/replace_constructor_with_factory_function.py`
- CLI: Update `molting/cli.py`

## Notes
- Use rope's IntroduceFactory from rope.refactor.introduce_factory
- Parse target in format "ClassName::__init__" or "ClassName"
- Follow existing RefactoringBase pattern
- Fixtures already exist at tests/fixtures/simplifying_method_calls/replace_constructor_with_factory_function/simple/
