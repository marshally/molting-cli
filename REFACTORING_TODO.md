# Refactoring TODO

This document outlines a step-by-step plan to refactor common patterns in the molting-cli codebase.

## Status Legend
- [ ] Not started
- [WIP] Work in progress
- [x] Completed

---

## High Priority Refactorings

### 1. Parameter Validation Helper ✅ COMPLETED
**Impact**: Eliminates ~50 lines of duplicate validation code across 12+ commands

**Steps**:
- [x] 1.1. Add `validate_required_params()` method to `BaseCommand` in `molting/commands/base.py`
  ```python
  def validate_required_params(self, *param_names: str) -> None:
      """Validate that required parameters are present.

      Args:
          *param_names: Names of required parameters

      Raises:
          ValueError: If any required parameters are missing
      """
      missing = [p for p in param_names if p not in self.params]
      if missing:
          raise ValueError(
              f"Missing required parameters for {self.name}: {', '.join(missing)}"
          )
  ```

- [x] 1.2. Write unit tests for `validate_required_params()` in a new test file `tests/test_base_command.py`

- [x] 1.3. Migrate all commands to use the new helper (in order):
  - [x] `molting/commands/composing_methods/extract_method.py` (lines 21-31)
  - [x] `molting/commands/moving_features/move_method.py` (lines 17-27)
  - [x] `molting/commands/moving_features/extract_class.py` (lines 16-25)
  - [x] `molting/commands/simplifying_method_calls/rename_method.py` (lines 16-26)
  - [x] `molting/commands/simplifying_method_calls/add_parameter.py` (lines 19-29)
  - [x] `molting/commands/simplifying_method_calls/remove_parameter.py` (lines 19-28)
  - [x] `molting/commands/dealing_with_generalization/extract_superclass.py` (lines 16-25)
  - [x] `molting/commands/dealing_with_generalization/extract_interface.py` (lines 16-27)
  - [x] `molting/commands/moving_features/inline_class.py` (lines 18-27)
  - [x] `molting/commands/dealing_with_generalization/collapse_hierarchy.py` (lines 15-31)

- [x] 1.4. Run all tests to verify no regressions: `make test`

- [x] 1.5. Search for any remaining try/except KeyError patterns: `grep -r "except KeyError" molting/commands/`

---

### 2. Field Extraction from __init__ Utilities ✅ COMPLETED
**Impact**: Eliminates 100+ lines of duplicate field extraction logic across 4 commands

**Steps**:
- [x] 2.1. Add field extraction utilities to `molting/core/ast_utils.py`:
  ```python
  def extract_init_field_assignments(
      init_method: cst.FunctionDef
  ) -> dict[str, cst.BaseExpression]:
      """Extract self.field = value assignments from __init__ method.

      Args:
          init_method: The __init__ method to analyze

      Returns:
          Dictionary mapping field names to their assigned values
      """

  def find_self_field_assignment(
      stmt: cst.SimpleStatementLine
  ) -> tuple[str, cst.BaseExpression] | None:
      """Extract (field_name, value) if statement is self.field = value.

      Args:
          stmt: The statement to check

      Returns:
          Tuple of (field_name, value) or None if not a self.field assignment
      """

  def is_assignment_to_field(
      stmt: cst.BaseStatement,
      field_names: set[str]
  ) -> bool:
      """Check if statement assigns to any of the specified fields.

      Args:
          stmt: The statement to check
          field_names: Set of field names to check for

      Returns:
          True if statement assigns to one of the fields
      """
  ```

- [x] 2.2. Write comprehensive unit tests for new utilities in `tests/test_ast_utils.py`

- [x] 2.3. Migrate ExtractClassCommand to use new utilities:
  - [x] Replace `_is_assignment_to_extracted_field()` at line 184
  - [x] Update `_modify_init()` to use `find_self_field_assignment()`
  - [x] Remove old helper methods

- [x] 2.4. Migrate ExtractSuperclassCommand to use new utilities:
  - [x] Replace `_extract_init_fields()` at line 178
  - [x] Replace `_get_self_field_assignment()` at line 198
  - [x] Update all callers

- [x] 2.5. Migrate InlineClassCommand to use new utilities:
  - [x] Replace `_find_self_assignments()` at line 166
  - [x] Replace `_extract_fields_from_init()` at line 204
  - [x] Update all callers

