# Test Strategy for Molting CLI

This document outlines the comprehensive testing strategy for all 66 refactoring operations.

## Test Case Types

### 1. Edge Cases

**Purpose**: Validate behavior at the boundaries of normal operation.

- **`empty`** - Empty methods, classes, or minimal code
  - Example: Empty method body, class with no methods
  - Applies to: Most refactorings
  
- **`single_statement`** - Single line methods/functions
  - Example: `def foo(): return 42`
  - Applies to: Extract Method, Inline Method, Extract Function
  
- **`no_parameters`** - Methods with no parameters
  - Example: `def calculate(): return self.x * self.y`
  - Applies to: Move Method, Extract Method, Parameterize Method
  
- **`many_parameters`** - Methods with 5+ parameters
  - Example: Methods with extensive parameter lists
  - Applies to: Introduce Parameter Object, Remove Parameter, Add Parameter

### 2. Variable Handling

**Purpose**: Ensure correct handling of different variable scopes and lifetimes.

- **`with_locals`** - Local variables that need special handling
  - Example: Extract method where locals become parameters/return values
  - Priority: **HIGH** - Critical for most refactorings
  - Applies to: Extract Method, Replace Temp with Query, Inline Temp
  
- **`with_instance_vars`** - Heavy use of self.field
  - Example: Methods that primarily manipulate instance state
  - Priority: **HIGH** - Essential for class refactorings
  - Applies to: Move Method, Extract Class, Self Encapsulate Field
  
- **`with_closure`** - Nested functions capturing variables
  - Example: Inner function referencing outer scope variables
  - Applies to: Extract Function, Replace Method with Method Object
  
- **`with_globals`** - References global variables
  - Example: Functions using module-level variables
  - Applies to: Extract Function, Move Method
  
- **`reassignment`** - Variables assigned multiple times
  - Example: Accumulator variables in loops
  - Applies to: Split Temporary Variable, Introduce Explaining Variable

### 3. Complex Cases

**Purpose**: Test realistic, non-trivial code scenarios.

- **`nested_structures`** - Nested classes, nested functions
  - Example: Class within class, function within function
  - Priority: **MEDIUM** - Common in real code
  - Applies to: Extract Class, Extract Method, Move Method
  
- **`multiple_calls`** - Target called from multiple places
  - Example: Method invoked 3+ times across codebase
  - Priority: **HIGH** - Must update all call sites
  - Applies to: Rename Method, Change Method Signature, Move Method
  
- **`complex_expressions`** - Long, complex calculations
  - Example: Nested mathematical operations, chained method calls
  - Applies to: Introduce Explaining Variable, Extract Method
  
- **`deep_nesting`** - Deeply nested if/for/while blocks
  - Example: 3+ levels of nesting
  - Applies to: Decompose Conditional, Replace Nested Conditional with Guard Clauses
  
- **`multiple_returns`** - Multiple return statements
  - Example: Early returns, guard clauses
  - Applies to: Extract Method, Replace Nested Conditional with Guard Clauses

### 4. Python-Specific

**Purpose**: Handle Python language features correctly.

- **`with_decorators`** - Methods with decorators
  - Example: `@property`, `@staticmethod`, `@classmethod`, custom decorators
  - Priority: **HIGH** - Very common in Python
  - Applies to: Rename Method, Move Method, Pull Up Method
  
- **`with_type_hints`** - Full type annotations
  - Example: `def foo(x: int) -> str:`
  - Priority: **MEDIUM** - Modern Python standard
  - Applies to: All refactorings (must preserve types)
  
- **`with_async`** - async/await patterns
  - Example: `async def fetch(): await api.get()`
  - Applies to: Extract Method, Move Method, Rename Method
  
- **`with_generators`** - yield statements
  - Example: Generator functions with yield
  - Applies to: Extract Method, Inline Method
  
- **`with_context_managers`** - with statements
  - Example: `with open('file') as f:`
  - Applies to: Extract Method, Move Method
  
- **`magic_methods`** - `__init__`, `__str__`, `__eq__`, etc.
  - Example: Special methods with double underscores
  - Applies to: Rename Method, Pull Up Method, Push Down Method

### 5. Error Cases

**Purpose**: Validate error handling and user feedback.

- **`invalid_target`** - Non-existent method/class
  - Example: Trying to refactor `Foo::bar` when `bar` doesn't exist
  - Priority: **HIGH** - Common user error
  - Applies to: All refactorings
  
