"""Tests for code generation utility functions.

This module tests the CST construction utilities used for generating
common Python code patterns.
"""

import libcst as cst

from molting.core.code_generation_utils import (
    create_field_assignment,
    create_init_method,
    create_parameter,
    create_super_init_call,
)


class TestCreateSuperInitCall:
    """Tests for create_super_init_call() function."""

    def test_no_arguments(self) -> None:
        """Should create super().__init__() with no arguments."""
        stmt = create_super_init_call()
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "super().__init__()"

    def test_with_single_argument(self) -> None:
        """Should create super().__init__(arg) with one argument."""
        args = [cst.Arg(value=cst.Name("name"))]
        stmt = create_super_init_call(args)
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "super().__init__(name)"

    def test_with_multiple_arguments(self) -> None:
        """Should create super().__init__(arg1, arg2) with multiple arguments."""
        args = [
            cst.Arg(value=cst.Name("name")),
            cst.Arg(value=cst.Name("age")),
        ]
        stmt = create_super_init_call(args)
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "super().__init__(name, age)"

    def test_with_keyword_argument(self) -> None:
        """Should create super().__init__(name=value) with keyword argument."""
        args = [cst.Arg(keyword=cst.Name("name"), value=cst.Name("value"))]
        stmt = create_super_init_call(args)
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "super().__init__(name = value)"

    def test_returns_simple_statement_line(self) -> None:
        """Should return a SimpleStatementLine instance."""
        stmt = create_super_init_call()
        assert isinstance(stmt, cst.SimpleStatementLine)


class TestCreateFieldAssignment:
    """Tests for create_field_assignment() function."""

    def test_simple_field_assignment(self) -> None:
        """Should create self.field = field assignment."""
        stmt = create_field_assignment("name")
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "self.name = name"

    def test_field_assignment_with_integer_value(self) -> None:
        """Should create self.field = 0 with integer value."""
        stmt = create_field_assignment("count", cst.Integer("0"))
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "self.count = 0"

    def test_field_assignment_with_string_value(self) -> None:
        """Should create self.field = 'value' with string value."""
        stmt = create_field_assignment("name", cst.SimpleString('"default"'))
        code = cst.Module(body=[stmt]).code
        assert code.strip() == 'self.name = "default"'

    def test_field_assignment_with_list_value(self) -> None:
        """Should create self.field = [] with list value."""
        stmt = create_field_assignment("items", cst.List([]))
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "self.items = []"

    def test_field_assignment_with_call_value(self) -> None:
        """Should create self.field = func() with call value."""
        stmt = create_field_assignment("result", cst.Call(func=cst.Name("compute")))
        code = cst.Module(body=[stmt]).code
        assert code.strip() == "self.result = compute()"

    def test_returns_simple_statement_line(self) -> None:
        """Should return a SimpleStatementLine instance."""
        stmt = create_field_assignment("name")
        assert isinstance(stmt, cst.SimpleStatementLine)


class TestCreateInitMethod:
    """Tests for create_init_method() function."""

    def test_simple_init_with_no_params(self) -> None:
        """Should create __init__(self) with no parameters."""
        method = create_init_method([])
        code = cst.Module(body=[method]).code
        # When no params and no field assignments, body should be empty or pass
        # LibCST requires at least one statement, so empty body becomes pass
        assert "__init__(self)" in code

    def test_simple_init_with_one_param(self) -> None:
        """Should create __init__(self, name) with one parameter."""
        method = create_init_method(["name"])
        code = cst.Module(body=[method]).code
        assert "def __init__(self, name):" in code
        assert "self.name = name" in code

    def test_init_with_multiple_params(self) -> None:
        """Should create __init__ with multiple parameters and assignments."""
        method = create_init_method(["name", "age"])
        code = cst.Module(body=[method]).code
        assert "def __init__(self, name, age):" in code
        assert "self.name = name" in code
        assert "self.age = age" in code

    def test_init_with_custom_field_assignments(self) -> None:
        """Should create __init__ with custom field values."""
        field_assignments = {
            "count": cst.Integer("0"),
            "name": cst.SimpleString('"default"'),
        }
        method = create_init_method(["data"], field_assignments=field_assignments)
        code = cst.Module(body=[method]).code
        assert "def __init__(self, data):" in code
        assert "self.count = 0" in code
        assert 'self.name = "default"' in code
        # Custom field assignments should NOT include self.data = data
        assert "self.data = data" not in code

    def test_init_with_super_call_no_args(self) -> None:
        """Should create __init__ with super().__init__() call."""
        method = create_init_method(["name"], super_call_args=[])
        code = cst.Module(body=[method]).code
        assert "def __init__(self, name):" in code
        assert "super().__init__()" in code
        assert "self.name = name" in code
        # super() call should come before field assignments
        super_pos = code.index("super().__init__()")
        name_pos = code.index("self.name = name")
        assert super_pos < name_pos

    def test_init_with_super_call_with_args(self) -> None:
        """Should create __init__ with super().__init__(args) call."""
        super_args = [cst.Arg(value=cst.Name("name"))]
        method = create_init_method(["name", "age"], super_call_args=super_args)
        code = cst.Module(body=[method]).code
        assert "def __init__(self, name, age):" in code
        assert "super().__init__(name)" in code
        assert "self.name = name" in code
        assert "self.age = age" in code

    def test_init_with_super_call_and_custom_fields(self) -> None:
        """Should create __init__ with super() call and custom field assignments."""
        super_args = [cst.Arg(value=cst.Name("base_val"))]
        field_assignments: dict[str, cst.BaseExpression] = {"local": cst.Integer("42")}
        method = create_init_method(
            ["base_val"], field_assignments=field_assignments, super_call_args=super_args
        )
        code = cst.Module(body=[method]).code
        assert "def __init__(self, base_val):" in code
        assert "super().__init__(base_val)" in code
        assert "self.local = 42" in code

    def test_returns_function_def(self) -> None:
        """Should return a FunctionDef instance."""
        method = create_init_method(["name"])
        assert isinstance(method, cst.FunctionDef)
        assert method.name.value == "__init__"

    def test_parameter_order_preserved(self) -> None:
        """Should preserve parameter order in function signature."""
        method = create_init_method(["first", "second", "third"])
        code = cst.Module(body=[method]).code
        assert "def __init__(self, first, second, third):" in code


