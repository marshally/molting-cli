# Molting CLI

A command-line tool for performing refactorings from Martin Fowler's "Refactoring: Improving the Design of Existing Code" on Python codebases.

Built on [libCST](https://libcst.readthedocs.io/) and [rope](https://github.com/python-rope/rope) for safe, automated code transformations.

## Installation

```bash
pip install molting-cli
```

## CLI Syntax

```bash
molting [refactoring-name] <target> [arguments] [flags]
```

### Target Specification

Targets use pytest-style syntax with optional GitHub-style line numbers:

- **Module**: `path/to/file.py`
- **Class**: `path/to/file.py::ClassName`
- **Method**: `path/to/file.py::ClassName::method_name`
- **Symbol**: `path/to/file.py::ClassName::method_name::variable_name`
- **With line range**: `path/to/file.py::ClassName::method_name#L10-L15`
- **Single line**: `path/to/file.py::ClassName::method_name#L10`

## Usage Examples

### Simple Refactorings (Positional Arguments)

#### Rename
Rename a variable, method, class, or module.

```bash
# Rename a method
molting rename src/foo.py::Calculator::add_numbers calculate_sum

# Rename a class
molting rename src/foo.py::OldClassName NewClassName

# Rename a variable
molting rename src/foo.py::Calculator::compute::result output
```

#### Inline Variable
Remove a variable by replacing all references with its value.

```bash
molting inline-temp src/foo.py::Calculator::compute::temp_value
```

#### Inline Method
Replace calls to a method with the method's body.

```bash
molting inline src/foo.py::Calculator::simple_helper
```

#### Extract Variable
Extract an expression into a named variable.

```bash
# Extract expression on lines 10-12 into a variable
molting extract-variable src/foo.py::Calculator::compute#L10-L12 discount_rate
```

#### Extract Method
Extract a code block into a new method.

```bash
# Extract lines 15-20 into a new method
molting extract-method src/foo.py::Calculator::compute#L15-L20 calculate_tax

# Extract from a single line
molting extract-method src/foo.py::Calculator::compute#L18 validate_input
```

#### Extract Function
Extract code into a module-level function.

```bash
molting extract-function src/foo.py::Calculator::helper#L5-L10 format_currency
```

### Complex Refactorings (With Flags)

#### Move Method
Move a method from one class to another.

```bash
molting move-method src/foo.py::Customer::calculate_discount --to Order
```

#### Move Field
Move a field from one class to another.

```bash
molting move-field src/foo.py::Customer::address --to Account
```

#### Extract Class
Extract fields and methods into a new class.

```bash
molting extract-class src/foo.py::Person \
  --fields name,phone,email \
  --methods get_contact_info,update_contact \
  --name ContactInfo
```

#### Pull Up Method
Move a method from a subclass to its superclass.

```bash
molting pull-up-method src/foo.py::Manager::calculate_bonus --to Employee
```

#### Push Down Method
Move a method from a superclass to specific subclasses.

```bash
molting push-down-method src/foo.py::Employee::specialized_task --to Manager,Engineer
```

#### Introduce Parameter Object
Replace multiple parameters with a parameter object.

```bash
molting introduce-parameter-object src/foo.py::Order::create \
  --params customer_name,customer_email,customer_phone \
  --name CustomerInfo
```

#### Replace Temp with Query
Replace a temporary variable with a method call.

```bash
molting replace-temp-with-query src/foo.py::Order::calculate_total::base_price
```

#### Replace Conditional with Polymorphism
Replace conditional logic with polymorphic method calls.

```bash
molting replace-conditional-with-polymorphism src/foo.py::Bird::get_speed#L10-L20
```

## Documentation

For detailed documentation on each refactoring, see:

- [Composing Methods](docs/composing-methods.md) - Refactorings for improving method structure
- [Moving Features Between Objects](docs/moving-features.md) - Refactorings for moving functionality between classes
- [Organizing Data](docs/organizing-data.md) - Refactorings for data structures and encapsulation
- [Simplifying Conditional Expressions](docs/simplifying-conditionals.md) - Refactorings for cleaner conditionals
- [Simplifying Method Calls](docs/simplifying-method-calls.md) - Refactorings for better method interfaces
- [Dealing with Generalization](docs/dealing-with-generalization.md) - Refactorings for inheritance hierarchies

## Supported Refactorings

### Composing Methods
- `extract-method` - Extract code into a new method
- `extract-function` - Extract code into a module-level function
- `inline-method` - Inline a method into its callers
- `inline-temp` - Inline a temporary variable
- `replace-temp-with-query` - Replace temporary variable with a method
- `introduce-explaining-variable` - Extract complex expression into a variable
- `split-temporary-variable` - Make separate variables for separate purposes
- `remove-assignments-to-parameters` - Use a temporary variable instead
- `replace-method-with-method-object` - Turn a method into its own object
- `substitute-algorithm` - Replace algorithm with a clearer one

### Moving Features Between Objects
- `move-method` - Move a method to another class
- `move-field` - Move a field to another class
- `extract-class` - Split a class into two classes
- `inline-class` - Merge a class into another
- `hide-delegate` - Create delegating methods to hide delegation
- `remove-middle-man` - Call the delegate directly
- `introduce-foreign-method` - Add method to a class you can't modify
- `introduce-local-extension` - Create a subclass or wrapper for extensions

### Organizing Data
- `self-encapsulate-field` - Create getter/setter for field access
- `replace-data-value-with-object` - Turn data item into an object
- `change-value-to-reference` - Change value object to reference object
- `change-reference-to-value` - Change reference object to value object
- `replace-array-with-object` - Replace array with an object
- `duplicate-observed-data` - Copy data to domain object
- `change-unidirectional-association-to-bidirectional` - Add back pointers
- `change-bidirectional-association-to-unidirectional` - Remove back pointers
- `replace-magic-number-with-symbolic-constant` - Create named constant
- `encapsulate-field` - Make field private with accessors
- `encapsulate-collection` - Return read-only view of collection
- `replace-type-code-with-class` - Replace type code with a class
- `replace-type-code-with-subclasses` - Replace type code with subclasses
- `replace-type-code-with-state-strategy` - Replace type code with State/Strategy

### Simplifying Conditional Expressions
- `decompose-conditional` - Extract condition and branches into methods
- `consolidate-conditional-expression` - Combine conditions into one
- `consolidate-duplicate-conditional-fragments` - Move common code outside conditionals
- `remove-control-flag` - Use break or return instead
- `replace-nested-conditional-with-guard-clauses` - Use guard clauses
- `replace-conditional-with-polymorphism` - Use polymorphic dispatch
- `introduce-null-object` - Replace null checks with null object
- `introduce-assertion` - Make assumptions explicit with assertions

### Simplifying Method Calls
- `rename-method` - Rename a method for clarity
- `add-parameter` - Add a parameter to a method
- `remove-parameter` - Remove an unused parameter
- `separate-query-from-modifier` - Split read and write operations
- `parameterize-method` - Combine similar methods with a parameter
- `replace-parameter-with-explicit-methods` - Create separate methods
- `preserve-whole-object` - Pass entire object instead of values
- `replace-parameter-with-method-call` - Call method instead of passing value
- `introduce-parameter-object` - Group parameters into an object
- `remove-setting-method` - Remove setter for field set in constructor
- `hide-method` - Make method private
- `replace-constructor-with-factory-function` - Use factory function
- `replace-error-code-with-exception` - Throw exception instead
- `replace-exception-with-test` - Use conditional check instead

### Dealing with Generalization
- `pull-up-field` - Move field to superclass
- `pull-up-method` - Move method to superclass
- `pull-up-constructor-body` - Move constructor code to superclass
- `push-down-method` - Move method to subclass
- `push-down-field` - Move field to subclass
- `extract-subclass` - Create subclass for special case
- `extract-superclass` - Create superclass for common features
- `extract-interface` - Create interface for common methods
- `collapse-hierarchy` - Merge subclass into superclass
- `form-template-method` - Extract common algorithm to superclass
- `replace-inheritance-with-delegation` - Use composition instead
- `replace-delegation-with-inheritance` - Use inheritance instead

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/marshally/molting-cli.git
cd molting-cli

# Install dependencies with Poetry
poetry install

# Install git hooks (optional but recommended)
cp hooks/pre-commit .git/hooks/pre-commit
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

### Running Linters

We use `make` to run code quality tools:

```bash
make help        # Show all available commands
make format      # Auto-fix formatting with black and ruff
make lint        # Check code style without modifying
make typecheck   # Run mypy type checking
make test        # Run tests
make all         # Format, typecheck, and test everything
```

### Managing Git Hooks

#### Pre-commit Hook (Staged Files Only)

Runs automatically before each commit on **staged Python files only**:

```bash
# Install the pre-commit hook
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**What it does:**
- Runs **black**, **ruff**, **mypy** on staged files
- **If linters made changes**: Creates a separate commit with just the formatting fixes, then asks you to run `git commit` again
- **If no changes**: Proceeds with your commit
- Keeps linter auto-fixes separate from your code changes

**Limitation:** Only checks staged files, not the entire codebase.

#### Pre-push Hook (Entire Codebase)

Runs automatically before each push on the **entire codebase**:

```bash
# Install the pre-push hook
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

**What it does:**
- Runs **black --check**, **ruff check**, **mypy** on entire codebase
- Checks for uncommitted beads JSONL changes (if using bd issue tracking)
- Blocks the push if any checks fail
- Catches issues that pre-commit hook might miss

**Recommended:** Install both hooks. Pre-commit for fast feedback on staged files, pre-push as final check before pushing.

#### Bypassing Hooks

To skip hooks temporarily (not recommended):
```bash
# Skip pre-commit hook
git commit --no-verify

# Skip pre-push hook
git push --no-verify
```

#### Uninstalling Hooks

To remove the hooks:
```bash
rm .git/hooks/pre-commit
rm .git/hooks/pre-push
```

#### Updating Hooks

If hooks are updated in the repository:
```bash
cp hooks/pre-commit .git/hooks/pre-commit
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

### Running Tests

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run specific test file
pytest tests/test_composing_methods.py -v

# Run specific test
pytest tests/test_composing_methods.py::TestExtractMethod::test_simple -v
```

## Continuous Integration

Every push to a pull request automatically runs:

### Lint Job
- **Black** - Code formatting check
- **Ruff** - Linting
- **Mypy** - Type checking

### Test Job
- **Pytest** - Test suite with coverage
- Runs on Python 3.8, 3.9, 3.10, 3.11, and 3.12

All checks must pass before merging. You can run the same checks locally:
```bash
make lint        # Check formatting and linting
make typecheck   # Run type checking
make test        # Run tests
```

## Contributing

Contributions welcome! Please open an issue or PR.

All pull requests must pass CI checks (linting and tests) before merging.

## License

MIT

## Acknowledgments

- Martin Fowler's "Refactoring: Improving the Design of Existing Code"
- [libCST](https://libcst.readthedocs.io/) - Concrete Syntax Tree parser
- [rope](https://github.com/python-rope/rope) - Python refactoring library