- **`syntax_error`** - Invalid Python syntax in input
  - Example: Malformed code that won't parse
  - Applies to: All refactorings
  
- **`name_conflict`** - New name already exists
  - Example: Renaming method to name that's already taken
  - Priority: **HIGH** - Must prevent breaking code
  - Applies to: Rename Method, Extract Method, Extract Class
  
- **`circular_dependency`** - Would create circular import
  - Example: Moving method would require circular import
  - Applies to: Move Method, Move Field, Extract Class
  
- **`type_mismatch`** - Incompatible types (for typed code)
  - Example: Attempting incompatible refactoring on typed code
  - Applies to: Move Method, Change Method Signature

### 6. Inheritance/OOP

**Purpose**: Handle object-oriented patterns correctly.

- **`with_inheritance`** - Subclass overriding methods
  - Example: Parent and child both define same method
  - Priority: **MEDIUM** - Common in OOP code
  - Applies to: Pull Up Method, Push Down Method, Rename Method
  
- **`multiple_inheritance`** - Diamond problem scenarios
  - Example: Class inheriting from multiple parents
  - Applies to: Pull Up Method, Extract Superclass
  
- **`abstract_methods`** - ABC abstract methods
  - Example: Methods decorated with `@abstractmethod`
  - Applies to: Pull Up Method, Extract Interface
  
- **`polymorphic`** - Multiple implementations
  - Example: Same method name in different classes
  - Applies to: Replace Conditional with Polymorphism, Form Template Method

### 7. Integration Cases

**Purpose**: Test composition and multi-file scenarios.

- **`with_imports`** - Import statements involved
  - Example: Moving class requires updating imports
  - Priority: **MEDIUM** - Real code has imports
  - Applies to: Move Method, Extract Class, Move Field
  
- **`multiple_files`** - Refactoring spans files
  - Example: Method called from different modules
  - Applies to: Move Method, Rename Method, Extract Class
  
- **`sequence`** - Multiple refactorings applied in order
  - Example: Extract Method → Rename Method → Move Method
  - Priority: **MEDIUM** - How refactorings are actually used
  - Applies to: All refactorings

### 8. Real-World Patterns

**Purpose**: Test common coding patterns.

- **`with_logging`** - Common logging patterns
  - Example: Methods with `logger.info()` calls
  - Applies to: Extract Method, Move Method
  
- **`with_error_handling`** - try/except blocks
  - Example: Exception handling within method
  - Applies to: Extract Method, Replace Error Code with Exception
  
- **`with_validation`** - Input validation logic
  - Example: Parameter validation at method start
  - Applies to: Extract Method, Introduce Assertion
  
- **`design_patterns`** - Factory, Strategy, Observer patterns
  - Example: Established design pattern implementations
  - Applies to: Various refactorings depending on pattern

## Priority Matrix

### Must Have (Implement First)

| Test Case Type | Priority | Refactorings | Reason |
|----------------|----------|--------------|--------|
| `with_locals` | **CRITICAL** | Extract Method, Replace Temp with Query, Inline Temp | Most common complexity in method extraction |
| `with_instance_vars` | **CRITICAL** | Move Method, Extract Class, Self Encapsulate Field | Core to class-based refactorings |
| `multiple_calls` | **CRITICAL** | Rename Method, Move Method, Change Signature | Must update all call sites |
| `name_conflict` | **CRITICAL** | Rename Method, Extract Method, Extract Class | Prevents breaking code |
| `with_decorators` | **HIGH** | Most method refactorings | Ubiquitous in Python |
| `invalid_target` | **HIGH** | All refactorings | Common user error |

### Should Have (Implement Second)

| Test Case Type | Priority | Refactorings | Reason |
|----------------|----------|--------------|--------|
| `with_type_hints` | **MEDIUM** | All refactorings | Modern Python standard |
| `nested_structures` | **MEDIUM** | Extract Class, Extract Method, Move Method | Real code is often nested |
| `with_error_handling` | **MEDIUM** | Extract Method, Move Method | Common pattern |
| `empty` | **MEDIUM** | Most refactorings | Edge case validation |
| `with_inheritance` | **MEDIUM** | Pull Up, Push Down, Rename | Common in OOP |

### Nice to Have (Implement Later)

| Test Case Type | Priority | Refactorings | Reason |
|----------------|----------|--------------|--------|
| `with_async` | **LOW** | Extract Method, Move Method | Growing importance |
| `multiple_files` | **LOW** | Move Method, Extract Class | Complex but important |
| `sequence` | **LOW** | All refactorings | Tests composition |
| `with_generators` | **LOW** | Extract Method | Less common |

