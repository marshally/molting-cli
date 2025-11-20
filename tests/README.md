# Molting CLI Test Suite

Comprehensive test suite for all refactoring operations based on Martin Fowler's refactoring catalog.

## Structure

```
tests/
  conftest.py                      # Test base class and shared fixtures
  test_composing_methods.py        # Tests for Composing Methods category
  test_moving_features.py          # Tests for Moving Features category
  test_organizing_data.py          # Tests for Organizing Data category
  test_simplifying_conditionals.py # Tests for Simplifying Conditionals category
  test_simplifying_method_calls.py # Tests for Simplifying Method Calls category
  test_dealing_with_generalization.py # Tests for Generalization category
  fixtures/
    composing_methods/
      extract_method/
        simple/
          input.py                 # Input code before refactoring
          expected.py              # Expected output after refactoring
        with_locals/
          input.py
          expected.py
      inline_method/
        simple/
          input.py
          expected.py
    moving_features/
      move_method/
        ...
```

## Writing Tests

### Convention-Based Testing

Tests use a **convention-based approach** where:
1. Test method name (minus `test_` prefix) maps to fixture directory name
2. Each fixture directory contains `input.py` and `expected.py`
3. Test parameters are specified in the test method, not in JSON files

### Example

```python
# tests/test_composing_methods.py
from tests.conftest import RefactoringTestBase

class TestExtractMethod(RefactoringTestBase):
    fixture_category = "composing_methods/extract_method"

    def test_simple(self):
        """Extract a simple code block with no local variables."""
        self.refactor(
            "extract-method",
            target="Order::print_owing#L6-L8",
            name="print_banner"
        )
```

This test:
- Looks for fixtures in `tests/fixtures/composing_methods/extract_method/simple/`
- Copies `input.py` to a temporary directory
- Runs the refactoring with specified parameters
- Compares result against `expected.py`
- Cleans up automatically

### Adding a New Test

1. **Create fixture directory**:
   ```bash
   mkdir -p tests/fixtures/composing_methods/extract_method/my_new_case
   ```

2. **Create `input.py`**:
   ```python
   # tests/fixtures/composing_methods/extract_method/my_new_case/input.py
   class Example:
       def method(self):
           # code to refactor
           pass
   ```

3. **Create `expected.py`**:
   ```python
   # tests/fixtures/composing_methods/extract_method/my_new_case/expected.py
   class Example:
       def method(self):
           self.extracted()

       def extracted(self):
           # refactored code
           pass
   ```

4. **Add test method**:
   ```python
   # tests/test_composing_methods.py
   class TestExtractMethod(RefactoringTestBase):
       fixture_category = "composing_methods/extract_method"

       def test_my_new_case(self):
           """Description of what this case tests."""
           self.refactor(
               "extract-method",
               target="Example::method#L3-L4",
               name="extracted"
           )
   ```

That's it! The test infrastructure handles:
- Copying fixtures to temporary directory
- Running the refactoring
- Comparing results (AST-based by default)
- Cleanup

## Test Base Class

### `RefactoringTestBase`

Base class providing automatic fixture management.

**Key attributes:**
- `fixture_category`: Path to fixtures (e.g., `"composing_methods/extract_method"`)
- `self.tmp_path`: Temporary directory for this test
- `self.test_file`: Path to input.py (in tmp_path)
- `self.expected_file`: Path to expected.py (in fixtures)

**Key methods:**
- `self.refactor(name, **params)`: Run refactoring and assert matches expected
- `self.assert_matches_expected(normalize=True)`: Manual assertion if needed

## Validation Strategy

By default, tests use **AST-based comparison** which:
- Ignores whitespace and formatting differences
- Focuses on semantic correctness
- Shows readable diffs on failure

For exact string comparison:
```python
self.refactor("extract-method", ...)
self.assert_matches_expected(normalize=False)  # Exact string match
```

## Running Tests

```bash
# Run all tests
pytest

# Run tests for specific category
pytest tests/test_composing_methods.py

# Run specific test class
pytest tests/test_composing_methods.py::TestExtractMethod

# Run specific test
pytest tests/test_composing_methods.py::TestExtractMethod::test_simple

# Verbose output
pytest -v

# Show print statements
pytest -s
```

## Test Isolation

Each test:
1. Gets a fresh temporary directory (`tmp_path`)
2. Has fixtures copied to that directory
3. Runs in complete isolation
4. Cleans up automatically

No manual cleanup or state management required!

## Adding New Refactoring Categories

To add tests for a new category (e.g., "Moving Features"):

1. **Create test file**:
   ```python
   # tests/test_moving_features.py
   from tests.conftest import RefactoringTestBase

   class TestMoveMethod(RefactoringTestBase):
       fixture_category = "moving_features/move_method"

       def test_simple(self):
           self.refactor("move-method",
               target="Customer::calculate_discount",
               to="Order"
           )
   ```

2. **Create fixtures**:
   ```bash
   mkdir -p tests/fixtures/moving_features/move_method/simple
   # Add input.py and expected.py
   ```

Done!

## Best Practices

1. **One test per fixture** - Keep tests simple and focused
2. **Descriptive names** - Use clear fixture directory names (`simple`, `with_locals`, `complex_nesting`)
3. **Document edge cases** - Add docstrings explaining what each test validates
4. **Real-world examples** - Use realistic code examples from the documentation
5. **Start simple** - Begin with basic cases, add complex ones later

## Coverage Goals

Aim to test:
- ✅ Simple/basic cases
- ✅ Edge cases (empty methods, single statements)
- ✅ Complex cases (nested structures, multiple variables)
- ✅ Error cases (invalid targets, syntax errors)
- ✅ Integration (multiple refactorings in sequence)
