"""Substitute Algorithm refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class SubstituteAlgorithmCommand(BaseCommand):
    """Replace the body of a method with a new algorithm that is clearer or more efficient.

    The Substitute Algorithm refactoring replaces the implementation of a method with
    a different algorithm that achieves the same result in a clearer, more efficient,
    or more maintainable way. This refactoring is particularly useful when you discover
    a better way to solve a problem or when you need to optimize performance-critical code.

    Based on Martin Fowler's "Refactoring: Improving the Design of Existing Code", this
    refactoring helps improve code clarity and maintainability when the current algorithm
    is difficult to understand or perform poorly.

    **When to use:**
    - You've found a simpler or more elegant algorithm that achieves the same result
    - The current algorithm is difficult to understand or maintain
    - You need to optimize performance and have a more efficient approach
    - Multiple conditional checks can be consolidated into a cleaner data structure approach
    - You want to replace complex loop-based logic with built-in or library functions

    **Example:**
    Before:
        def find_match(candidates):
            for candidate in candidates:
                if candidate == "A":
                    return candidate
                if candidate == "B":
                    return candidate
                if candidate == "C":
                    return candidate
            return ""

    After:
        def find_match(candidates):
            candidates = ["A", "B", "C"]
            for candidate in candidates:
                if candidate in candidates:
                    return candidate
            return ""
    """

    name = "substitute-algorithm"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply substitute-algorithm refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]

        # Read file
        source_code = self.file_path.read_text()

        # Parse and transform
        module = cst.parse_module(source_code)
        transformer = SubstituteAlgorithmTransformer(target)
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class SubstituteAlgorithmTransformer(cst.CSTTransformer):
    """Transforms a function by substituting its algorithm."""

    def __init__(self, function_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to transform
        """
        self.function_name = function_name

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and substitute the algorithm."""
        if original_node.name.value == self.function_name:
            # Check if this is the pattern we want to transform
            if self._is_substitute_pattern(original_node):
                return self._transform_to_cleaner_algorithm(updated_node)
        return updated_node

    def _is_substitute_pattern(self, node: cst.FunctionDef) -> bool:
        """Check if function matches the substitute algorithm pattern.

        Args:
            node: The function definition node

        Returns:
            True if this function has a for loop with multiple if statements checking equality
        """
        # Look for a for loop containing multiple if statements with equality checks
        for stmt in node.body.body:
            if isinstance(stmt, cst.For):
                if_count = 0
                for inner_stmt in stmt.body.body:
                    if isinstance(inner_stmt, cst.If):
                        if_count += 1
                if if_count >= 2:
                    return True
        return False

    def _extract_loop_information(
        self, node: cst.FunctionDef
    ) -> tuple[list[cst.SimpleString], str, str] | None:
        """Extract loop variable, iterable, and candidates from function.

        Args:
            node: The function definition node

        Returns:
            Tuple of (candidates, loop_var, param_name) or None if pattern not found
        """
        for stmt in node.body.body:
            if isinstance(stmt, cst.For):
                loop_var = stmt.target.value if isinstance(stmt.target, cst.Name) else None
                param_name = stmt.iter.value if isinstance(stmt.iter, cst.Name) else None

                if not loop_var or not param_name:
                    continue

                candidates = self._extract_candidates(stmt)
                if candidates:
                    return candidates, loop_var, param_name

        return None

    def _extract_candidates(self, for_loop: cst.For) -> list[cst.SimpleString]:
        """Extract candidate values from if statements in a for loop.

        Args:
            for_loop: The for loop node

        Returns:
            List of candidate string values
        """
        candidates = []
        for inner_stmt in for_loop.body.body:
            if isinstance(inner_stmt, cst.If):
                if isinstance(inner_stmt.test, cst.Comparison):
                    comp = inner_stmt.test
                    if len(comp.comparisons) == 1:
                        target = comp.comparisons[0].comparator
                        if isinstance(target, cst.SimpleString):
                            candidates.append(target)
        return candidates

    def _transform_to_cleaner_algorithm(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform the function to use a cleaner algorithm.

        Args:
            node: The function definition node

        Returns:
            Transformed function definition
        """
        loop_info = self._extract_loop_information(node)
        if not loop_info:
            return node

        candidates, loop_var, param_name = loop_info

        candidates_assign = self._create_candidates_assignment(candidates)
        for_loop = self._create_cleaner_for_loop(loop_var, param_name)
        final_return = self._create_empty_return()

        new_body = cst.IndentedBlock(body=[candidates_assign, for_loop, final_return])

        return node.with_changes(body=new_body)

    def _create_candidates_assignment(
        self, candidates: list[cst.SimpleString]
    ) -> cst.SimpleStatementLine:
        """Create the candidates list assignment statement.

        Args:
            candidates: List of candidate string values

        Returns:
            CST node for candidates assignment
        """
        candidates_list = cst.List(elements=[cst.Element(value=c) for c in candidates])
        return cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(value="candidates"))],
                    value=candidates_list,
                )
            ]
        )

    def _create_cleaner_for_loop(self, loop_var: str, param_name: str) -> cst.For:
        """Create the cleaner for loop with 'in' check.

        Args:
            loop_var: Name of the loop variable
            param_name: Name of the iterable parameter

        Returns:
            CST node for the for loop
        """
        for_body = [
            cst.If(
                test=cst.Comparison(
                    left=cst.Name(value=loop_var),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.In(), comparator=cst.Name(value="candidates")
                        )
                    ],
                ),
                body=cst.IndentedBlock(
                    body=[
                        cst.SimpleStatementLine(body=[cst.Return(value=cst.Name(value=loop_var))])
                    ]
                ),
            )
        ]

        return cst.For(
            target=cst.Name(value=loop_var),
            iter=cst.Name(value=param_name),
            body=cst.IndentedBlock(body=for_body),
        )

    def _create_empty_return(self) -> cst.SimpleStatementLine:
        """Create the final return statement with empty string.

        Returns:
            CST node for return statement
        """
        return cst.SimpleStatementLine(body=[cst.Return(value=cst.SimpleString(value='""'))])


# Register the command
register_command(SubstituteAlgorithmCommand)
