"""Pluggable search backends for finding code references.

This module provides different search implementations for finding text patterns
in Python files. It supports multiple backends (ripgrep, ag, grep, Python) and
automatically selects the fastest available tool.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class TextMatch:
    """Represents a single text match in a file.

    Attributes:
        file_path: Path to the file containing the match
        line_number: Line number where the match was found (1-indexed)
        column: Column number where the match starts (0-indexed)
        text: The matched text
        line: The full line of text containing the match
    """

    file_path: Path
    line_number: int
    column: int
    text: str
    line: str


@runtime_checkable
class ReferenceSearcher(Protocol):
    """Protocol for search backends that find text patterns in files."""

    def search(self, pattern: str, directory: Path) -> list[TextMatch]:
        """Search for a pattern in all Python files within a directory.

        Args:
            pattern: The text pattern to search for
            directory: The directory to search in

        Returns:
            List of TextMatch objects representing all matches found
        """
        ...

    def is_available(self) -> bool:
        """Check if this search backend is available on the system.

        Returns:
            True if the backend can be used, False otherwise
        """
        ...


class RipgrepSearcher:
    """Search backend using ripgrep (rg) for fast text searching."""

    def is_available(self) -> bool:
        """Check if ripgrep is installed."""
        return shutil.which("rg") is not None

    def search(self, pattern: str, directory: Path) -> list[TextMatch]:
        """Search using ripgrep."""
        if not self.is_available():
            raise RuntimeError("ripgrep (rg) is not available")

        try:
            # Use ripgrep with line numbers and column numbers
            result = subprocess.run(
                [
                    "rg",
                    "--line-number",
                    "--column",
                    "--no-heading",
                    "--type",
                    "py",
                    "--fixed-strings",
                    pattern,
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )

            matches = []
            for line in result.stdout.splitlines():
                # Format: filename:line:column:text
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    file_path = directory / parts[0]
                    line_number = int(parts[1])
                    column = int(parts[2]) - 1  # rg uses 1-indexed columns
                    full_line = parts[3]

                    matches.append(
                        TextMatch(
                            file_path=file_path,
                            line_number=line_number,
                            column=column,
                            text=pattern,
                            line=full_line,
                        )
                    )

            return matches
        except Exception as e:
            raise RuntimeError(f"ripgrep search failed: {e}") from e


class AgSearcher:
    """Search backend using The Silver Searcher (ag)."""

    def is_available(self) -> bool:
        """Check if ag is installed."""
        return shutil.which("ag") is not None

    def search(self, pattern: str, directory: Path) -> list[TextMatch]:
        """Search using ag."""
        if not self.is_available():
            raise RuntimeError("ag (The Silver Searcher) is not available")

        try:
            # Use ag with line numbers and column numbers
            result = subprocess.run(
                ["ag", "--line-numbers", "--column", "--nogroup", "--python", "--literal", pattern],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )

            matches = []
            for line in result.stdout.splitlines():
                # Format: filename:line:column:text
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    file_path = directory / parts[0]
                    line_number = int(parts[1])
                    column = int(parts[2]) - 1  # ag uses 1-indexed columns
                    full_line = parts[3]

                    matches.append(
                        TextMatch(
                            file_path=file_path,
                            line_number=line_number,
                            column=column,
                            text=pattern,
                            line=full_line,
                        )
                    )

            return matches
        except Exception as e:
            raise RuntimeError(f"ag search failed: {e}") from e


class GrepSearcher:
    """Search backend using standard grep."""

    def is_available(self) -> bool:
        """Check if grep is installed."""
        return shutil.which("grep") is not None

    def search(self, pattern: str, directory: Path) -> list[TextMatch]:
        """Search using grep."""
        if not self.is_available():
            raise RuntimeError("grep is not available")

        try:
            # Use grep with line numbers, recursive, only Python files
            result = subprocess.run(
                [
                    "grep",
                    "-n",
                    "-r",
                    "--include=*.py",
                    "-F",  # Fixed string (literal)
                    pattern,
                    str(directory),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            matches = []
            for line in result.stdout.splitlines():
                # Format: filename:line:text
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path = Path(parts[0])
                    line_number = int(parts[1])
                    full_line = parts[2]

                    # Find column by searching for pattern in line
                    column = full_line.find(pattern)
                    if column == -1:
                        column = 0

                    matches.append(
                        TextMatch(
                            file_path=file_path,
                            line_number=line_number,
                            column=column,
                            text=pattern,
                            line=full_line,
                        )
                    )

            return matches
        except Exception as e:
            raise RuntimeError(f"grep search failed: {e}") from e


class PythonSearcher:
    """Fallback search backend using pure Python."""

    def is_available(self) -> bool:
        """Python searcher is always available."""
        return True

    def search(self, pattern: str, directory: Path) -> list[TextMatch]:
        """Search using pure Python."""
        matches = []

        # Find all .py files recursively
        for py_file in directory.rglob("*.py"):
            if not py_file.is_file():
                continue

            try:
                content = py_file.read_text()
                lines = content.splitlines()

                for line_num, line in enumerate(lines, start=1):
                    # Find all occurrences of pattern in this line
                    column = 0
                    while True:
                        index = line.find(pattern, column)
                        if index == -1:
                            break

                        matches.append(
                            TextMatch(
                                file_path=py_file,
                                line_number=line_num,
                                column=index,
                                text=pattern,
                                line=line,
                            )
                        )

                        # Move past this match to find additional matches on same line
                        column = index + 1

            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        return matches


def get_best_searcher() -> ReferenceSearcher:
    """Auto-detect and return the fastest available search backend.

    Priority order:
    1. ripgrep (fastest)
    2. ag (The Silver Searcher)
    3. grep
    4. Python (fallback, always available)

    Returns:
        The best available ReferenceSearcher implementation
    """
    searchers: list[ReferenceSearcher] = [
        RipgrepSearcher(),
        AgSearcher(),
        GrepSearcher(),
        PythonSearcher(),
    ]

    for searcher in searchers:
        if searcher.is_available():
            return searcher

    # This should never happen since PythonSearcher is always available
    return PythonSearcher()
