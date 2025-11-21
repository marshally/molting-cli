# Replace Conditional with Polymorphism - TDD Task

## Overview
Implement the "replace-conditional-with-polymorphism" refactoring that transforms conditional logic into polymorphic method calls.

## Acceptance Criteria

### 1. RED: Create failing test fixture and test
- [ ] Create fixture files: `tests/fixtures/simplifying_conditionals/replace_conditional_with_polymorphism/simple/`
  - input.py: Contains a class with conditional logic
  - expected.py: Contains refactored code with polymorphic classes
- [ ] Add test method to `tests/test_simplifying_conditionals.py`
- [ ] Run test to confirm it fails

### 2. GREEN: Implement ReplaceConditionalWithPolymorphism class
- [ ] Create `molting/refactorings/simplifying_conditionals/replace_conditional_with_polymorphism.py`
- [ ] Implement initialization with target and type_field parameters
- [ ] Implement apply() method to refactor conditional logic
- [ ] Implement validate() method
- [ ] Run test to confirm it passes

### 3. REFACTOR: Add to CLI registry
- [ ] Add import to `molting/cli.py`
- [ ] Add entry to REFACTORING_REGISTRY
- [ ] Verify all tests pass

### 4. FINAL: Code quality and commits
- [ ] Run linter and fix any style issues
- [ ] Create appropriate commits for each phase
- [ ] Create PR with summary

## Notes
- Target format: "ClassName::method_name#L13-L20"
- Parameters: target (method range) and type_field (field containing type)
- Transform conditional type checking into class hierarchy with polymorphic methods
