"""
Tests for BaseCommand class.

This module tests the core functionality of the BaseCommand class,
including parameter validation and other base functionality.
"""

import ast
from pathlib import Path

import libcst as cst
import pytest

from molting.commands.base import BaseCommand


class ConcreteCommand(BaseCommand):
    """Concrete implementation of BaseCommand for testing."""

    name = "test-command"

    def execute(self) -> None:
        """Execute the refactoring (no-op for testing)."""
        pass

    def validate(self) -> None:
        """Validate parameters (no-op for testing)."""
        pass


class TestValidateRequiredParams:
    """Tests for BaseCommand.validate_required_params() method."""

    def test_all_required_params_present(self) -> None:
        """Should not raise when all required params are present."""
        cmd = ConcreteCommand(Path("test.py"), foo="value1", bar="value2", baz="value3")

        # Should not raise
        cmd.validate_required_params("foo", "bar")
        cmd.validate_required_params("foo")
        cmd.validate_required_params("bar", "baz")

    def test_one_missing_param(self) -> None:
        """Should raise ValueError with correct message when one param is missing."""
        cmd = ConcreteCommand(Path("test.py"), foo="value1", bar="value2")

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("foo", "missing_param")

        error_message = str(exc_info.value)
        assert "Missing required parameters for test-command" in error_message
        assert "missing_param" in error_message
        assert "foo" not in error_message  # foo is present, should not be in error

    def test_multiple_missing_params(self) -> None:
        """Should raise ValueError listing all missing params."""
        cmd = ConcreteCommand(Path("test.py"), foo="value1")

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("foo", "missing1", "missing2", "missing3")

        error_message = str(exc_info.value)
        assert "Missing required parameters for test-command" in error_message
        assert "missing1" in error_message
        assert "missing2" in error_message
        assert "missing3" in error_message
        assert "foo" not in error_message  # foo is present, should not be in error

    def test_no_params_required(self) -> None:
        """Should not raise when no params are required."""
        cmd = ConcreteCommand(Path("test.py"), foo="value1")

        # Should not raise
        cmd.validate_required_params()

    def test_no_params_provided_but_some_required(self) -> None:
        """Should raise when params are required but none provided."""
        cmd = ConcreteCommand(Path("test.py"))

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("required_param")

        error_message = str(exc_info.value)
        assert "Missing required parameters for test-command" in error_message
        assert "required_param" in error_message

    def test_error_message_format(self) -> None:
        """Should format error message correctly with comma-separated list."""
        cmd = ConcreteCommand(Path("test.py"))

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("param1", "param2")

        error_message = str(exc_info.value)
        # Check exact format: "Missing required parameters for {name}: {param1}, {param2}"
        assert error_message == "Missing required parameters for test-command: param1, param2"

    def test_includes_command_name_in_error(self) -> None:
        """Should include the command name in the error message."""

        class DifferentCommand(BaseCommand):
            name = "different-command"

            def execute(self) -> None:
                pass

            def validate(self) -> None:
                pass

        cmd = DifferentCommand(Path("test.py"))

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("missing")

        error_message = str(exc_info.value)
        assert "different-command" in error_message
        assert "test-command" not in error_message


class SimpleTransformer(cst.CSTTransformer):
    """A simple transformer that adds a comment to the module."""

    def __init__(self, comment: str) -> None:
        """Initialize the transformer with a comment."""
        self.comment = comment

    def visit_Module(self, node: cst.Module) -> None:  # noqa: N802
        """Visit the module (no-op, just for testing)."""
        pass


