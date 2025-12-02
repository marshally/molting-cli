"""Conditional pattern matching infrastructure for multi-function refactoring.

This module provides tools for finding and matching identical conditional patterns
across multiple functions in a codebase. It enables refactorings that need to
identify duplicate logic (like repeated eligibility checks) and consolidate them.
"""

from dataclasses import dataclass

import libcst as cst
from libcst import metadata


@dataclass(frozen=True)
class ConditionalPatternSignature:
    """Hashable representation of a conditional pattern for matching.

    This captures the essential structure of a sequence of conditional statements
    in a way that allows comparison across different functions, even when
    parameter names differ.

    Attributes:
        conditions: Tuple of normalized condition strings, sorted alphabetically
        num_statements: Number of if statements in the pattern
    """

    conditions: tuple[str, ...]
    num_statements: int

    def __hash__(self) -> int:
        """Hash based on conditions and statement count."""
        return hash((self.conditions, self.num_statements))

    def __eq__(self, other: object) -> bool:
        """Compare patterns for equality."""
        if not isinstance(other, ConditionalPatternSignature):
            return NotImplemented
        return self.conditions == other.conditions and self.num_statements == other.num_statements


@dataclass
class PatternMatch:
    """Represents a function that matches a conditional pattern.

    Attributes:
        function_name: Name of the function containing the pattern
        class_name: Name of the containing class (empty string for module-level)
        start_line: Start line of the pattern within the function
        end_line: End line of the pattern within the function
        conditions: The actual CST condition expressions
        return_value: The return value expression from the if bodies
    """

    function_name: str
    class_name: str
    start_line: int
    end_line: int
    conditions: list[cst.BaseExpression]
    return_value: cst.BaseExpression | None


def normalize_condition(condition: cst.BaseExpression, param_map: dict[str, str]) -> str:
    """Normalize a condition expression to a canonical string form.

    Replaces function parameter names with positional placeholders ($0, $1, etc.)
    so that patterns can match across functions with different parameter names.

    Example:
        Input:  employee.seniority < 2, param_map={"employee": "$0"}
        Output: "$0.seniority < 2"

    Args:
        condition: The CST expression to normalize
        param_map: Mapping from parameter names to placeholders

    Returns:
        Normalized string representation of the condition
    """
    # Convert to string first
    dummy_module = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(condition)])])
    code = dummy_module.code.strip()

    # Replace parameter names with placeholders using word boundaries
    # Sort by length (longest first) to avoid partial replacements
    sorted_params = sorted(param_map.keys(), key=len, reverse=True)

    for param_name in sorted_params:
        placeholder = param_map[param_name]
        # Use simple word boundary replacement
        # Handle: param.attr, param[x], (param), param,
        import re

        pattern = rf"\b{re.escape(param_name)}\b"
        code = re.sub(pattern, placeholder, code)

    return code


def build_param_map(func: cst.FunctionDef) -> dict[str, str]:
    """Build a mapping from parameter names to positional placeholders.

    Args:
        func: The function definition

    Returns:
        Mapping like {"self": "$0", "employee": "$1"} or {"employee": "$0"}
    """
    param_map: dict[str, str] = {}
    for i, param in enumerate(func.params.params):
        param_map[param.name.value] = f"${i}"
    return param_map