## Implementation Roadmap

### Phase 1: Critical Test Cases (Week 1-2)
Focus on test cases that cover the most common real-world scenarios:

1. **Extract Method**
   - `with_locals` - variables that need to become parameters
   - `multiple_calls` - ensure all call sites updated
   - `with_instance_vars` - accessing self.field
   - `with_decorators` - preserve decorators

2. **Rename Method**
   - `multiple_calls` - update all references
   - `name_conflict` - detect existing names
   - `with_inheritance` - handle overrides
   - `invalid_target` - error on missing method

3. **Move Method**
   - `with_instance_vars` - handle self references
   - `multiple_calls` - update call sites
   - `with_imports` - update imports

### Phase 2: High-Value Test Cases (Week 3-4)
Expand coverage to handle more complex scenarios:

1. Add `with_type_hints` to all refactorings
2. Add `nested_structures` for structural refactorings
3. Add `with_error_handling` for method-level refactorings
4. Add error cases for all refactorings

### Phase 3: Comprehensive Coverage (Week 5-6)
Complete the test suite:

1. Add Python-specific cases (`with_async`, `with_generators`)
2. Add integration cases (`multiple_files`, `sequence`)
3. Add real-world pattern tests
4. Edge case completion

## Test Case Naming Convention

Follow this pattern for fixture directories:
```
tests/fixtures/<category>/<refactoring>/<test_case_type>/
```

Examples:
- `tests/fixtures/composing_methods/extract_method/with_locals/`
- `tests/fixtures/composing_methods/extract_method/multiple_calls/`
- `tests/fixtures/moving_features/move_method/with_instance_vars/`

## Creating New Test Cases

### Template for Adding Test Cases

1. **Create fixture directory**:
   ```bash
   mkdir -p tests/fixtures/<category>/<refactoring>/<test_type>
   ```

2. **Create input.py** with realistic code:
   ```python
   # Example showing the pattern to test
   class Example:
       def method_with_locals(self):
           x = 10
           y = 20
           result = x + y
           print(result)
   ```

3. **Create expected.py** with correct transformation:
   ```python
   class Example:
       def method_with_locals(self):
           result = self.calculate_sum()
           print(result)
       
       def calculate_sum(self):
           x = 10
           y = 20
           return x + y
   ```

4. **Add test method** to test class:
   ```python
   def test_with_locals(self):
       """Extract method with local variables."""
       self.refactor(
           "extract-method",
           target="Example::method_with_locals#L3-L5",
           name="calculate_sum"
       )
   ```

## Refactoring-Specific Recommendations

### Extract Method
**Most Important Test Cases**:
1. `with_locals` - Variables used within extracted region
2. `with_locals_return` - Local variable needs to be returned
3. `with_multiple_locals` - Multiple locals become parameters
4. `with_instance_vars` - Uses self.field
5. `multiple_returns` - Extracted code has early returns

### Rename Method
**Most Important Test Cases**:
1. `multiple_calls` - Method called from many places
2. `name_conflict` - Target name already exists
3. `with_inheritance` - Overridden in subclass
4. `with_decorators` - Property or static method

### Move Method
**Most Important Test Cases**:
1. `with_instance_vars` - Heavy use of self
2. `cross_file` - Method used from other files
3. `with_multiple_uses` - High coupling to target class

### Replace Conditional with Polymorphism
**Most Important Test Cases**:
1. `multiple_branches` - Many if/elif branches
2. `nested_conditionals` - Nested if statements
3. `with_state` - Conditional based on state field

## Success Metrics

Track these metrics to measure test coverage:

1. **Coverage per refactoring**: Target 5+ test cases per refactoring
2. **Coverage per category**: Ensure all 8 test case categories represented
3. **Error case coverage**: Every refactoring has at least 2 error test cases
4. **Real-world patterns**: 20%+ of tests based on actual code patterns

## Maintenance

### Regular Reviews
- **Quarterly**: Review priority matrix based on user feedback
- **After major features**: Add test cases for new capabilities
- **Bug-driven**: Add regression tests for every bug fix

### Test Case Evolution
When adding new test cases:
1. Start with the simplest possible example
2. Ensure it tests exactly one thing
3. Document why this case matters
4. Link to documentation or real-world examples if applicable