class AddCommentTransformer(cst.CSTTransformer):
    """Transformer that adds a comment to class definitions."""

    def __init__(self, comment_text: str, prefix: str = "") -> None:
        """Initialize transformer.

        Args:
            comment_text: The comment text to add
            prefix: Optional prefix for the comment
        """
        self.comment_text = comment_text
        self.prefix = prefix

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Add a comment above class definitions."""
        comment = f"# {self.prefix}{self.comment_text}" if self.prefix else f"# {self.comment_text}"
        new_leading = cst.EmptyLine(
            indent=False,
            whitespace=cst.SimpleWhitespace(""),
            comment=cst.Comment(value=comment),
        )
        # Convert to list, add new line, convert back to tuple
        leading_lines = list(updated_node.leading_lines)
        leading_lines.insert(0, new_leading)
        return updated_node.with_changes(leading_lines=leading_lines)


class TestApplyLibcstTransform:
    """Tests for BaseCommand.apply_libcst_transform() method."""

    def test_transformer_applied_successfully(self, tmp_path: Path) -> None:
        """Should apply transformer and write modified code back to file."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("class MyClass:\n    pass\n")

        cmd = ConcreteCommand(test_file)

        # Apply transformer
        cmd.apply_libcst_transform(AddCommentTransformer, "This is a test")

        # Verify file was modified
        result = test_file.read_text()
        assert "# This is a test" in result
        assert "class MyClass:" in result

    def test_transformer_receives_positional_args(self, tmp_path: Path) -> None:
        """Should pass positional args to transformer constructor."""
        test_file = tmp_path / "test.py"
        test_file.write_text("class MyClass:\n    pass\n")

        cmd = ConcreteCommand(test_file)

        # Apply transformer with positional arg
        cmd.apply_libcst_transform(AddCommentTransformer, "Positional arg test")

        result = test_file.read_text()
        assert "# Positional arg test" in result

    def test_transformer_receives_keyword_args(self, tmp_path: Path) -> None:
        """Should pass keyword args to transformer constructor."""
        test_file = tmp_path / "test.py"
        test_file.write_text("class MyClass:\n    pass\n")

        cmd = ConcreteCommand(test_file)

        # Apply transformer with keyword args
        cmd.apply_libcst_transform(
            AddCommentTransformer, comment_text="Keyword test", prefix="PREFIX: "
        )

        result = test_file.read_text()
        assert "# PREFIX: Keyword test" in result

    def test_transformer_receives_mixed_args(self, tmp_path: Path) -> None:
        """Should pass both positional and keyword args to transformer."""
        test_file = tmp_path / "test.py"
        test_file.write_text("class MyClass:\n    pass\n")

        cmd = ConcreteCommand(test_file)

        # Apply transformer with both positional and keyword args
        cmd.apply_libcst_transform(AddCommentTransformer, "Mixed test", prefix="MIX: ")

        result = test_file.read_text()
        assert "# MIX: Mixed test" in result

    def test_file_actually_modified(self, tmp_path: Path) -> None:
        """Should actually modify the file on disk."""
        test_file = tmp_path / "test.py"
        original_content = "class MyClass:\n    pass\n"
        test_file.write_text(original_content)

        cmd = ConcreteCommand(test_file)
        cmd.apply_libcst_transform(AddCommentTransformer, "File modification test")

        # Read file directly to verify it was modified
        modified_content = test_file.read_text()
        assert modified_content != original_content
        assert "# File modification test" in modified_content

    def test_preserves_valid_python_syntax(self, tmp_path: Path) -> None:
        """Should preserve valid Python syntax after transformation."""
        test_file = tmp_path / "test.py"
        test_file.write_text("class MyClass:\n    def method(self):\n        return 42\n")

        cmd = ConcreteCommand(test_file)
        cmd.apply_libcst_transform(AddCommentTransformer, "Syntax test")

        # Verify the result is valid Python
        result = test_file.read_text()
        # Should not raise SyntaxError
        compile(result, str(test_file), "exec")


