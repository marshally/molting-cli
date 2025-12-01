"""CallSiteUpdater for finding and updating code references.

This module provides the CallSiteUpdater class which combines search backends
and AST validators to find and transform all references to a symbol across
a codebase.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from molting.core.ast_validators import get_validator
from molting.core.reference_searcher import ReferenceSearcher, get_best_searcher
from molting.core.symbol_context import SymbolContext


@dataclass
class Reference:
    """Represents a single reference to a symbol in code.

    Attributes:
        file_path: Path to the file containing the reference
        line_number: Line number where the reference appears (1-indexed)
        column: Column number where the reference starts (0-indexed)
        node: The CST node representing the reference
        parent: The parent CST node
        module: The full module CST
        context: The SymbolContext type of this reference
        symbol: The symbol name being referenced
        containing_class: Name of the class containing this reference (if any)
        containing_function: Name of the function containing this reference (if any)
        attribute_chain: List of attributes in the chain (e.g., ["obj", "field"])
        source_line: The full source line containing the reference
        metadata: Additional metadata about the reference
    """

    file_path: Path
    line_number: int
    column: int
    node: cst.CSTNode
    parent: cst.CSTNode
    module: cst.Module
    context: SymbolContext
    symbol: str
    containing_class: str | None
    containing_function: str | None
    attribute_chain: list[str] | None
    source_line: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateResult:
    """Result of an update_all operation.

    Attributes:
        files_modified: List of file paths that were modified
        references_updated: Total number of references that were updated
    """

    files_modified: list[Path]
    references_updated: int


class CallSiteUpdater:
    """Find and update all references to a symbol across a directory.

    This class combines search backends (for fast text search) with AST validators
    (for precise pattern matching) to find and transform all references to a symbol.

    Example:
        updater = CallSiteUpdater(Path("/path/to/code"))

        # Find all attribute accesses of "manager"
        refs = updater.find_references("manager", SymbolContext.ATTRIBUTE_ACCESS)

        # Update all references
        result = updater.update_all("manager", SymbolContext.ATTRIBUTE_ACCESS, transformer)
    """

    def __init__(self, directory: Path, searcher: ReferenceSearcher | None = None) -> None:
        """Initialize the updater.

        Args:
            directory: Root directory to search in
            searcher: Optional custom search backend (auto-detects if not provided)
        """
        self.directory = directory
        self.searcher = searcher if searcher is not None else get_best_searcher()

    def find_references(
        self, symbol: str, context: SymbolContext, on_object: str | None = None
    ) -> list[Reference]:
        """Find all references matching the pattern.

        Args:
            symbol: The symbol name to find
            context: The context type to match (e.g., ATTRIBUTE_ACCESS)
            on_object: Optional object name to filter on

        Returns:
            List of Reference objects for all matches

        Raises:
            RuntimeError: If search or parsing fails
        """
        # Use the search backend to find potential matches
        text_matches = self.searcher.search(symbol, self.directory)

        # Get the validator for this context
        validator = get_validator(context)

        references = []

        # Process each text match to see if it's a true match
        for match in text_matches:
            try:
                # Parse the file
                source_code = match.file_path.read_text()
                module = cst.parse_module(source_code)

                # Find the node at this line and validate it
                node_finder = NodeFinder(match.line_number, symbol, validator, on_object)
                # Use metadata wrapper to provide position information
                wrapper = MetadataWrapper(module)
                wrapper.visit(node_finder)

                # If we found a matching node, create a Reference
                for found_node in node_finder.found_nodes:
                    # Get accurate position from metadata using the same wrapper
                    try:
                        pos = wrapper.resolve(PositionProvider)[found_node]
                        line_num = pos.start.line
                        col_num = pos.start.column
                    except (KeyError, AttributeError):
                        # Fall back to text match position
                        line_num = match.line_number
                        col_num = match.column

                    ref = Reference(
                        file_path=match.file_path,
                        line_number=line_num,
                        column=col_num,
                        node=found_node,
                        parent=module,  # Simplified - could track actual parent
                        module=module,
                        context=context,
                        symbol=symbol,
                        containing_class=None,  # Could be enhanced to track this
                        containing_function=None,  # Could be enhanced to track this
                        attribute_chain=None,  # Could be enhanced to extract chain
                        source_line=match.line,
                        metadata={},
                    )
                    references.append(ref)

            except Exception as e:
                # Fail-fast: raise on any error
                raise RuntimeError(
                    f"Error processing {match.file_path}:{match.line_number}: {e}"
                ) from e

        return references

    def update_all(
        self,
        symbol: str,
        context: SymbolContext,
        transformer: Callable[[cst.CSTNode, Reference], cst.CSTNode],
        on_object: str | None = None,
    ) -> UpdateResult:
        """Find and transform all matching references.

        Args:
            symbol: The symbol name to update
            context: The context type to match
            transformer: Function to transform each matching node
            on_object: Optional object name to filter on

        Returns:
            UpdateResult with files modified and count of references updated

        Raises:
            RuntimeError: If search, parsing, or transformation fails
        """
        # Find all references
        references = self.find_references(symbol, context, on_object)

        if not references:
            return UpdateResult(files_modified=[], references_updated=0)

        # Group references by file
        refs_by_file: dict[Path, list[Reference]] = {}
        for ref in references:
            if ref.file_path not in refs_by_file:
                refs_by_file[ref.file_path] = []
            refs_by_file[ref.file_path].append(ref)

        # Transform each file
        modified_files = []
        total_updated = 0

        for file_path, file_refs in refs_by_file.items():
            try:
                # Parse the file
                source_code = file_path.read_text()
                module = cst.parse_module(source_code)

                # Apply transformations using metadata wrapper
                wrapper = MetadataWrapper(module)
                updater_visitor = UpdaterTransformer(file_refs, transformer)
                modified_module = wrapper.visit(updater_visitor)

                # Write back if changed
                if modified_module != module:
                    file_path.write_text(modified_module.code)
                    modified_files.append(file_path)
                    total_updated += len(file_refs)

            except Exception as e:
                raise RuntimeError(f"Error updating {file_path}: {e}") from e

        return UpdateResult(files_modified=modified_files, references_updated=total_updated)


class NodeFinder(cst.CSTVisitor):
    """Visitor to find nodes at a specific line matching a pattern."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self, target_line: int, symbol: str, validator: Any, on_object: str | None = None
    ) -> None:
        """Initialize the finder.

        Args:
            target_line: Line number to search on (1-indexed)
            symbol: Symbol name to find
            validator: Validator to check if nodes match
            on_object: Optional object name to filter on
        """
        super().__init__()
        self.target_line = target_line
        self.symbol = symbol
        self.validator = validator
        self.on_object = on_object
        self.found_nodes: list[cst.CSTNode] = []

    def on_visit(self, node: cst.CSTNode) -> bool:
        """Visit a node and check if it's on the target line."""
        # Check if node matches the pattern
        if self.validator.matches(node, self.symbol, self.on_object):
            # Try to get position metadata
            try:
                pos = self.get_metadata(PositionProvider, node)
                if pos.start.line == self.target_line:
                    self.found_nodes.append(node)
            except KeyError:
                # Metadata not available, fall back to adding all matches
                # (this is less precise but works for simple cases)
                self.found_nodes.append(node)
        return True


