"""Separate Query from Modifier refactoring command."""

from collections.abc import Sequence
from dataclasses import dataclass

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


@dataclass
class CallSiteInfo:
    """Information about a call site that needs to be updated."""

    receiver_code: str  # The object the method is called on (e.g., "self.security")
    assigned_var: str  # Variable the result is assigned to (e.g., "threat")
    line: int  # Line number of the call


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

        # Read source
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # First pass: split the method into query and modifier (if present)
        transformer = SeparateQueryFromModifierTransformer(class_name, method_name)
        modified_tree = module.visit(transformer)

        # Get the generated method names
        query_name = transformer.query_name
        modifier_name = transformer.modifier_name

        # If we found and split the method, we have the method names
        # If not, we need to derive them from the original method name for call site updates
        if not query_name or not modifier_name:
            # Method definition not found in this file, but we still need to update call sites
            # Derive the method names the same way the transformer would
            query_name, modifier_name = transformer._generate_method_names(method_name)

        # Second pass: update all call sites (whether or not method definition was in this file)
        # Pass the query_first flag from the first transformer (if it was set)
        query_first = transformer.query_first if hasattr(transformer, "query_first") else True
        wrapper = metadata.MetadataWrapper(modified_tree)
        call_site_transformer = CallSiteUpdateTransformer(
            class_name, method_name, query_name, modifier_name, query_first
        )
        modified_tree = wrapper.visit(call_site_transformer)

        # Write back only if changes were made
        new_code = modified_tree.code
        if new_code != source_code:
            self.file_path.write_text(new_code)


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
        self.query_name: str = ""
        self.modifier_name: str = ""
        self.query_first: bool = True  # Track whether query or modifier comes first

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
            # Order follows the original method name pattern
            new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
            for stmt in updated_node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.method_name:
                    if self.query_first:
                        new_body.append(query_method)
                        new_body.append(modifier_method)
                    else:
                        new_body.append(modifier_method)
                        new_body.append(query_method)
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
        # Store for later use in call site updates
        self.query_name = query_name
        self.modifier_name = modifier_name

        # Create query and modifier bodies
        query_body = self._create_query_body(original_method)
        modifier_body = self._create_modifier_body(original_method)

        # Note: Docstring generation disabled for now to avoid breaking existing tests
        # # Check if the original method had a docstring
        # has_docstring = self._has_docstring(original_method)
        #
        # # Add docstrings to the new methods only if the original had one
        # if has_docstring:
        #     query_docstring = self._create_query_docstring(...)
        #     modifier_docstring = self._create_modifier_docstring(...)
        #
        #     # Insert docstrings at the beginning of each body
        #     if query_docstring:
        #         query_body = [query_docstring] + query_body
        #     if modifier_docstring:
        #         modifier_body = [modifier_docstring] + modifier_body

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
        Also supports "increment_and_get" -> ("get_value", "increment").

        Args:
            original_name: The original method name

        Returns:
            Tuple of (query_name, modifier_name)
        """
        # Try to parse "verb1_and_verb2_noun" pattern
        parts = original_name.split("_and_")
        if len(parts) == 2:
            # For "increment_and_get", treat increment as modifier and get as query
            # Modifying verbs: increment, decrement, add, remove, pop, push, append, etc.
            modifying_verbs = {
                "increment",
                "decrement",
                "add",
                "remove",
                "pop",
                "push",
                "append",
                "delete",
                "clear",
                "reset",
                "update",
                "modify",
                "change",
                "process",
            }

            # Query verbs: get, find, search, query, etc.
            query_verbs = {"get", "find", "search", "query", "fetch", "retrieve"}

            # Check if first part is a modifier and second is a query
            if parts[0] in modifying_verbs and parts[1] in query_verbs:
                # Pattern: "increment_and_get" -> ("get_value", "increment")
                # Need to infer the noun - for now, use "value" as default
                # Track that modifier comes first in this case
                self.query_first = False
                return (f"{parts[1]}_value", parts[0])

            # Check if first part is a query and second is a modifier
            if parts[0] in query_verbs and parts[1] in modifying_verbs:
                # Pattern: "get_and_remove" -> ("get_X", "remove_X")
                # Query comes first
                self.query_first = True

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

    def _create_query_docstring(
        self, query_name: str, modifier_name: str, class_name: str
    ) -> cst.SimpleStatementLine:
        """Create a docstring for the query method.

        Args:
            query_name: Name of the query method
            modifier_name: Name of the modifier method
            class_name: Name of the class containing the method

        Returns:
            A statement containing the docstring
        """
        # Extract noun from query_name (e.g., "get_value" -> "value")
        noun = query_name.split("_", 1)[1] if "_" in query_name else "result"

        # Use the class name (lowercased) as context if appropriate
        context = class_name.lower()

        # Create a docstring matching the expected format
        noun_display = noun.replace("_", " ")
        docstring_text = (
            f'"""Get the current {context} {noun_display}.\n\n'
            f"        This method only queries state without modifying it.\n\n"
            f"        Returns:\n"
            f'            The current {noun_display}\n        """'
        )
        docstring = cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.SimpleString(value=docstring_text))]
        )
        return docstring

    def _create_modifier_docstring(
        self, modifier_name: str, query_name: str, class_name: str
    ) -> cst.SimpleStatementLine:
        """Create a docstring for the modifier method.

        Args:
            modifier_name: Name of the modifier method
            query_name: Name of the query method
            class_name: Name of the class containing the method

        Returns:
            A statement containing the docstring
        """
        # Extract the verb from the modifier name
        verb = modifier_name.split("_")[0].capitalize()

        # Use the class name (lowercased) as context
        context = class_name.lower()

        # Create a docstring matching the expected format
        docstring_text = (
            f'"""{verb} the {context}.\n\n'
            f"        This method only modifies state without returning a value.\n"
            f'        """'
        )
        docstring = cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.SimpleString(value=docstring_text))]
        )
        return docstring

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
        defined_vars: set[str] = set()

        for i, stmt in enumerate(method.body.body):
            # Skip docstring (first statement if it's an Expr with a string)
            if i == 0 and self._is_docstring(stmt):
                continue

            # Remove statements that modify state (including augmented assignments)
            if self._is_pure_modifier(stmt) or self._modifies_instance_state(stmt):
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

    def _has_docstring(self, method: cst.FunctionDef) -> bool:
        """Check if a method has a docstring.

        Args:
            method: The method to check

        Returns:
            True if the method has a docstring
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return False
        if not method.body.body:
            return False
        return self._is_docstring(method.body.body[0])

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

        for i, stmt in enumerate(method.body.body):
            # Skip docstring (first statement if it's an Expr with a string)
            if i == 0 and self._is_docstring(stmt):
                continue

            # Skip return statements (they go in the query method)
            if isinstance(stmt, cst.SimpleStatementLine):
                is_return = any(isinstance(sub_stmt, cst.Return) for sub_stmt in stmt.body)
                if is_return:
                    continue

            # Keep statements that modify state or control flow
            if self._is_pure_modifier(stmt) or self._modifies_instance_state(stmt):
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


class CallSiteUpdateTransformer(cst.CSTTransformer):
    """Updates call sites to use the new query and modifier methods."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        class_name: str,
        original_method: str,
        query_name: str,
        modifier_name: str,
        query_first: bool = True,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            original_method: Original method name being replaced
            query_name: Name of the new query method
            modifier_name: Name of the new modifier method
            query_first: Whether query comes first in original method name
        """
        self.class_name = class_name
        self.original_method = original_method
        self.query_name = query_name
        self.modifier_name = modifier_name
        self.query_first = query_first
        # Track pending modifier insertions: {var_name: receiver_code}
        self.pending_modifiers: dict[str, str] = {}
        # Track current function context
        self.current_function_params: list[str] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track function parameters for receiver detection."""
        self.current_function_params = []
        for param in node.params.params:
            self.current_function_params.append(param.name.value)
        return True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Process pending modifiers and clear function context when leaving.

        Any pending modifiers that weren't consumed by if/while blocks
        need to be inserted immediately after their assignments.
        """
        if self.pending_modifiers and isinstance(updated_node.body, cst.IndentedBlock):
            new_body = []
            consumed_vars = set()

            for stmt in updated_node.body.body:
                new_body.append(stmt)

                # Check if this is an assignment to a pending modifier variable
                if isinstance(stmt, cst.SimpleStatementLine):
                    for sub_stmt in stmt.body:
                        if isinstance(sub_stmt, cst.Assign) and len(sub_stmt.targets) == 1:
                            target = sub_stmt.targets[0].target
                            if (
                                isinstance(target, cst.Name)
                                and target.value in self.pending_modifiers
                            ):
                                var_name = target.value
                                receiver_code = self.pending_modifiers[var_name]
                                modifier_call = self._create_modifier_call(receiver_code)

                                if not self.query_first:
                                    # Modifier-first pattern: ALWAYS insert BEFORE the assignment
                                    # Re-add in correct order
                                    new_body.pop()  # Remove assignment
                                    new_body.append(modifier_call)  # Add modifier
                                    new_body.append(stmt)  # Re-add assignment
                                    consumed_vars.add(var_name)
                                else:
                                    # Query-first pattern: check if next stmt is if/while
                                    # If so, modifier will be inserted by leave_If/leave_While
                                    # Otherwise, insert after the assignment
                                    is_tested_next = self._is_tested_in_next_stmt(
                                        updated_node.body.body, new_body
                                    )

                                    if not is_tested_next:
                                        # Insert AFTER the assignment
                                        new_body.append(modifier_call)
                                        consumed_vars.add(var_name)
                                    # else: will be handled by leave_If/leave_While

            # Remove consumed variables from pending
            for var in consumed_vars:
                del self.pending_modifiers[var]

            updated_node = updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

        self.current_function_params = []
        self.pending_modifiers = {}
        return updated_node

    def _is_tested_in_next_stmt(
        self,
        all_stmts: Sequence[cst.BaseStatement],
        processed_stmts: Sequence[cst.BaseStatement],
    ) -> bool:
        """Check if the next unprocessed statement tests the variable."""
        if len(processed_stmts) < len(all_stmts):
            next_stmt = all_stmts[len(processed_stmts)]
            if isinstance(next_stmt, (cst.If, cst.While)):
                return True
        return False

    def _create_modifier_call(self, receiver_code: str) -> cst.SimpleStatementLine:
        """Create a modifier call statement."""
        receiver = cst.parse_expression(receiver_code)
        modifier_call = cst.Call(
            func=cst.Attribute(value=receiver, attr=cst.Name(self.modifier_name)),
            args=[],
        )
        return cst.SimpleStatementLine(body=[cst.Expr(modifier_call)])

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Replace calls to the original method with calls to the query method."""
        # Check if this is a call to the original method
        if isinstance(updated_node.func, cst.Attribute):
            if updated_node.func.attr.value == self.original_method:
                # Replace with query method name
                new_func = updated_node.func.with_changes(attr=cst.Name(self.query_name))
                return updated_node.with_changes(func=new_func)
        return updated_node

    def leave_SimpleStatementLine(  # noqa: N802
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel[cst.SimpleStatementLine]:
        """Transform or track assignments from the method call.

        Strategy:
        - If assignment will be followed by an if/while that tests the variable, track it for later
        - Otherwise, insert modifier call immediately after the assignment
        """
        # For modifier-first patterns, handle direct return statements
        if not self.query_first:
            for i, stmt in enumerate(updated_node.body):
                if isinstance(stmt, cst.Return) and stmt.value:
                    if isinstance(stmt.value, cst.Call) and isinstance(
                        stmt.value.func, cst.Attribute
                    ):
                        if stmt.value.func.attr.value == self.query_name:
                            # Direct return of query method - insert modifier before return
                            receiver = stmt.value.func.value
                            receiver_code = self._get_receiver_code(receiver)
                            modifier_call = self._create_modifier_call(receiver_code)

                            # Return both modifier call and return statement
                            return cst.FlattenSentinel([modifier_call, updated_node])

        # Check for assignments to track
        for stmt in updated_node.body:
            if isinstance(stmt, cst.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0].target
                if isinstance(target, cst.Name) and isinstance(stmt.value, cst.Call):
                    call = stmt.value
                    if isinstance(call.func, cst.Attribute):
                        if call.func.attr.value == self.query_name:
                            receiver = call.func.value
                            receiver_code = self._get_receiver_code(receiver)
                            if receiver_code:
                                # Track this assignment - will be processed later
                                # (Either by leave_If/leave_While, or in leave_IndentedBlock)
                                self.pending_modifiers[target.value] = receiver_code
        return updated_node

    def _get_receiver_code(self, receiver: cst.BaseExpression) -> str:
        """Get the code string for a receiver expression."""
        # Convert the receiver expression to code
        dummy_module = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(receiver)])])
        return dummy_module.code.strip()

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> cst.If:  # noqa: N802
        """Insert modifier call at the end of if-blocks that test the result variable."""
        # Check if any pending modifier variable is tested in this if
        var_name = self._get_tested_variable(updated_node.test)
        if var_name and var_name in self.pending_modifiers:
            # Skip if this is a negated test (if not x:) - it's likely an exit condition
            if self._is_negated_test(updated_node.test):
                return updated_node

            receiver_code = self.pending_modifiers[var_name]
            # Insert modifier call at the end of the if body
            updated_body = self._insert_modifier_at_end(updated_node.body, receiver_code)
            return updated_node.with_changes(body=updated_body)
        return updated_node

    def _is_negated_test(self, test: cst.BaseExpression) -> bool:
        """Check if a test is negated (if not x:)."""
        return isinstance(test, cst.UnaryOperation) and isinstance(test.operator, cst.Not)

    def leave_While(  # noqa: N802
        self, original_node: cst.While, updated_node: cst.While
    ) -> cst.While:
        """Insert modifier call at the end of while loop bodies."""
        # Check if any pending modifier is used in this while loop
        # We need to look inside the body for the assignment and the if-break pattern
        if not isinstance(updated_node.body, cst.IndentedBlock):
            return updated_node

        # Look for pattern: x = query(); if not x: break; ...; (need modifier here)
        var_name = None
        receiver_code = None

        for stmt in updated_node.body.body:
            # Look for assignments from the query method
            if isinstance(stmt, cst.SimpleStatementLine):
                for sub_stmt in stmt.body:
                    if isinstance(sub_stmt, cst.Assign) and len(sub_stmt.targets) == 1:
                        target = sub_stmt.targets[0].target
                        if isinstance(target, cst.Name):
                            if isinstance(sub_stmt.value, cst.Call):
                                call = sub_stmt.value
                                if isinstance(call.func, cst.Attribute):
                                    if call.func.attr.value == self.query_name:
                                        var_name = target.value
                                        receiver_code = self._get_receiver_code(call.func.value)
                                        break

        if var_name and receiver_code:
            # Insert modifier at the end of the loop body
            updated_body = self._insert_modifier_at_end(updated_node.body, receiver_code)
            return updated_node.with_changes(body=updated_body)

        return updated_node

    def _get_tested_variable(self, test: cst.BaseExpression) -> str | None:
        """Get the variable name being tested in a condition."""
        # Handle: if var:
        if isinstance(test, cst.Name):
            return test.value
        # Handle: if not var:
        if isinstance(test, cst.UnaryOperation):
            if isinstance(test.operator, cst.Not) and isinstance(test.expression, cst.Name):
                return test.expression.value
        return None

    def _insert_modifier_at_end(self, body: cst.BaseSuite, receiver_code: str) -> cst.IndentedBlock:
        """Insert the modifier call at the end of a block."""
        if not isinstance(body, cst.IndentedBlock):
            return body  # type: ignore

        # Parse the receiver and create the modifier call
        receiver = cst.parse_expression(receiver_code)
        modifier_call = cst.Call(
            func=cst.Attribute(value=receiver, attr=cst.Name(self.modifier_name)),
            args=[],
        )
        modifier_stmt = cst.SimpleStatementLine(body=[cst.Expr(modifier_call)])

        # Add to the end of the block
        new_body = list(body.body) + [modifier_stmt]
        return body.with_changes(body=new_body)


# Register the command
register_command(SeparateQueryFromModifierCommand)