class TestApplyAstTransform:
    """Tests for BaseCommand.apply_ast_transform() method."""

    def test_transform_applied_successfully(self, tmp_path: Path) -> None:
        """Should apply AST transform and write modified code back to file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\ny = 2\n")

        def add_variable(tree: ast.Module) -> ast.Module:
            """Add a new variable assignment to the module."""
            new_assign = ast.Assign(
                targets=[ast.Name(id="z", ctx=ast.Store())],
                value=ast.Constant(value=3),
            )
            tree.body.append(new_assign)
            return tree

        cmd = ConcreteCommand(test_file)
        cmd.apply_ast_transform(add_variable)

        result = test_file.read_text()
        assert "z = 3" in result

    def test_handles_fix_missing_locations(self, tmp_path: Path) -> None:
        """Should call ast.fix_missing_locations on modified tree."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        def create_new_node(tree: ast.Module) -> ast.Module:
            """Create a new node without location info."""
            # Create node without location info
            new_assign = ast.Assign(
                targets=[ast.Name(id="new_var", ctx=ast.Store())],
                value=ast.Constant(value=42),
            )
            tree.body.append(new_assign)
            return tree

        cmd = ConcreteCommand(test_file)
        # Should not raise AttributeError about missing location
        cmd.apply_ast_transform(create_new_node)

        result = test_file.read_text()
        assert "new_var = 42" in result

    def test_handles_ast_unparse(self, tmp_path: Path) -> None:
        """Should use ast.unparse to generate code from modified tree."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def func():\n    pass\n")

        def rename_function(tree: ast.Module) -> ast.Module:
            """Rename the function."""
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "func":
                    node.name = "renamed_func"
            return tree

        cmd = ConcreteCommand(test_file)
        cmd.apply_ast_transform(rename_function)

        result = test_file.read_text()
        assert "def renamed_func():" in result
        assert "def func():" not in result

    def test_file_actually_modified(self, tmp_path: Path) -> None:
        """Should actually modify the file on disk."""
        test_file = tmp_path / "test.py"
        original_content = "value = 10\n"
        test_file.write_text(original_content)

        def modify_value(tree: ast.Module) -> ast.Module:
            """Change the value."""
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if isinstance(node.value, ast.Constant):
                        node.value = ast.Constant(value=99)
            return tree

        cmd = ConcreteCommand(test_file)
        cmd.apply_ast_transform(modify_value)

        # Read file directly to verify it was modified
        modified_content = test_file.read_text()
        assert modified_content != original_content
        assert "value = 99" in modified_content

    def test_preserves_valid_python_syntax(self, tmp_path: Path) -> None:
        """Should preserve valid Python syntax after transformation."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "def calculate(a, b):\n    return a + b\n\nresult = calculate(5, 10)\n"
        )

        def add_docstring(tree: ast.Module) -> ast.Module:
            """Add a docstring to the function."""
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "calculate":
                    docstring = ast.Expr(value=ast.Constant(value="A calculator function"))
                    node.body.insert(0, docstring)
            return tree

        cmd = ConcreteCommand(test_file)
        cmd.apply_ast_transform(add_docstring)

        # Verify the result is valid Python
        result = test_file.read_text()
        # Should not raise SyntaxError
        compile(result, str(test_file), "exec")

    def test_transform_with_complex_ast_modifications(self, tmp_path: Path) -> None:
        """Should handle complex AST modifications correctly."""
        test_file = tmp_path / "test.py"
        test_file.write_text("class MyClass:\n    def method(self, x):\n        return x * 2\n")

        def add_parameter(tree: ast.Module) -> ast.Module:
            """Add a parameter to the method."""
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "method":
                    new_arg = ast.arg(arg="y", annotation=None)
                    node.args.args.append(new_arg)
                    # Modify return to use new parameter
                    node.body[0] = ast.Return(
                        value=ast.BinOp(
                            left=ast.BinOp(
                                left=ast.Name(id="x", ctx=ast.Load()),
                                op=ast.Mult(),
                                right=ast.Constant(value=2),
                            ),
                            op=ast.Add(),
                            right=ast.Name(id="y", ctx=ast.Load()),
                        )
                    )
            return tree

        cmd = ConcreteCommand(test_file)
        cmd.apply_ast_transform(add_parameter)

        result = test_file.read_text()
        # Verify the modified code is syntactically correct
        compile(result, str(test_file), "exec")
        # Verify the modification was applied
        assert "def method(self, x, y):" in result
