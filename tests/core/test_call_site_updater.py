"""Tests for CallSiteUpdater."""

from pathlib import Path

import libcst as cst

from molting.core.call_site_updater import CallSiteUpdater, Reference, UpdateResult
from molting.core.reference_searcher import PythonSearcher
from molting.core.symbol_context import SymbolContext


class TestCallSiteUpdater:
    """Tests for the CallSiteUpdater class."""

    def test_init_with_custom_searcher(self, tmp_path: Path) -> None:
        """Test initializing with a custom searcher."""
        searcher = PythonSearcher()
        updater = CallSiteUpdater(tmp_path, searcher=searcher)
        assert updater.directory == tmp_path
        assert updater.searcher == searcher

    def test_init_auto_detects_searcher(self, tmp_path: Path) -> None:
        """Test auto-detecting searcher when not provided."""
        updater = CallSiteUpdater(tmp_path)
        assert updater.directory == tmp_path
        assert updater.searcher is not None
        assert updater.searcher.is_available()

    def test_find_references_attribute_access(self, tmp_path: Path) -> None:
        """Test finding attribute access references."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """class Person:
    def __init__(self, dept):
        self.department = dept

def process(person):
    mgr = person.department.manager
    return mgr
"""
        )

        updater = CallSiteUpdater(tmp_path)
        refs = updater.find_references("manager", SymbolContext.ATTRIBUTE_ACCESS)

        assert len(refs) == 1
        assert isinstance(refs[0], Reference)
        assert refs[0].symbol == "manager"
        assert refs[0].context == SymbolContext.ATTRIBUTE_ACCESS
        assert refs[0].file_path == test_file
        assert refs[0].line_number == 6

    def test_find_references_method_call(self, tmp_path: Path) -> None:
        """Test finding method call references."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """def process(person):
    result = person.get_manager()
    return result
"""
        )

        updater = CallSiteUpdater(tmp_path)
        refs = updater.find_references("get_manager", SymbolContext.METHOD_CALL, on_object="person")

        assert len(refs) == 1
        assert refs[0].symbol == "get_manager"
        assert refs[0].context == SymbolContext.METHOD_CALL
        assert refs[0].line_number == 2

    def test_find_references_multiple_files(self, tmp_path: Path) -> None:
        """Test finding references across multiple files."""
        file1 = tmp_path / "file1.py"
        file1.write_text("x = person.department.manager\n")

        file2 = tmp_path / "file2.py"
        file2.write_text("y = emp.department.manager\n")

        updater = CallSiteUpdater(tmp_path)
        refs = updater.find_references("manager", SymbolContext.ATTRIBUTE_ACCESS)

        assert len(refs) == 2
        file_paths = {ref.file_path for ref in refs}
        assert file1 in file_paths
        assert file2 in file_paths

    def test_find_references_no_matches(self, tmp_path: Path) -> None:
        """Test finding references when none exist."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    return None\n")

        updater = CallSiteUpdater(tmp_path)
        refs = updater.find_references("nonexistent", SymbolContext.ATTRIBUTE_ACCESS)

        assert len(refs) == 0

    def test_update_all_transforms_references(self, tmp_path: Path) -> None:
        """Test updating all references with a transformer."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """def process(person):
    mgr = person.department.manager
    return mgr.name
"""
        )

        def transformer(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform person.department.manager to person.get_manager()."""
            if isinstance(node, cst.Attribute):
                # Get the base object (person.department)
                if isinstance(node.value, cst.Attribute):
                    # Get 'person'
                    base = node.value.value
                    return cst.Call(
                        func=cst.Attribute(value=base, attr=cst.Name("get_manager")), args=[]
                    )
            return node

        updater = CallSiteUpdater(tmp_path)
        result = updater.update_all("manager", SymbolContext.ATTRIBUTE_ACCESS, transformer)

        assert isinstance(result, UpdateResult)
        assert len(result.files_modified) == 1
        assert test_file in result.files_modified
        assert result.references_updated == 1

        # Verify the file was actually modified
        modified_content = test_file.read_text()
        assert "person.get_manager()" in modified_content
        assert "person.department.manager" not in modified_content

    def test_update_all_multiple_references_same_file(self, tmp_path: Path) -> None:
        """Test updating multiple references in the same file."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """def process(person, employee):
    mgr1 = person.department.manager
    mgr2 = employee.department.manager
    return mgr1, mgr2
"""
        )

        def transformer(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform x.department.manager to x.get_manager()."""
            if isinstance(node, cst.Attribute):
                if isinstance(node.value, cst.Attribute):
                    base = node.value.value
                    return cst.Call(
                        func=cst.Attribute(value=base, attr=cst.Name("get_manager")), args=[]
                    )
            return node

        updater = CallSiteUpdater(tmp_path)
        result = updater.update_all("manager", SymbolContext.ATTRIBUTE_ACCESS, transformer)

        assert result.references_updated == 2
        modified_content = test_file.read_text()
        assert "person.get_manager()" in modified_content
        assert "employee.get_manager()" in modified_content

    def test_update_all_no_matches(self, tmp_path: Path) -> None:
        """Test updating when no matches exist."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    return None\n")

        def transformer(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            return node

        updater = CallSiteUpdater(tmp_path)
        result = updater.update_all("nonexistent", SymbolContext.ATTRIBUTE_ACCESS, transformer)

        assert result.references_updated == 0
        assert len(result.files_modified) == 0


class TestReference:
    """Tests for the Reference dataclass."""

    def test_reference_creation(self, tmp_path: Path) -> None:
        """Test creating a Reference instance."""
        test_file = tmp_path / "test.py"
        module = cst.parse_module("x = person.department")
        node = module.body[0].body[0].value

        ref = Reference(
            file_path=test_file,
            line_number=1,
            column=4,
            node=node,
            parent=module.body[0],
            module=module,
            context=SymbolContext.ATTRIBUTE_ACCESS,
            symbol="department",
            containing_class=None,
            containing_function="foo",
            attribute_chain=["person", "department"],
            source_line="x = person.department",
            metadata={},
        )

        assert ref.file_path == test_file
        assert ref.line_number == 1
        assert ref.symbol == "department"
        assert ref.context == SymbolContext.ATTRIBUTE_ACCESS
        assert ref.containing_function == "foo"


class TestUpdateResult:
    """Tests for the UpdateResult dataclass."""

    def test_update_result_creation(self, tmp_path: Path) -> None:
        """Test creating an UpdateResult instance."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        result = UpdateResult(files_modified=[file1, file2], references_updated=5)

        assert len(result.files_modified) == 2
        assert file1 in result.files_modified
        assert file2 in result.files_modified
        assert result.references_updated == 5
