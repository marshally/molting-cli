"""Separate Query from Modifier refactoring command."""

from collections.abc import Sequence

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target

# List of method names that mutate state
MUTATING_METHODS = frozenset(["pop", "remove", "append", "clear", "extend"])


class SeparateQueryFromModifierCommand(BaseCommand):
    """Separate a method that queries and modifies into two independent methods.

    This refactoring applies the Command-Query Separation principle by splitting a single
    method that both returns a value and has side effects into two focused methods: one that
    queries (returns a value without side effects) and one that modifies (performs side effects
    without returning a value). This improves code clarity and makes each method's intent explicit.

    **When to use:**
    - A method returns a value and also modifies object state
    - You want to make the distinction between queries and modifications explicit
    - Callers need to distinguish between "checking" and "doing" operations
    - You're applying the Command-Query Separation principle from Martin Fowler's Refactoring

    **Example:**
    Before:
        def get_and_remove_intruder(self):
            if len(self.intruders) > 0:
                return self.intruders.pop(0)
            return None

    After:
        def get_intruder(self):
            if len(self.intruders) > 0:
                return self.intruders[0]
            return None

        def remove_intruder(self):
            if len(self.intruders) > 0:
                self.intruders.pop(0)
    """

    name = "separate-query-from-modifier"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply separate-query-from-modifier refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        class_name, method_name = parse_target(target, expected_parts=2)

        # Apply the transformation
        self.apply_libcst_transform(SeparateQueryFromModifierTransformer, class_name, method_name)


