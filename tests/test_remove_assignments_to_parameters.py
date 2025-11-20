"""Tests for Remove Assignments to Parameters refactoring.

This module tests the Remove Assignments to Parameters refactoring which
replaces parameter reassignments with local variables using libcst.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestRemoveAssignmentsToParametersSimple(RefactoringTestBase):
    """Tests for removing simple parameter assignments."""
    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_simple(self):
        """Remove assignments to a single parameter."""
        self.refactor(
            "remove-assignments-to-parameters",
            target="discount"
        )


class TestRemoveAssignmentsToParametersClassMethod(RefactoringTestBase):
    """Tests for class method parameter assignments."""
    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_class_method(self):
        """Remove assignments to a class method parameter."""
        self.refactor(
            "remove-assignments-to-parameters",
            target="calculate"
        )


class TestRemoveAssignmentsToParametersParseTargetFunction:
    """Test parsing of function target specification."""

    def test_target_parsing(self):
        """Test that function target is correctly parsed."""
        from pathlib import Path
        import tempfile
        from molting.refactorings.composing_methods.remove_assignments_to_parameters import RemoveAssignmentsToParameters

        test_code = """def calculate(value, quantity):
    if value > 50:
        value -= 2
    return value
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            f.flush()

            try:
                refactor = RemoveAssignmentsToParameters(f.name, "calculate")
                result = refactor.apply(test_code)

                # Check that transformation occurred
                assert "result = value" in result
                assert "result -= 2" in result
                assert "return result" in result
            finally:
                import os
                os.unlink(f.name)


class TestRemoveAssignmentsToParametersDetectAssignments:
    """Test detection of parameter assignments."""

    def test_detect_parameter_assignment(self):
        """Test that parameter assignments are detected."""
        from molting.refactorings.composing_methods.remove_assignments_to_parameters import RemoveAssignmentsToParameters
        import tempfile

        test_code = """def process(data):
    data = data.strip()
    return data
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            f.flush()

            try:
                refactor = RemoveAssignmentsToParameters(f.name, "process")
                result = refactor.apply(test_code)

                # Check that transformation occurred
                assert "result = data" in result
                assert "result = result.strip()" in result
                assert "return result" in result
            finally:
                import os
                os.unlink(f.name)


class TestRemoveAssignmentsToParametersInvalidTarget:
    """Test handling of invalid targets."""

    def test_nonexistent_function(self):
        """Test handling when target function doesn't exist."""
        from molting.refactorings.composing_methods.remove_assignments_to_parameters import RemoveAssignmentsToParameters
        import tempfile

        test_code = """def existing_func(value):
    return value
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            f.flush()

            try:
                refactor = RemoveAssignmentsToParameters(f.name, "nonexistent")
                result = refactor.apply(test_code)

                # Code should remain unchanged since function doesn't exist
                assert result == test_code
            finally:
                import os
                os.unlink(f.name)