- [x] 2.6. Migrate MoveMethodCommand to use new utilities:
  - [x] Replace `_extract_field_from_init()` at line 140
  - [x] Replace `_get_self_field_assignment()` at line 158
  - [x] Update all callers

- [x] 2.7. Run tests after each migration: `make test`

- [x] 2.8. Verify no duplicate field extraction logic remains: `grep -r "_field_assignment\|_extract.*field" molting/commands/`

---

### 3. File I/O Boilerplate Wrapper ✅ COMPLETED
**Impact**: Eliminates 5-10 lines per command, improves consistency

**Steps**:
- [x] 3.1. Add helper methods to `BaseCommand` in `molting/commands/base.py`:
  ```python
  def apply_libcst_transform(
      self,
      transformer_class: type[cst.CSTTransformer],
      *args: Any,
      **kwargs: Any
  ) -> None:
      """Apply a libCST transformer to the file.

      Args:
          transformer_class: The transformer class to instantiate
          *args: Positional arguments for transformer
          **kwargs: Keyword arguments for transformer
      """
      source_code = self.file_path.read_text()
      module = cst.parse_module(source_code)
      transformer = transformer_class(*args, **kwargs)
      modified_tree = module.visit(transformer)
      self.file_path.write_text(modified_tree.code)

  def apply_ast_transform(
      self,
      transform_func: Callable[[ast.Module], ast.Module]
  ) -> None:
      """Apply an AST transformation function to the file.

      Args:
          transform_func: Function that takes and returns an ast.Module
      """
      source_code = self.file_path.read_text()
      tree = ast.parse(source_code)
      modified_tree = transform_func(tree)
      ast.fix_missing_locations(modified_tree)
      modified_source = ast.unparse(modified_tree)
      self.file_path.write_text(modified_source)
  ```

- [x] 3.2. Write unit tests for the new methods

- [x] 3.3. Migrate libcst-based commands (in order):
  - [x] `molting/commands/moving_features/move_method.py` (lines 39-45)
  - [x] `molting/commands/moving_features/extract_class.py` (lines 41-47)
  - [x] `molting/commands/dealing_with_generalization/extract_superclass.py` (lines 40-48)
  - [x] `molting/commands/moving_features/inline_class.py` (lines 38-44)
  - [x] `molting/commands/dealing_with_generalization/collapse_hierarchy.py` (lines 46-54)

- [x] 3.4. Migrate ast-based commands:
  - [x] `molting/commands/simplifying_method_calls/add_parameter.py` (lines 43-69)
  - [x] `molting/commands/simplifying_method_calls/remove_parameter.py` (lines 40-76)

- [x] 3.5. Note: ExtractMethodCommand and ExtractInterfaceCommand may need special handling due to metadata/multi-pass logic

- [x] 3.6. Run tests: `make test`

- [x] 3.7. Search for remaining file I/O patterns: `grep -r "read_text\|write_text" molting/commands/`

---

### 4. Self-Reference Collection Visitor ✅ COMPLETED
**Impact**: Eliminates duplicate visitor classes across commands

**Steps**:
- [x] 4.1. Create new file `molting/core/visitors.py` with reusable visitors:
  ```python
  """Reusable CST visitor classes."""

  import libcst as cst

  class SelfFieldCollector(cst.CSTVisitor):
      """Collects all self.field references in a node.

      Example:
          collector = SelfFieldCollector(exclude_fields={"target_field"})
          method.visit(collector)
          fields = collector.collected_fields
      """

      def __init__(self, exclude_fields: set[str] | None = None) -> None:
          """Initialize the collector.

          Args:
              exclude_fields: Set of field names to exclude from collection
          """
          self.collected_fields: list[str] = []
          self.exclude_fields = exclude_fields or set()

      def visit_Attribute(self, node: cst.Attribute) -> None:
          """Visit attribute access to find self.field references."""
          if isinstance(node.value, cst.Name) and node.value.value == "self":
              field_name = node.attr.value
              if field_name not in self.collected_fields and field_name not in self.exclude_fields:
                  self.collected_fields.append(field_name)
  ```

- [x] 4.2. Write unit tests in `tests/test_visitors.py`

- [x] 4.3. Migrate MoveMethodCommand:
  - [x] Replace `SelfReferenceCollector` class (lines 222-239)
  - [x] Update `_collect_self_references()` to use new visitor
  - [x] Remove old class

- [x] 4.4. Check other commands for similar visitor patterns and migrate

