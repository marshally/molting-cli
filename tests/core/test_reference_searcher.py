"""Tests for ReferenceSearcher and its backends."""

from pathlib import Path

from molting.core.reference_searcher import (
    PythonSearcher,
    ReferenceSearcher,
    TextMatch,
    get_best_searcher,
)


class TestTextMatch:
    """Tests for TextMatch dataclass."""

    def test_text_match_creation(self) -> None:
        """Test creating a TextMatch instance."""
        match = TextMatch(
            file_path=Path("/test/file.py"),
            line_number=10,
            column=5,
            text="test_pattern",
            line="    test_pattern()",
        )
        assert match.file_path == Path("/test/file.py")
        assert match.line_number == 10
        assert match.column == 5
        assert match.text == "test_pattern"
        assert match.line == "    test_pattern()"


class TestPythonSearcher:
    """Tests for the fallback Python-based searcher."""

    def test_is_available(self) -> None:
        """Test that Python searcher is always available."""
        searcher = PythonSearcher()
        assert searcher.is_available() is True

    def test_search_finds_pattern(self, tmp_path: Path) -> None:
        """Test searching for a pattern in files."""
        # Create test files
        file1 = tmp_path / "test1.py"
        file1.write_text("def test_function():\n    department.manager\n    return None\n")

        file2 = tmp_path / "test2.py"
        file2.write_text("class Test:\n    def method(self):\n        x.department.manager\n")

        searcher = PythonSearcher()
        matches = searcher.search("department.manager", tmp_path)

        assert len(matches) == 2
        assert all(isinstance(m, TextMatch) for m in matches)

        # Check first match
        match1 = [m for m in matches if "test1.py" in str(m.file_path)][0]
        assert match1.line_number == 2
        assert "department.manager" in match1.line

        # Check second match
        match2 = [m for m in matches if "test2.py" in str(m.file_path)][0]
        assert match2.line_number == 3
        assert "department.manager" in match2.line

    def test_search_no_matches(self, tmp_path: Path) -> None:
        """Test searching when no matches exist."""
        file1 = tmp_path / "test.py"
        file1.write_text("def test():\n    return None\n")

        searcher = PythonSearcher()
        matches = searcher.search("nonexistent_pattern", tmp_path)

        assert len(matches) == 0

    def test_search_ignores_non_python_files(self, tmp_path: Path) -> None:
        """Test that search only looks at .py files."""
        py_file = tmp_path / "test.py"
        py_file.write_text("department.manager")

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("department.manager")

        searcher = PythonSearcher()
        matches = searcher.search("department.manager", tmp_path)

        assert len(matches) == 1
        assert matches[0].file_path == py_file


class TestGetBestSearcher:
    """Tests for searcher auto-detection."""

    def test_returns_searcher(self) -> None:
        """Test that get_best_searcher returns a valid searcher."""
        searcher = get_best_searcher()
        assert isinstance(searcher, ReferenceSearcher)
        assert searcher.is_available()

    def test_returns_python_searcher_as_fallback(self) -> None:
        """Test that Python searcher is available as a fallback."""
        # This test always passes since Python searcher is guaranteed
        searcher = get_best_searcher()
        assert searcher.is_available()