class SeparateQueryFromModifierTransformer(cst.CSTTransformer):
    """Transforms a class to separate query from modifier."""

    def __init__(self, class_name: str, method_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to separate
        """
        self.class_name = class_name
        self.method_name = method_name
        self.in_target_class = False
        self.target_method: cst.FunctionDef | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and insert new methods."""
        if original_node.name.value == self.class_name and self.target_method:
            # Create the query method and modifier method
            query_method, modifier_method = self._create_separated_methods(self.target_method)

            # Replace the original method with both new methods
            new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
            for stmt in updated_node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.method_name:
                    new_body.append(query_method)
                    new_body.append(modifier_method)
                else:
                    new_body.append(stmt)

            updated_node = updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )

            self.in_target_class = False
            self.target_method = None

        return updated_node

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and store if it's the target method."""
        if self.in_target_class and original_node.name.value == self.method_name:
            self.target_method = updated_node
        return updated_node

    def _create_separated_methods(
        self, original_method: cst.FunctionDef
    ) -> tuple[cst.FunctionDef, cst.FunctionDef]:
        """Create the query and modifier methods from the original.

        Args:
            original_method: The original method to separate

        Returns:
            Tuple of (query_method, modifier_method)
        """
        # Extract the query name and modifier name from original method name
        query_name, modifier_name = self._generate_method_names(self.method_name)

        # Create query and modifier bodies
        query_body = self._create_query_body(original_method)
        modifier_body = self._create_modifier_body(original_method)

        # Create query method
        query_method = original_method.with_changes(
            name=cst.Name(query_name), body=cst.IndentedBlock(body=query_body)
        )

        # Create modifier method
        modifier_method = original_method.with_changes(
            name=cst.Name(modifier_name), body=cst.IndentedBlock(body=modifier_body)
        )

        return query_method, modifier_method

    def _generate_method_names(self, original_name: str) -> tuple[str, str]:
        """Generate names for the query and modifier methods.

        Supports patterns like "get_and_remove_X" -> ("get_X", "remove_X").

        Args:
            original_name: The original method name

        Returns:
            Tuple of (query_name, modifier_name)
        """
        # Try to parse "verb1_and_verb2_noun" pattern
        parts = original_name.split("_and_")
        if len(parts) == 2:
            # For "process_and_get_X", the order is reversed (modifier first, query second)
            if parts[0] in ("process", "modify", "update", "change"):
                # Swap the parts so query comes first
                return self._extract_names_from_and_pattern(parts[1], parts[0])
            return self._extract_names_from_and_pattern(parts[0], parts[1])

        # Fallback patterns for non-standard names
        return self._generate_fallback_names(original_name)

    def _extract_names_from_and_pattern(
        self, query_part: str, modifier_part: str
    ) -> tuple[str, str]:
        """Extract method names from 'verb1_and_verb2_noun' pattern.

        Args:
            query_part: The query verb part (e.g., "get" or "get_next")
            modifier_part: The modifier part (e.g., "remove_intruder" or "process")

        Returns:
            Tuple of (query_name, modifier_name)
        """
        # Extract the noun from whichever part has it
        query_words = query_part.split("_")
        modifier_words = modifier_part.split("_")

        # Determine which part has the noun
        if len(query_words) > 1:
            # Query part has the noun (e.g., "get_next")
            noun = "_".join(query_words[1:])
            return query_part, f"{modifier_part}_{noun}"
        elif len(modifier_words) > 1:
            # Modifier part has the noun (e.g., "remove_intruder")
            noun = "_".join(modifier_words[1:])
            return f"{query_part}_{noun}", modifier_part

        # Neither has a noun, use as-is
        return query_part, modifier_part

    def _generate_fallback_names(self, original_name: str) -> tuple[str, str]:
        """Generate fallback names when standard pattern is not found.

        Args:
            original_name: The original method name

        Returns:
            Tuple of (query_name, modifier_name)
        """
        # Handle "process_and_get_X" pattern -> ("get_X", "process_X")
        if "process_and_get_" in original_name:
            parts = original_name.split("process_and_get_")
            if len(parts) == 2:
                noun = parts[1]
                return f"get_{noun}", f"process_{noun}"

        if original_name.startswith("get_"):
            base_name = original_name[4:]
            return original_name, f"modify_{base_name}"

        return f"get_{original_name}", f"modify_{original_name}"

    def _create_query_body(self, method: cst.FunctionDef) -> list[cst.BaseStatement]:
        """Create the query method body by removing modifier operations.

        Args:
            method: The original method

        Returns:
            List of statements for the query method
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return []

        query_stmts = []
        # Track which variables are defined in the query body
        defined_vars = set()

        for i, stmt in enumerate(method.body.body):
            # Skip docstring (first statement if it's an Expr with a string)
            if i == 0 and self._is_docstring(stmt):
                continue

            # Remove statements that modify state
            if self._is_pure_modifier(stmt):
                continue

            # Handle control flow separately
            if self._is_control_flow(stmt):
                transformed = self._transform_if_for_query(stmt)
                if transformed:
                    query_stmts.append(transformed)
            # Transform assignments to local variables into returns
            elif isinstance(stmt, cst.SimpleStatementLine):
                transformed = self._transform_for_query(stmt, defined_vars)
                if transformed:
                    query_stmts.append(transformed)
            else:
                query_stmts.append(stmt)

        return query_stmts

    def _is_docstring(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a docstring.

        Args:
            stmt: The statement to check

        Returns:
            True if the statement is a docstring
        """
        if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1:
            first = stmt.body[0]
            if isinstance(first, cst.Expr) and isinstance(
                first.value, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)
            ):
                return True
        return False

    def _create_modifier_body(self, method: cst.FunctionDef) -> list[cst.BaseStatement]:
        """Create the modifier method body by keeping only modifier operations.

        Args:
            method: The original method

        Returns:
            List of statements for the modifier method
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return []

        modifier_stmts = []

        for stmt in method.body.body:
            # Keep only statements that modify state or control flow
            if self._is_pure_modifier(stmt):
                modifier_stmts.append(stmt)
            elif self._is_control_flow(stmt):
                # Transform control flow to keep only modifier operations
                transformed = self._transform_for_modifier(stmt)
                if transformed:
                    modifier_stmts.append(transformed)

        return modifier_stmts

    def _is_pure_modifier(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a pure modifier (mutates state).

        Args:
            stmt: The statement to check

        Returns:
            True if the statement modifies state
        """
        if isinstance(stmt, cst.SimpleStatementLine):
            for sub_stmt in stmt.body:
                if isinstance(sub_stmt, cst.Expr) and isinstance(sub_stmt.value, cst.Call):
                    # Check for mutating method calls like .pop()
                    if isinstance(sub_stmt.value.func, cst.Attribute):
                        if sub_stmt.value.func.attr.value in MUTATING_METHODS:
                            return True
                    # Check for function calls with side effects like print()
                    elif isinstance(sub_stmt.value.func, cst.Name):
                        # Functions like print, input, etc. have side effects
                        if sub_stmt.value.func.value in ("print", "input", "open", "write"):
                            return True
        return False

    def _is_control_flow(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is control flow.

        Args:
            stmt: The statement to check

        Returns:
            True if the statement is control flow
        """
        return isinstance(stmt, (cst.If, cst.While, cst.For))

    def _transform_for_query(
        self, stmt: cst.SimpleStatementLine, defined_vars: set[str]
    ) -> cst.BaseStatement | None:
        """Transform a statement for the query method.

        Args:
            stmt: The statement to transform
            defined_vars: Set of variables defined in the query body so far

        Returns:
            Transformed statement or None to skip
        """
        for sub_stmt in stmt.body:
            if isinstance(sub_stmt, cst.Assign):
                # Assignment to local variable - convert to return
                # Skip it for query, we'll return the value directly
                return None
            elif isinstance(sub_stmt, cst.Return):
                # Check if the return value references an undefined variable
                if sub_stmt.value and isinstance(sub_stmt.value, cst.Name):
                    var_name = sub_stmt.value.value
                    if var_name not in defined_vars and not var_name.startswith("self."):
                        # Return value is an undefined local variable, convert to None
                        return cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("None"))])
                # Keep return statements
                return stmt

        return stmt

    def _transform_if_for_query(self, stmt: cst.BaseStatement) -> cst.BaseStatement | None:
        """Transform an if statement for the query method.

        Args:
            stmt: The if statement to transform

        Returns:
            Transformed statement or None to skip
        """
        if not isinstance(stmt, cst.If):
            return stmt

        # Filter the if body to keep only query operations
        new_body = self._filter_query_stmts(stmt.body)
        if not new_body:
            return None

        return stmt.with_changes(body=cst.IndentedBlock(body=new_body))

    def _filter_query_stmts(self, block: cst.BaseSuite) -> list[cst.BaseStatement]:
        """Filter statements in a block to keep only query operations.

        Args:
            block: The block to filter

        Returns:
            List of query statements
        """
        if not isinstance(block, cst.IndentedBlock):
            return []

        result: list[cst.BaseStatement] = []
        for stmt in block.body:
            # Skip pure modifiers
            if self._is_pure_modifier(stmt):
                continue

            # For assignments followed by returns, convert to direct return
            if isinstance(stmt, cst.SimpleStatementLine):
                for sub_stmt in stmt.body:
                    if isinstance(sub_stmt, cst.Assign):
                        # Found an assignment - convert the value to a return
                        result.append(
                            cst.SimpleStatementLine(body=[cst.Return(value=sub_stmt.value)])
                        )
                        # Don't process the return statement after this
                        return result
                    elif isinstance(sub_stmt, cst.Return):
                        result.append(stmt)
            else:
                result.append(stmt)

        return result

    def _transform_for_modifier(self, stmt: cst.BaseStatement) -> cst.BaseStatement | None:
        """Transform a control flow statement for the modifier method.

        Args:
            stmt: The statement to transform

        Returns:
            Transformed statement or None to skip
        """
        if isinstance(stmt, cst.If):
            # Transform the if body to keep only modifiers
            new_body = self._filter_modifier_stmts(stmt.body)
            if not new_body:
                return None

            return stmt.with_changes(body=cst.IndentedBlock(body=new_body))

        return stmt

    def _filter_modifier_stmts(self, block: cst.BaseSuite) -> list[cst.BaseStatement]:
        """Filter statements in a block to keep only modifiers.

        Args:
            block: The block to filter

        Returns:
            List of modifier statements
        """
        if not isinstance(block, cst.IndentedBlock):
            return []

        result: list[cst.BaseStatement] = []

        # First pass: identify which statements modify state
        needed_indices = set()
        for i, stmt in enumerate(block.body):
            if self._is_pure_modifier(stmt) or self._modifies_instance_state(stmt):
                needed_indices.add(i)

        # Second pass: iteratively add dependencies
        # Keep adding statements until no more dependencies are found
        changed = True
        max_iterations = len(block.body)
        iteration = 0
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            for i, stmt in enumerate(block.body):
                if i not in needed_indices:
                    if self._is_local_var_assignment_needed_for_statements(
                        stmt, block.body, i, needed_indices
                    ):
                        needed_indices.add(i)
                        changed = True

        # Third pass: collect the needed statements in order
        for i, stmt in enumerate(block.body):
            if i in needed_indices:
                result.append(stmt)

        return result

    def _is_local_var_assignment_needed_for_statements(
        self,
        stmt: cst.BaseStatement,
        all_stmts: Sequence[cst.BaseStatement],
        index: int,
        needed_indices: set[int],
    ) -> bool:
        """Check if a local variable assignment is needed for other needed statements.

        Args:
            stmt: The statement to check
            all_stmts: All statements in the block
            index: The index of this statement
            needed_indices: Set of indices of statements that are already needed

        Returns:
            True if this assignment is needed for later needed statements
        """
        # Check if this is a local variable assignment
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        assigned_var = None
        for sub_stmt in stmt.body:
            if isinstance(sub_stmt, cst.Assign) and len(sub_stmt.targets) == 1:
                target = sub_stmt.targets[0].target
                if isinstance(target, cst.Name):
                    # This is a local variable assignment
                    assigned_var = target.value

        if not assigned_var:
            return False

        # Check if this variable is used in later needed statements
        for j in range(index + 1, len(all_stmts)):
            if j in needed_indices:
                if self._uses_variable(all_stmts[j], assigned_var):
                    return True

        return False

    def _uses_variable(self, stmt: cst.BaseStatement, var_name: str) -> bool:
        """Check if a statement uses a specific variable.

        Args:
            stmt: The statement to check
            var_name: The variable name to look for

        Returns:
            True if the statement uses the variable
        """
        if isinstance(stmt, cst.SimpleStatementLine):
            for sub_stmt in stmt.body:
                if isinstance(sub_stmt, cst.Assign):
                    # Check in the target (for attribute assignments like lowest.field = value)
                    for target in sub_stmt.targets:
                        if self._expression_uses_variable(target.target, var_name):
                            return True
                    # Check in the value expression
                    if self._expression_uses_variable(sub_stmt.value, var_name):
                        return True
                elif isinstance(sub_stmt, cst.AugAssign):
                    # Check if the target or value uses the variable
                    if self._expression_uses_variable(sub_stmt.target, var_name):
                        return True
                    if self._expression_uses_variable(sub_stmt.value, var_name):
                        return True
                elif isinstance(sub_stmt, cst.Expr):
                    # Check for variable use in expression statements (like function calls)
                    if self._expression_uses_variable(sub_stmt.value, var_name):
                        return True
        return False

    def _expression_uses_variable(self, expr: cst.BaseExpression, var_name: str) -> bool:
        """Check if an expression uses a specific variable.

        Args:
            expr: The expression to check
            var_name: The variable name to look for

        Returns:
            True if the expression uses the variable
        """
        # Direct variable reference
        if isinstance(expr, cst.Name):
            if expr.value == var_name:
                return True
        # Attribute access (e.g., variable.attr)
        elif isinstance(expr, cst.Attribute):
            if isinstance(expr.value, cst.Name) and expr.value.value == var_name:
                return True
            # Recursively check the base expression
            return self._expression_uses_variable(expr.value, var_name)
        # Function calls (check arguments)
        elif isinstance(expr, cst.Call):
            for arg in expr.args:
                if self._expression_uses_variable(arg.value, var_name):
                    return True
        # F-strings (formatted string literals)
        elif isinstance(expr, cst.FormattedString):
            for part in expr.parts:
                if isinstance(part, cst.FormattedStringExpression):
                    if self._expression_uses_variable(part.expression, var_name):
                        return True
        # Conditional expressions (a if condition else b)
        elif isinstance(expr, cst.IfExp):
            if self._expression_uses_variable(expr.test, var_name):
                return True
            if self._expression_uses_variable(expr.body, var_name):
                return True
            if self._expression_uses_variable(expr.orelse, var_name):
                return True
        # Binary operations (a + b, a == b, etc.)
        elif isinstance(expr, cst.BinaryOperation):
            if self._expression_uses_variable(expr.left, var_name):
                return True
            if self._expression_uses_variable(expr.right, var_name):
                return True
        # Comparison operations (a > b)
        elif isinstance(expr, cst.Comparison):
            if self._expression_uses_variable(expr.left, var_name):
                return True
            for comp in expr.comparisons:
                if self._expression_uses_variable(comp.comparator, var_name):
                    return True
        return False

    def _modifies_instance_state(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement modifies instance state.

        Args:
            stmt: The statement to check

        Returns:
            True if the statement modifies instance state
        """
        if isinstance(stmt, cst.SimpleStatementLine):
            for sub_stmt in stmt.body:
                if isinstance(sub_stmt, cst.Assign):
                    # Check if this is an assignment to self.something or object.attribute
                    for target in sub_stmt.targets:
                        if isinstance(target.target, cst.Attribute):
                            # self.field = value or lowest.field = value
                            return True
                elif isinstance(sub_stmt, cst.AugAssign):
                    # self.field += value, etc.
                    if isinstance(sub_stmt.target, cst.Attribute):
                        return True
        return False


# Register the command
register_command(SeparateQueryFromModifierCommand)