- [x] 4.5. Run tests: `make test`

---

## Medium Priority Refactorings

### 5. Class/Method Finding Utilities
**Impact**: Consolidates search logic, makes code more readable

**Steps**:
- [ ] 5.1. Add utilities to `molting/core/ast_utils.py`:
  ```python
  def find_class_in_module(
      module: cst.Module,
      class_name: str
  ) -> cst.ClassDef | None:
      """Find a class definition by name in a module."""

  def find_method_in_class(
      class_def: cst.ClassDef,
      method_name: str
  ) -> cst.FunctionDef | None:
      """Find a method in a class definition."""

  def extract_all_methods(
      class_def: cst.ClassDef,
      exclude_init: bool = False
  ) -> list[cst.FunctionDef]:
      """Extract all method definitions from a class."""
  ```

- [ ] 5.2. Write unit tests

- [ ] 5.3. Audit all commands for class/method finding patterns:
  - [ ] ExtractSuperclassCommand: `_find_method_in_classes()`
  - [ ] InlineClassCommand: method searching in `visit_Module()`
  - [ ] Other commands with similar patterns

- [ ] 5.4. Migrate to use new utilities

- [ ] 5.5. Run tests: `make test`

---

### 6. Import Management Utilities
**Impact**: Makes import handling consistent across commands

**Steps**:
- [ ] 6.1. Create new file `molting/core/import_utils.py`:
  ```python
  """Utilities for managing imports in CST modules."""

  import libcst as cst

  def has_import(
      module: cst.Module,
      module_name: str,
      import_name: str
  ) -> bool:
      """Check if a specific import exists.

      Args:
          module: The module to check
          module_name: The module being imported from (e.g., "typing")
          import_name: The name being imported (e.g., "Protocol")

      Returns:
          True if the import exists
      """

  def ensure_import(
      module: cst.Module,
      module_name: str,
      names: list[str]
  ) -> cst.Module:
      """Add import if not already present.

      Args:
          module: The module to modify
          module_name: The module to import from
          names: List of names to import

      Returns:
          Modified module with import added
      """
  ```

- [ ] 6.2. Write unit tests in `tests/test_import_utils.py`

- [ ] 6.3. Migrate ExtractInterfaceCommand:
  - [ ] Replace `_protocol_already_imported()` (line 215)
  - [ ] Replace `_add_typing_import()` (line 187)
  - [ ] Remove old methods

- [ ] 6.4. Check other commands for import management logic

- [ ] 6.5. Run tests: `make test`

---

### 7. Comma-Separated List Parsing
**Impact**: Small but consistent improvement

**Steps**:
- [ ] 7.1. Add utility to `molting/core/ast_utils.py`:
  ```python
  def parse_comma_separated_list(value: str) -> list[str]:
      """Parse comma-separated string into list of trimmed values.

      Args:
          value: Comma-separated string

      Returns:
          List of trimmed string values
      """
      return [item.strip() for item in value.split(",")]
  ```

- [ ] 7.2. Write unit tests

- [ ] 7.3. Migrate commands:
  - [ ] `molting/commands/moving_features/extract_class.py` (lines 38-39)
  - [ ] `molting/commands/dealing_with_generalization/extract_superclass.py` (line 37)
  - [ ] `molting/commands/dealing_with_generalization/extract_interface.py` (line 39)

- [ ] 7.4. Run tests: `make test`

- [ ] 7.5. Search for remaining split patterns: `grep -r "split(\",\")" molting/commands/`

---

## Low Priority Refactorings

### 8. Spacing/Blank Line Helpers
**Impact**: Minor code cleanup, improved readability

**Steps**:
- [ ] 8.1. Add utilities to `molting/core/cst_helpers.py`:
  ```python
  """Helper functions for working with libCST nodes."""

  import libcst as cst
  from typing import TypeVar

  T = TypeVar('T', bound=cst.CSTNode)

  def with_leading_blank_line(node: T) -> T:
      """Add a leading blank line before a node.

      Args:
          node: The node to add spacing to

      Returns:
          Node with leading blank line
      """
      return node.with_changes(
          leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
      )

  def create_blank_line() -> cst.EmptyLine:
      """Create a blank line node.

      Returns:
          EmptyLine node
      """
      return cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))
  ```

- [ ] 8.2. Write unit tests

