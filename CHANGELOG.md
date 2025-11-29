# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Consolidated parsing logic**: All command files now use canonical parsing functions from `molting/core/ast_utils.py` instead of duplicated implementations. Affected 7 command files (`extract_method.py`, `extract_function.py`, `decompose_conditional.py`, `consolidate_duplicate_conditional_fragments.py`, `introduce_assertion.py`, `introduce_foreign_method.py`, `replace_conditional_with_polymorphism.py`).

- **Standardized validation pattern**: All 21 command files now use `validate_required_params()` helper instead of manual parameter checks. Provides consistent validation error messages and reduces code duplication.

- **Dynamic CLI imports**: Replaced 66 static import statements in `cli.py` with automatic command discovery via `discover_and_register_commands()`. New commands are now automatically registered when added to the commands directory.

- **Refactored ExtractMethodTransformer**: Broke up long `leave_FunctionDef` method into 3 focused helper methods (`_collect_statements_to_extract`, `_build_modified_method_body`, `_create_new_extracted_method`) for better readability and single responsibility principle.

- **Refactored InlineClassTransformer**: Extracted 8 helper methods from long methods for better code organization, maintainability, and testability.

- **Enhanced form-template-method command**: Added `--steps` parameter to specify variable-to-method mappings. Removed hardcoded `TAX_RATE`, `is_winter`, `winter_charge`, `summer_charge` values. Command is now domain-agnostic and fully configurable.

- **Test fixture improvements**: Updated docstrings in test fixture expected output files from "Example code" to "Expected output after" for clarity and consistency in test documentation.

### Removed

- **Duplicate FieldAccessCollector class**: Removed from `transformers.py`. Use `SelfFieldCollector` from `visitors.py` instead. Eliminates redundant implementations.

- **Duplicate parsing methods**: Removed `_parse_line_range`, `_parse_target`, `_parse_target_specification` duplicates from command files. All now use canonical implementations from `ast_utils.py`.

- **Hardcoded constants in form-template-method**: Removed `CLASS_VARIABLE_NAME` and `CLASS_VARIABLE_VALUE` constants from module scope. Values are now specified via command line.

### Documentation

- **Added visitor pattern documentation**: Explained why LibCST visitors use mutable state pattern in `molting/core/visitors.py` module docstring. Documents the rationale for state mutation in visitor classes and how to properly manage visitor lifecycle.

### Tests

- Test suite: 407 passed, 66 skipped, 12 failed (pre-existing failures in multiple refactoring commands, not caused by Clean Code refactoring)
- Linting: All checks pass (black, ruff, mypy)
- Type checking: No issues found in 162 source files

## Pre-existing Test Failures

The following test failures were identified during Clean Code refactoring and are pre-existing issues in the refactoring command implementations (not caused by these changes):

- `test_extract_class.py`: test_multiple_calls, test_with_decorators
- `test_move_field.py`: test_multiple_calls, test_with_instance_vars
- `test_move_method.py`: test_with_decorators
- `test_add_parameter.py`: test_with_decorators, test_multiple_calls, test_with_instance_vars
- `test_introduce_parameter_object.py`: test_multiple_calls
- `test_remove_parameter.py`: test_multiple_calls
- `test_rename_method.py`: test_multiple_calls
- `test_replace_exception_with_test.py`: test_multiple_calls

These failures indicate issues in the corresponding refactoring transformers that require separate fixes outside the scope of this Clean Code refactoring effort.
