"""Pytest configuration and shared fixtures for molting-cli tests."""

import ast
import shutil
from pathlib import Path
from typing import Optional

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
        - Fixture directory contains: input.py and expected.py
        - Example: test_simple() -> fixtures/composing_methods/extract_method/simple/
    """

    fixture_category: Optional[str] = None  # Must be set in subclass
    test_file: Optional[Path] = None
    expected_file: Optional[Path] = None
    _should_defer_assertion: bool = False

    @pytest.fixture(autouse=True)
    def _setup_fixture(self, tmp_path, request):
        """Automatically set up fixture files before each test.

        Creates:
            self.tmp_path: Temporary directory for this test
            self.test_file: Path to input.py (copied to tmp_path)
            self.expected_file: Path to expected.py (in fixtures)
            self._should_defer_assertion: Flag to defer assertion until end
        """
        self.tmp_path = tmp_path
        self._should_defer_assertion = False

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
            input_file = fixture_dir / "input.py"
            expected_file = fixture_dir / "expected.py"

            if not input_file.exists():
                raise FileNotFoundError(f"Missing input.py in fixture directory: {fixture_dir}")
            if not expected_file.exists():
                raise FileNotFoundError(f"Missing expected.py in fixture directory: {fixture_dir}")

            # Copy input.py to temporary directory
            self.test_file = tmp_path / "input.py"
            self.expected_file = expected_file

            shutil.copy(input_file, self.test_file)
        else:
            # Allow tests without fixtures (for unit tests, etc.)
            self.test_file = None
            self.expected_file = None

        yield

        # Assert at the end of test if deferred
        if self._should_defer_assertion and self.test_file and self.expected_file:
            self.assert_matches_expected()

        # Cleanup handled automatically by tmp_path fixture

    def refactor(self, refactoring_name: str, **params) -> None:
        """Run refactoring and assert result matches expected output.

        For tests that call refactor() multiple times, assertion is deferred until
        the end of the test method.

        Args:
            refactoring_name: Name of refactoring (e.g., "extract-method")
            **params: Parameters to pass to the refactoring

        Raises:
            AssertionError: If refactored output doesn't match expected
        """
        if self.test_file is None:
            raise RuntimeError("No fixture loaded. Ensure fixture directory exists for this test.")

        # Import here to avoid circular dependencies during test collection
        from molting.cli import refactor_file

        # Run the refactoring
        refactor_file(refactoring_name, str(self.test_file), **params)

        # Defer assertion - it will be checked at the end of the test
        # This allows tests to chain multiple refactorings before assertion
        self._should_defer_assertion = True

    def assert_matches_expected(self, normalize: bool = True) -> None:
        """Assert that test_file matches expected_file.

        Args:
            normalize: If True, use AST comparison (ignores formatting).
                      If False, use exact string comparison.
        """
        if self.test_file is None or self.expected_file is None:
            raise RuntimeError("No fixture loaded")

        actual = self.test_file.read_text()
        expected = self.expected_file.read_text()

        if normalize:
            # AST-based comparison (ignores whitespace/formatting)
            self._assert_ast_equal(actual, expected)
        else:
            # Exact string comparison
            assert actual == expected, self._format_diff(actual, expected)

    def _assert_ast_equal(self, actual, expected):
        """Compare two code strings by AST structure.

        This ignores formatting differences but catches semantic changes.
        """
        try:
            actual_ast = ast.parse(actual)
            expected_ast = ast.parse(expected)
        except SyntaxError as e:
            pytest.fail(
                f"Syntax error in {'actual' if 'actual' in str(e) else 'expected'} code: {e}"
            )

        actual_dump = ast.dump(actual_ast)
        expected_dump = ast.dump(expected_ast)

        if actual_dump != expected_dump:
            # ASTs don't match - show a readable diff
            pytest.fail(
                f"AST mismatch:\n\n"
                f"Expected code:\n{expected}\n\n"
                f"Actual code:\n{actual}\n\n"
                f"{self._format_diff(actual, expected)}"
            )

    def _format_diff(self, actual, expected):
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


def normalize_code(code):
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
