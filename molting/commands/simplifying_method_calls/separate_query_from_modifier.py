"""Separate Query from Modifier refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target

# List of method names that mutate state
MUTATING_METHODS = frozenset(["pop", "remove", "append", "clear", "extend"])


class SeparateQueryFromModifierCommand(BaseCommand):
    """Command to separate a query from a modifier into two separate methods."""

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
            new_body = []
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
            return self._extract_names_from_and_pattern(parts[0], parts[1])

        # Fallback patterns for non-standard names
        return self._generate_fallback_names(original_name)

    def _extract_names_from_and_pattern(
        self, query_part: str, modifier_part: str
    ) -> tuple[str, str]:
        """Extract method names from 'verb1_and_verb2_noun' pattern.

        Args:
            query_part: The query verb part (e.g., "get")
            modifier_part: The modifier part (e.g., "remove_intruder")

        Returns:
            Tuple of (query_name, modifier_name)
        """
        modifier_words = modifier_part.split("_")
        if len(modifier_words) > 1:
            noun = "_".join(modifier_words[1:])
            return f"{query_part}_{noun}", modifier_part

        return query_part, modifier_part

    def _generate_fallback_names(self, original_name: str) -> tuple[str, str]:
        """Generate fallback names when standard pattern is not found.

        Args:
            original_name: The original method name

        Returns:
            Tuple of (query_name, modifier_name)
        """
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

        for stmt in method.body.body:
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
                transformed = self._transform_for_query(stmt)
                if transformed:
                    query_stmts.append(transformed)
            else:
                query_stmts.append(stmt)

        return query_stmts

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
        return False

    def _is_control_flow(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is control flow.

        Args:
            stmt: The statement to check

        Returns:
            True if the statement is control flow
        """
        return isinstance(stmt, (cst.If, cst.While, cst.For))

    def _transform_for_query(self, stmt: cst.SimpleStatementLine) -> cst.BaseStatement | None:
        """Transform a statement for the query method.

        Args:
            stmt: The statement to transform

        Returns:
            Transformed statement or None to skip
        """
        for sub_stmt in stmt.body:
            if isinstance(sub_stmt, cst.Assign):
                # Assignment to local variable - convert to return
                # Skip it for query, we'll return the value directly
                return None
            elif isinstance(sub_stmt, cst.Return):
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

        result = []
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

        result = []
        for stmt in block.body:
            if self._is_pure_modifier(stmt):
                result.append(stmt)
            # Skip assignments, returns, and other query operations

        return result


# Register the command
register_command(SeparateQueryFromModifierCommand)