class TestCreateParameter:
    """Tests for create_parameter() function."""

    def test_simple_parameter(self) -> None:
        """Should create simple parameter without annotation or default."""
        param = create_parameter("name")
        # Create a minimal function to test parameter rendering
        func = cst.FunctionDef(
            name=cst.Name("test"),
            params=cst.Parameters(params=[param]),
            body=cst.SimpleStatementSuite(body=[cst.Pass()]),
        )
        code = cst.Module(body=[func]).code
        assert "def test(name):" in code

    def test_parameter_with_annotation(self) -> None:
        """Should create parameter with type annotation."""
        annotation = cst.Annotation(annotation=cst.Name("str"))
        param = create_parameter("name", annotation=annotation)
        func = cst.FunctionDef(
            name=cst.Name("test"),
            params=cst.Parameters(params=[param]),
            body=cst.SimpleStatementSuite(body=[cst.Pass()]),
        )
        code = cst.Module(body=[func]).code
        assert "def test(name: str):" in code

    def test_parameter_with_default_value(self) -> None:
        """Should create parameter with default value."""
        param = create_parameter("count", default=cst.Integer("0"))
        func = cst.FunctionDef(
            name=cst.Name("test"),
            params=cst.Parameters(params=[param]),
            body=cst.SimpleStatementSuite(body=[cst.Pass()]),
        )
        code = cst.Module(body=[func]).code
        assert "def test(count = 0):" in code

    def test_parameter_with_annotation_and_default(self) -> None:
        """Should create parameter with both annotation and default value."""
        annotation = cst.Annotation(annotation=cst.Name("int"))
        param = create_parameter("age", annotation=annotation, default=cst.Integer("0"))
        func = cst.FunctionDef(
            name=cst.Name("test"),
            params=cst.Parameters(params=[param]),
            body=cst.SimpleStatementSuite(body=[cst.Pass()]),
        )
        code = cst.Module(body=[func]).code
        assert "def test(age: int = 0):" in code

    def test_parameter_with_complex_annotation(self) -> None:
        """Should create parameter with complex type annotation."""
        # Create list[str] annotation
        annotation = cst.Annotation(
            annotation=cst.Subscript(
                value=cst.Name("list"),
                slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("str")))],
            )
        )
        param = create_parameter("items", annotation=annotation)
        func = cst.FunctionDef(
            name=cst.Name("test"),
            params=cst.Parameters(params=[param]),
            body=cst.SimpleStatementSuite(body=[cst.Pass()]),
        )
        code = cst.Module(body=[func]).code
        assert "def test(items: list[str]):" in code

    def test_parameter_with_none_default(self) -> None:
        """Should create parameter with None as default value."""
        param = create_parameter("value", default=cst.Name("None"))
        func = cst.FunctionDef(
            name=cst.Name("test"),
            params=cst.Parameters(params=[param]),
            body=cst.SimpleStatementSuite(body=[cst.Pass()]),
        )
        code = cst.Module(body=[func]).code
        assert "def test(value = None):" in code

    def test_returns_param(self) -> None:
        """Should return a Param instance."""
        param = create_parameter("name")
        assert isinstance(param, cst.Param)
        assert param.name.value == "name"


class TestIntegration:
    """Integration tests combining multiple utility functions."""

    def test_create_complete_class_with_init(self) -> None:
        """Should create a complete class with __init__ method using utilities."""
        # Create __init__ method with super() call
        super_args = [cst.Arg(value=cst.Name("name"))]
        init_method = create_init_method(["name", "age"], super_call_args=super_args)

        # Create a simple class with the __init__ method
        class_def = cst.ClassDef(
            name=cst.Name("Person"),
            body=cst.IndentedBlock(body=[init_method]),
        )

        code = cst.Module(body=[class_def]).code
        assert "class Person:" in code
        assert "def __init__(self, name, age):" in code
        assert "super().__init__(name)" in code
        assert "self.name = name" in code
        assert "self.age = age" in code

    def test_create_init_with_mixed_parameters(self) -> None:
        """Should handle parameters with annotations and field assignments."""
        # This tests that the utilities produce valid Python code
        method = create_init_method(
            ["name", "count"],
            field_assignments={
                "name": cst.Name("name"),
                "count": cst.Integer("0"),
            },
        )

        code = cst.Module(body=[method]).code
        # Verify the generated code is valid Python
        assert "def __init__(self, name, count):" in code
        assert "self.name = name" in code
        assert "self.count = 0" in code

        # Verify it's valid by parsing it back
        parsed = cst.parse_module(code)
        assert isinstance(parsed.body[0], cst.FunctionDef)