- [ ] 8.3. Migrate commands with blank line creation:
  - [ ] `molting/commands/composing_methods/extract_method.py` (line 302)
  - [ ] `molting/commands/moving_features/move_method.py` (line 120)
  - [ ] `molting/commands/moving_features/extract_class.py` (lines 112-113)
  - [ ] Other commands with similar patterns

- [ ] 8.4. Run tests: `make test`

---

### 9. Method Factory Functions
**Impact**: Minor improvement in method creation consistency

**Steps**:
- [ ] 9.1. Add to `molting/core/cst_helpers.py`:
  ```python
  def create_method(
      name: str,
      body: cst.BaseStatement | list[cst.BaseStatement],
      params: list[cst.Param] | None = None,
      returns: cst.Annotation | None = None,
      include_self: bool = True
  ) -> cst.FunctionDef:
      """Create a method definition.

      Args:
          name: Method name
          body: Method body (single statement or list)
          params: Additional parameters beyond self
          returns: Return type annotation
          include_self: Whether to include self parameter

      Returns:
          FunctionDef node
      """
  ```

- [ ] 9.2. Write unit tests

- [ ] 9.3. Identify and migrate method creation patterns:
  - [ ] `molting/commands/composing_methods/extract_method.py` (lines 284-288)
  - [ ] `molting/commands/moving_features/extract_class.py` (lines 266-270)
  - [ ] Other commands

- [ ] 9.4. Run tests: `make test`

---

### 10. Module-Level Insertion Helpers
**Impact**: Simplifies complex insertion logic

**Steps**:
- [ ] 10.1. Add to `molting/core/cst_helpers.py`:
  ```python
  def insert_class_before_target(
      module: cst.Module,
      new_class: cst.ClassDef,
      before_class: str,
      spacing: int = 2
  ) -> cst.Module:
      """Insert a new class definition before a target class.

      Args:
          module: The module to modify
          new_class: The class to insert
          before_class: Name of the class to insert before
          spacing: Number of blank lines before new class

      Returns:
          Modified module
      """

  def insert_class_after_imports(
      module: cst.Module,
      new_class: cst.ClassDef,
      spacing: int = 2
  ) -> cst.Module:
      """Insert a class after import statements.

      Args:
          module: The module to modify
          new_class: The class to insert
          spacing: Number of blank lines before class

      Returns:
          Modified module
      """
  ```

- [ ] 10.2. Write unit tests

- [ ] 10.3. Migrate commands with module insertion:
  - [ ] `molting/commands/dealing_with_generalization/extract_superclass.py` (lines 81-105)
  - [ ] `molting/commands/dealing_with_generalization/extract_interface.py` (lines 240-272)

- [ ] 10.4. Run tests: `make test`

---

## Post-Refactoring Cleanup

### Final Verification Steps
- [ ] Run full test suite: `make test`
- [ ] Run linters: `make lint`
- [ ] Run type checker: `make typecheck`
- [ ] Run all checks: `make all`

### Documentation Updates
- [ ] Update ARCHITECTURE_NOTES.md with new utilities
- [ ] Add docstrings to all new utilities
- [ ] Update README.md if any changes affect usage

### Code Quality Checks
- [ ] Search for any remaining duplicate patterns:
  ```bash
  # Check for duplicate try/except KeyError
  grep -r "except KeyError" molting/commands/

  # Check for duplicate field extraction
  grep -r "_field_assignment\|_extract.*field" molting/commands/

  # Check for duplicate file I/O
  grep -r "read_text.*parse.*write_text" molting/commands/

  # Check for duplicate self.field collection
  grep -r "class.*Collector.*CSTVisitor" molting/commands/

  # Check for duplicate split patterns
  grep -r 'split.*","' molting/commands/
  ```

- [ ] Verify all old helper methods have been removed
- [ ] Ensure no dead code remains
- [ ] Check that all imports are used

---

## Notes

### Testing Strategy
- Write tests for new utilities BEFORE migrating commands
- Run tests after EACH command migration, not at the end
- If a test fails, fix it before moving to the next migration

### Migration Order
- Always migrate high-priority items first
- Within each priority level, migrate in the order listed
- Complete all steps for one refactoring before starting the next

### Rollback Plan
- Each migration should be a separate commit
- Commit message format: "Refactor: Migrate [CommandName] to use [utility]"
- If something breaks, can easily revert individual migrations

### Performance Considerations
- New utilities should not be slower than original code
- Consider caching if utilities are called repeatedly
- Profile before/after for complex transformations