class UpdaterTransformer(cst.CSTTransformer):
    """Transformer to update specific nodes in a module."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self,
        references: list[Reference],
        transformer: Callable[[cst.CSTNode, Reference], cst.CSTNode],
    ) -> None:
        """Initialize the transformer.

        Args:
            references: List of references to transform
            transformer: Function to apply to each matching node
        """
        super().__init__()
        self.references = references
        self.transformer = transformer
        # Build a dict of (line, column) -> reference for position-based lookup
        self.positions_to_transform = {(ref.line_number, ref.column): ref for ref in references}

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        """Check if this attribute node should be transformed."""
        result = self._check_and_transform(original_node, updated_node)
        return result if isinstance(result, cst.BaseExpression) else updated_node

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Check if this call node should be transformed."""
        result = self._check_and_transform(original_node, updated_node)
        return result if isinstance(result, cst.BaseExpression) else updated_node

    def _check_and_transform(
        self, original_node: cst.CSTNode, updated_node: cst.CSTNode
    ) -> cst.CSTNode:
        """Check if a node should be transformed based on position."""
        try:
            pos = self.get_metadata(PositionProvider, original_node)
            key = (pos.start.line, pos.start.column)
            if key in self.positions_to_transform:
                ref = self.positions_to_transform[key]
                return self.transformer(updated_node, ref)
        except KeyError:
            # No metadata available or not in positions to transform
            pass
        return updated_node
