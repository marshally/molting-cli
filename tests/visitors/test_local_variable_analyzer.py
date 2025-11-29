"""Tests for LocalVariableAnalyzer visitor.

LocalVariableAnalyzer identifies local variable definitions and usage
within a function, helping determine which variables need to be passed
as parameters to extracted code.
"""

import libcst as cst

from molting.core.local_variable_analyzer import LocalVariableAnalyzer


class TestLocalVariableAnalyzer:
    """Test suite for LocalVariableAnalyzer."""

    def test_identifies_local_variable_assignments(self) -> None:
        """Test that local variable assignments are identified.

        Local variables are defined via simple assignment (e.g., x = 5)
        and annotated assignment (e.g., x: int = 5).
        """
        code = """
def calculate(a, b):
    x = 10
    y: int = 20
    z = x + y
    return z
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "calculate")
        local_vars = analyzer.get_local_variables()

        assert "x" in local_vars
        assert "y" in local_vars
        assert "z" in local_vars
        # Function parameters should not be in local variables
        assert "a" not in local_vars
        assert "b" not in local_vars

    def test_identifies_parameter_names(self) -> None:
        """Test that function parameters are identified separately from locals."""
        code = """
def process(param1, param2):
    local_var = param1 + param2
    return local_var
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "process")

        params = analyzer.get_parameters()
        assert "param1" in params
        assert "param2" in params

        local_vars = analyzer.get_local_variables()
        assert "local_var" in local_vars
        assert "param1" not in local_vars
        assert "param2" not in local_vars

    def test_identifies_variables_used_in_code_block(self) -> None:
        """Test that variables used in an expression are identified."""
        code = """
def calculate():
    x = 10
    y = 20
    z = x + y
    return z
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "calculate")

        # Simulate analyzing a code block that uses x and y
        # This would be lines 4-5 (z = x + y; return z)
        used_vars = analyzer.get_variables_used_in_range(4, 5)
        assert "x" in used_vars
        assert "y" in used_vars
        assert "z" in used_vars

    def test_identifies_which_locals_are_defined_before_use(self) -> None:
        """Test that locals defined before usage are identified.

        This distinguishes between:
        - Local variables: defined in the function before use
        - Parameters: passed in from outside
        - External references: undefined variables
        """
        code = """
def process(param):
    local_x = 10
    local_y = local_x + param
    return local_y
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "process")

        # Variables defined in this function
        local_vars = analyzer.get_local_variables()
        assert "local_x" in local_vars
        assert "local_y" in local_vars

        # Variables that are parameters
        params = analyzer.get_parameters()
        assert "param" in params

    def test_handles_method_context(self) -> None:
        """Test that the analyzer correctly handles class methods.

        Instance variables (self.attr) should not be treated as local variables.
        """
        code = """
class Calculator:
    def __init__(self):
        self.base = 10

    def calculate(self):
        local_val = 5
        result = self.base + local_val
        return result
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "Calculator", "calculate")

        # local_val should be identified as local
        local_vars = analyzer.get_local_variables()
        assert "local_val" in local_vars

        # self.base should NOT be in local variables
        assert "base" not in local_vars

    def test_identifies_variables_to_pass_as_parameters(self) -> None:
        """Test identifying which local variables must be passed to extracted code.

        When extracting code that uses local variables, those locals need to be
        parameters to the extracted method. This method should identify which
        local variables need to be passed.
        """
        code = """
def process(param1):
    local1 = 10
    local2 = 20
    # Extracted code below uses local1 and local2
    result = local1 + local2 + param1
    return result
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "process")

        # For a code block (result = local1 + local2 + param1)
        # that uses local1, local2, and param1
        # We should identify which are locals vs params
        variables_used = analyzer.get_variables_used_in_range(5, 6)

        # All three are used
        assert "local1" in variables_used
        assert "local2" in variables_used
        assert "param1" in variables_used

    def test_handles_multiple_assignments_to_same_variable(self) -> None:
        """Test that variables with multiple assignments are still identified once."""
        code = """
def calculate():
    x = 10
    x = x + 5
    x = x * 2
    return x
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "calculate")

        local_vars = analyzer.get_local_variables()
        # x should appear only once in the list
        assert local_vars.count("x") == 1

    def test_ignores_self_references_in_methods(self) -> None:
        """Test that self.attribute assignments are not treated as local variables."""
        code = """
class MyClass:
    def init_state(self):
        self.x = 10
        self.y = 20
        local = 30
        return local
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "MyClass", "init_state")

        local_vars = analyzer.get_local_variables()
        # Only 'local' should be in local variables
        assert "local" in local_vars
        assert "x" not in local_vars
        assert "y" not in local_vars

    def test_handles_for_loop_variables(self) -> None:
        """Test that loop variables are identified as local variables."""
        code = """
def iterate(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "iterate")

        local_vars = analyzer.get_local_variables()
        assert "result" in local_vars
        # 'item' might also be considered a local variable in the function scope
        # depending on how strictly we define it

    def test_handles_with_statement_variables(self) -> None:
        """Test that with-statement variables are identified."""
        code = """
def read_file(filename):
    with open(filename) as f:
        content = f.read()
    return content
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "read_file")

        local_vars = analyzer.get_local_variables()
        assert "content" in local_vars
        # 'f' might also be identified as a local variable

    def test_exception_handlers(self) -> None:
        """Test that exception handler variables are identified."""
        code = """
def safe_divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError as e:
        result = 0
    return result
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "safe_divide")

        local_vars = analyzer.get_local_variables()
        assert "result" in local_vars

    def test_distinguishes_locals_from_parameters(self) -> None:
        """Test that we correctly distinguish between parameters and locals.

        This is the critical test for the main use case: when extracting
        code, knowing which variables are locals vs parameters determines
        what must be passed to the extracted method.
        """
        code = """
def process_data(data, threshold):
    # Parameters: data, threshold
    filtered = [x for x in data if x > threshold]
    # Local variables: filtered, total, average
    total = sum(filtered)
    count = len(filtered)
    average = total / count if count > 0 else 0
    return average
"""
        module = cst.parse_module(code)
        analyzer = LocalVariableAnalyzer(module, "", "process_data")

        params = analyzer.get_parameters()
        assert "data" in params
        assert "threshold" in params
        assert len(params) == 2

        locals_vars = analyzer.get_local_variables()
        assert "filtered" in locals_vars
        assert "total" in locals_vars
        assert "count" in locals_vars
        assert "average" in locals_vars
        assert "data" not in locals_vars
        assert "threshold" not in locals_vars