class PatternExtractor(cst.CSTVisitor):
    """Extracts a conditional pattern from a specific function and line range.

    This visitor analyzes a function to find consecutive if statements within
    a line range that all return the same value, and creates a signature
    representing that pattern.
    """

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        target_function: str,
        target_class: str,
        start_line: int,
        end_line: int,
    ) -> None:
        """Initialize the extractor.

        Args:
            target_function: Name of the function to analyze
            target_class: Name of the class (empty string for module-level)
            start_line: Start line of the pattern range
            end_line: End line of the pattern range
        """
        self.target_function = target_function
        self.target_class = target_class
        self.start_line = start_line
        self.end_line = end_line

        self.conditions: list[cst.BaseExpression] = []
        self.return_value: cst.BaseExpression | None = None
        self.param_map: dict[str, str] = {}
        self.current_class: str = ""
        self.signature: ConditionalPatternSignature | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track current class."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Reset class tracking."""
        self.current_class = ""

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Extract pattern from target function."""
        # Check if this is the target function
        if node.name.value != self.target_function:
            return True
        if self.target_class and self.current_class != self.target_class:
            return True
        if not self.target_class and self.current_class:
            return True

        # Build parameter map for normalization
        self.param_map = build_param_map(node)

        # Extract conditions from if statements in the line range
        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.If):
                    try:
                        pos = self.get_metadata(metadata.PositionProvider, stmt)
                        if pos.start.line < self.start_line or pos.start.line > self.end_line:
                            continue
                    except KeyError:
                        continue

                    # Check if this has a simple return
                    return_val = self._get_return_value(stmt)
                    if return_val is None:
                        continue

                    # First condition or matching return value
                    if self.return_value is None:
                        self.return_value = return_val
                        self.conditions.append(stmt.test)
                    elif self._values_match(return_val, self.return_value):
                        self.conditions.append(stmt.test)
                    else:
                        # Different return value, stop
                        break

        # Create signature if we found conditions
        if self.conditions:
            normalized = []
            for cond in self.conditions:
                norm = normalize_condition(cond, self.param_map)
                normalized.append(norm)

            # Sort for order-independent matching
            normalized.sort()
            self.signature = ConditionalPatternSignature(
                conditions=tuple(normalized),
                num_statements=len(self.conditions),
            )

        return True

    def _get_return_value(self, if_stmt: cst.If) -> cst.BaseExpression | None:
        """Get return value from an if statement with a simple return body."""
        if not isinstance(if_stmt.body, cst.IndentedBlock):
            return None
        if len(if_stmt.body.body) != 1:
            return None

        body_stmt = if_stmt.body.body[0]
        if not isinstance(body_stmt, cst.SimpleStatementLine):
            return None
        if len(body_stmt.body) != 1:
            return None

        item = body_stmt.body[0]
        if isinstance(item, cst.Return) and item.value:
            return item.value
        return None

    def _values_match(self, val1: cst.BaseExpression, val2: cst.BaseExpression) -> bool:
        """Check if two return values match (same type, ignoring exact value)."""
        # For pattern matching, we just need same type of return (e.g., both return numbers)
        # The actual values can differ (0 vs 0.5)
        if isinstance(val1, cst.Integer) and isinstance(val2, cst.Integer):
            return True
        if isinstance(val1, cst.Float) and isinstance(val2, cst.Float):
            return True
        if isinstance(val1, cst.Integer) and isinstance(val2, cst.Float):
            return True
        if isinstance(val1, cst.Float) and isinstance(val2, cst.Integer):
            return True
        return False


class PatternScanner(cst.CSTVisitor):
    """Scans a module for functions containing a matching conditional pattern.

    This visitor walks through all functions in a module and identifies those
    that have the same pattern of conditional statements as the target.
    """

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        target_pattern: ConditionalPatternSignature,
        exclude_function: str = "",
        exclude_class: str = "",
    ) -> None:
        """Initialize the scanner.

        Args:
            target_pattern: The pattern signature to search for
            exclude_function: Function name to exclude (usually the original target)
            exclude_class: Class name to exclude (if method)
        """
        self.target_pattern = target_pattern
        self.exclude_function = exclude_function
        self.exclude_class = exclude_class
        self.matches: list[PatternMatch] = []
        self.current_class: str = ""

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track current class."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Reset class tracking."""
        self.current_class = ""

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Check if this function matches the pattern."""
        # Skip the original target function
        if node.name.value == self.exclude_function:
            if not self.exclude_class and not self.current_class:
                return True
            if self.exclude_class == self.current_class:
                return True

        # Build parameter map for this function
        param_map = build_param_map(node)

        # Find consecutive if statements with matching returns
        conditions: list[cst.BaseExpression] = []
        return_value: cst.BaseExpression | None = None
        start_line = 0
        end_line = 0

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.If):
                    try:
                        pos = self.get_metadata(metadata.PositionProvider, stmt)
                        line = pos.start.line
                    except KeyError:
                        continue

                    ret_val = self._get_return_value(stmt)
                    if ret_val is None:
                        if conditions:
                            break  # Pattern ended
                        continue

                    if return_value is None:
                        return_value = ret_val
                        conditions.append(stmt.test)
                        start_line = line
                        end_line = line
                    elif self._values_match(ret_val, return_value):
                        conditions.append(stmt.test)
                        end_line = line
                    else:
                        break

        # Check if conditions match the target pattern
        if conditions:
            normalized = []
            for cond in conditions:
                norm = normalize_condition(cond, param_map)
                normalized.append(norm)
            normalized.sort()

            candidate = ConditionalPatternSignature(
                conditions=tuple(normalized),
                num_statements=len(conditions),
            )

            if candidate == self.target_pattern:
                self.matches.append(
                    PatternMatch(
                        function_name=node.name.value,
                        class_name=self.current_class,
                        start_line=start_line,
                        end_line=end_line,
                        conditions=conditions,
                        return_value=return_value,
                    )
                )

        return True

    def _get_return_value(self, if_stmt: cst.If) -> cst.BaseExpression | None:
        """Get return value from an if statement with a simple return body."""
        if not isinstance(if_stmt.body, cst.IndentedBlock):
            return None
        if len(if_stmt.body.body) != 1:
            return None

        body_stmt = if_stmt.body.body[0]
        if not isinstance(body_stmt, cst.SimpleStatementLine):
            return None
        if len(body_stmt.body) != 1:
            return None

        item = body_stmt.body[0]
        if isinstance(item, cst.Return) and item.value:
            return item.value
        return None

    def _values_match(self, val1: cst.BaseExpression, val2: cst.BaseExpression) -> bool:
        """Check if two return values match (same type)."""
        if isinstance(val1, cst.Integer) and isinstance(val2, cst.Integer):
            return True
        if isinstance(val1, cst.Float) and isinstance(val2, cst.Float):
            return True
        if isinstance(val1, cst.Integer) and isinstance(val2, cst.Float):
            return True
        if isinstance(val1, cst.Float) and isinstance(val2, cst.Integer):
            return True
        return False


def extract_pattern(
    module: cst.Module,
    function_name: str,
    class_name: str,
    start_line: int,
    end_line: int,
) -> ConditionalPatternSignature | None:
    """Extract a conditional pattern from a function.

    Args:
        module: The CST module
        function_name: Name of the function to analyze
        class_name: Name of the class (empty string for module-level)
        start_line: Start line of the pattern range
        end_line: End line of the pattern range

    Returns:
        The pattern signature, or None if no pattern found
    """
    wrapper = metadata.MetadataWrapper(module)
    extractor = PatternExtractor(function_name, class_name, start_line, end_line)
    wrapper.visit(extractor)
    return extractor.signature


def scan_for_pattern(
    module: cst.Module,
    pattern: ConditionalPatternSignature,
    exclude_function: str = "",
    exclude_class: str = "",
) -> list[PatternMatch]:
    """Scan a module for functions matching a pattern.

    Args:
        module: The CST module to scan
        pattern: The pattern signature to match
        exclude_function: Function to exclude from matching
        exclude_class: Class to exclude (if method)

    Returns:
        List of PatternMatch objects for matching functions
    """
    wrapper = metadata.MetadataWrapper(module)
    scanner = PatternScanner(pattern, exclude_function, exclude_class)
    wrapper.visit(scanner)
    return scanner.matches
