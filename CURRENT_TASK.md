# Replace Magic Number with Symbolic Constant - TDD Task

## Feature Description
Implement the "replace-magic-number-with-symbolic-constant" refactoring CLI command using libcst for AST transformation.

From Martin Fowler's catalog: "You have a literal number with a particular meaning. Create a constant, name it after the meaning, and replace the number with it."

## CLI Syntax
```bash
molting replace-magic-number-with-symbolic-constant src/foo.py::calculate#L10 "0.05" TAX_RATE
```

## Acceptance Criteria

- [ ] **Parse line number from target** - Extract line number from target specification format (e.g., `method#L10`)
- [ ] **Replace simple magic number in expression** - Find and replace a numeric literal on target line with constant name
- [ ] **Add constant declaration at module level** - Insert constant declaration at top of module
- [ ] **Replace multiple occurrences of same number** - Replace all instances of the magic number throughout file
- [ ] **Handle magic numbers in class methods** - Support replacing numbers in methods within classes
- [ ] **Handle invalid targets** - Raise appropriate errors for malformed targets
- [ ] **CLI command integration** - Integrate with Click CLI in molting/cli.py

## Test Structure
Tests: `tests/test_replace_magic_number_with_symbolic_constant.py`
Implementation: `molting/refactorings/organizing_data/replace_magic_number_with_symbolic_constant.py`
CLI: Update `molting/cli.py` (add to REFACTORING_REGISTRY)

## Example Transformation

**Before:**
```python
def calculate_tax(amount):
    return amount * 0.05
```

**After** `molting replace-magic-number-with-symbolic-constant file.py::calculate_tax#L2 "0.05" TAX_RATE`:
```python
TAX_RATE = 0.05

def calculate_tax(amount):
    return amount * TAX_RATE
```
