"""Pytest configuration and shared fixtures for molting-cli tests."""

import ast
import shutil
from pathlib import Path
from typing import Any, Optional

import pytest


class RefactoringTestBase:
    """Base class for refactoring tests with automatic fixture management.

    Usage:
        class TestExtractMethod(RefactoringTestBase):
            fixture_category = "composing_methods/extract_method"

            def test_simple(self):
                self.refactor("extract-method",
                    target="Order::print_owing#L3",
                    name="print_banner"
                )

    Convention:
        - Test method name (minus 'test_' prefix) maps to fixture directory name
        - Single-file: Fixture directory contains input.py and expected.py
        - Multi-file: Fixture directory contains input/ and expected/ directories
        - Example: test_simple() -> fixtures/composing_methods/extract_method/simple/
    """

    fixture_category: Optional[str] = None  # Must be set in subclass

    @pytest.fixture(autouse=True)
    def _setup_fixture(self, tmp_path: Path, request: pytest.FixtureRequest) -> None:  # type: ignore[misc]
        """Automatically set up fixture files before each test.

        Creates:
            self.tmp_path: Temporary directory for this test
            self.test_file: Path to input.py (copied to tmp_path) - single-file mode
            self.expected_file: Path to expected.py (in fixtures) - single-file mode
            self.test_files: Dict of filename -> Path (copied to tmp_path) - multi-file mode
            self.expected_files: Dict of filename -> Path (in fixtures) - multi-file mode
            self.is_multi_file: True if using multi-file fixtures
        """
        self.tmp_path = tmp_path
        self.is_multi_file = False
        self.test_files: dict[str, Path] = {}
        self.expected_files: dict[str, Path] = {}

        # Derive fixture name from test method name
        # test_simple_case -> simple_case
        test_name = request.function.__name__
        if test_name.startswith("test_"):
            fixture_name = test_name[5:]  # Remove 'test_' prefix
        else:
            fixture_name = test_name

        # Construct fixture directory path
        if self.fixture_category is None:
            raise ValueError(f"{self.__class__.__name__} must set fixture_category class attribute")

        fixture_dir = Path(__file__).parent / "fixtures" / self.fixture_category / fixture_name

        # Only set up if fixture directory exists
        if fixture_dir.exists():
            input_dir = fixture_dir / "input"
            expected_dir = fixture_dir / "expected"
            input_file = fixture_dir / "input.py"
            expected_file = fixture_dir / "expected.py"

            # Check for multi-file fixtures (input/ and expected/ directories)
            if input_dir.exists() and expected_dir.exists():
                self._setup_multi_file_fixture(input_dir, expected_dir)
            elif input_file.exists() and expected_file.exists():
                self._setup_single_file_fixture(input_file, expected_file)
            else:
                raise FileNotFoundError(
                    f"Fixture directory {fixture_dir} must contain either "
                    "(input.py + expected.py) or (input/ + expected/ directories)"
                )
        else:
            # Allow tests without fixtures (for unit tests, etc.)
            self.test_file = None
            self.expected_file = None

        yield

        # Cleanup handled automatically by tmp_path fixture

    def _setup_single_file_fixture(self, input_file: Path, expected_file: Path) -> None:
        """Set up a single-file fixture."""
        self.is_multi_file = False
        self.test_file: Optional[Path] = self.tmp_path / "input.py"
        self.expected_file: Optional[Path] = expected_file
        shutil.copy(input_file, self.test_file)

    def _setup_multi_file_fixture(self, input_dir: Path, expected_dir: Path) -> None:
        """Set up a multi-file fixture.

        Copies all .py files from input/ to tmp_path and records expected/ paths.
        """
        self.is_multi_file = True
        self.test_file = None  # Not used in multi-file mode
        self.expected_file = None  # Not used in multi-file mode

        # Copy all Python files from input/ to tmp_path
        for input_file in input_dir.glob("*.py"):
            dest_file = self.tmp_path / input_file.name
            shutil.copy(input_file, dest_file)
            self.test_files[input_file.name] = dest_file

        # Record expected file paths
        for expected_file in expected_dir.glob("*.py"):
            self.expected_files[expected_file.name] = expected_file

        # Verify all input files have corresponding expected files
        input_names = set(self.test_files.keys())
        expected_names = set(self.expected_files.keys())
        if input_names != expected_names:
            missing_expected = input_names - expected_names
            extra_expected = expected_names - input_names
            msg = f"Fixture file mismatch in multi-file fixture:"
            if missing_expected:
                msg += f"\n  Missing expected files: {missing_expected}"
            if extra_expected:
                msg += f"\n  Extra expected files: {extra_expected}"
            raise FileNotFoundError(msg)

    def refactor(self, refactoring_name: str, **params: Any) -> None:
        """Run refactoring and assert result matches expected output.

        Args:
            refactoring_name: Name of refactoring (e.g., "extract-method")
            **params: Parameters to pass to the refactoring
                For multi-file fixtures, use `target_file` to specify which file
                contains the target (e.g., target_file="order.py")

        Raises:
            AssertionError: If refactored output doesn't match expected
        """
        # Import here to avoid circular dependencies during test collection
        from molting.cli import refactor_file

        if self.is_multi_file:
            # Multi-file mode: get target file from params or use first file
            target_file_name = params.pop("target_file", None)
            if target_file_name is None:
                raise ValueError(
                    "Multi-file fixtures require 'target_file' parameter "
                    "to specify which file contains the refactoring target"
                )
            if target_file_name not in self.test_files:
                raise ValueError(
                    f"target_file '{target_file_name}' not found in fixture. "
                    f"Available files: {list(self.test_files.keys())}"
                )
            target_file = self.test_files[target_file_name]

            # Run the refactoring on the target file
            # Note: The refactoring command is responsible for updating other files
            # via CallSiteUpdater or similar mechanism
            refactor_file(refactoring_name, target_file, **params)
        else:
            # Single-file mode (original behavior)
            if self.test_file is None:
                raise RuntimeError("No fixture loaded. Ensure fixture directory exists for this test.")
            refactor_file(refactoring_name, self.test_file, **params)

        # Validate result
        self.assert_matches_expected()

    def refactor_directory(self, refactoring_name: str, **params: Any) -> None:
        """Run a directory-wide refactoring and assert results match expected.

        Use this for refactorings that operate on a directory rather than a single file.

        Args:
            refactoring_name: Name of refactoring (e.g., "rename-method")
            **params: Parameters to pass to the refactoring

        Raises:
            AssertionError: If refactored output doesn't match expected
        """
        if not self.is_multi_file:
            raise RuntimeError(
                "refactor_directory() requires multi-file fixtures "
                "(input/ and expected/ directories)"
            )

        # Import here to avoid circular dependencies during test collection
        from molting.cli import refactor_directory

        # Run the refactoring on the directory
        refactor_directory(refactoring_name, self.tmp_path, **params)

        # Validate result
        self.assert_matches_expected()

    def assert_matches_expected(self, normalize: bool = True) -> None:
        """Assert that test file(s) match expected file(s).

        Args:
            normalize: If True, use AST comparison (ignores formatting).
                      If False, use exact string comparison.
        """
        if self.is_multi_file:
            self._assert_multi_file_matches_expected(normalize)
        else:
            self._assert_single_file_matches_expected(normalize)

    def _assert_single_file_matches_expected(self, normalize: bool) -> None:
        """Assert single test file matches expected."""
        if self.test_file is None or self.expected_file is None:
            raise RuntimeError("No fixture loaded")

        actual = self.test_file.read_text()
        expected = self.expected_file.read_text()

        if normalize:
            self._assert_ast_equal(actual, expected)
        else:
            assert actual == expected, self._format_diff(actual, expected)

    def _assert_multi_file_matches_expected(self, normalize: bool) -> None:
        """Assert all test files match their expected counterparts."""
        failures = []

        for filename, test_file in self.test_files.items():
            expected_file = self.expected_files.get(filename)
            if expected_file is None:
                failures.append(f"{filename}: No expected file found")
                continue

            actual = test_file.read_text()
            expected = expected_file.read_text()

            try:
                if normalize:
                    self._assert_ast_equal(actual, expected, filename=filename)
                else:
                    if actual != expected:
                        failures.append(
                            f"{filename}:\n{self._format_diff(actual, expected)}"
                        )
            except AssertionError as e:
                failures.append(f"{filename}: {e}")

        if failures:
            pytest.fail(
                f"Multi-file assertion failed:\n\n" + "\n\n".join(failures)
            )

    def _assert_ast_equal(
        self, actual: str, expected: str, filename: Optional[str] = None
    ) -> None:
        """Compare two code strings by AST structure.

        This ignores formatting differences but catches semantic changes.

        Args:
            actual: The actual code string
            expected: The expected code string
            filename: Optional filename for error messages (multi-file mode)
        """
        file_prefix = f"[{filename}] " if filename else ""

        try:
            actual_ast = ast.parse(actual)
            expected_ast = ast.parse(expected)
        except SyntaxError as e:
            pytest.fail(
                f"{file_prefix}Syntax error in "
                f"{'actual' if 'actual' in str(e) else 'expected'} code: {e}"
            )

        actual_dump = ast.dump(actual_ast)
        expected_dump = ast.dump(expected_ast)

        if actual_dump != expected_dump:
            # ASTs don't match - show a readable diff
            pytest.fail(
                f"{file_prefix}AST mismatch:\n\n"
                f"Expected code:\n{expected}\n\n"
                f"Actual code:\n{actual}\n\n"
                f"{self._format_diff(actual, expected)}"
            )

    def _format_diff(self, actual: str, expected: str) -> str:
        """Format a readable diff between actual and expected."""
        import difflib

        diff = difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="expected.py",
            tofile="actual.py",
            lineterm="",
        )

        return "".join(diff)


def normalize_code(code: str) -> str:
    """Normalize Python code for comparison.

    Args:
        code: Python source code string

    Returns:
        Normalized code string (formatted consistently)
    """
    try:
        # Try to use black for formatting if available
        import black

        return black.format_str(code, mode=black.Mode())
    except ImportError:
        # Fall back to just parsing and unparsing with ast
        return ast.unparse(ast.parse(code))
