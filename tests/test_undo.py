"""Test undo system functionality."""

import tempfile
from pathlib import Path
from flux.core.undo import UndoManager


def test_undo_system():
    """Test the undo system with various file operations."""

    # Create temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "test_project"
        project_root.mkdir()

        flux_dir = Path(tmpdir) / ".flux"
        flux_dir.mkdir()

        # Initialize undo manager
        undo = UndoManager(flux_dir, project_root)

        print("Testing undo system...")
        print(f"Project: {project_root}")
        print(f"Flux dir: {flux_dir}")
        print()

        # Test 1: Create new file
        print("Test 1: Create new file")
        test_file = project_root / "test.txt"
        test_file.write_text("Hello, World!")

        undo.snapshot_operation(
            operation="write",
            file_path=test_file,
            old_content=None,
            new_content="Hello, World!",
            description="Created test.txt"
        )

        history = undo.get_history()
        print(f"  History entries: {len(history)}")
        assert len(history) == 1
        assert history[0]["operation"] == "write"
        print("  ✓ Snapshot recorded")
        print()

        # Test 2: Edit file
        print("Test 2: Edit file")
        old_content = test_file.read_text()
        new_content = "Hello, Flux!"
        test_file.write_text(new_content)

        undo.snapshot_operation(
            operation="edit",
            file_path=test_file,
            old_content=old_content,
            new_content=new_content,
            description="Edited test.txt"
        )

        history = undo.get_history()
        print(f"  History entries: {len(history)}")
        assert len(history) == 2
        assert test_file.read_text() == "Hello, Flux!"
        print("  ✓ Edit snapshot recorded")
        print()

        # Test 3: Undo edit
        print("Test 3: Undo last edit")
        result = undo.undo_last()
        print(f"  Result: {result}")
        assert result["success"]
        assert result["action"] == "restored"
        assert test_file.read_text() == "Hello, World!"
        print("  ✓ File restored to previous content")
        print()

        # Test 4: Undo creation (delete file)
        print("Test 4: Undo file creation")
        result = undo.undo_last()
        print(f"  Result: {result}")
        assert result["success"]
        assert result["action"] == "deleted"
        assert not test_file.exists()
        print("  ✓ File deleted")
        print()

        # Test 5: No more undos
        print("Test 5: No more operations to undo")
        result = undo.undo_last()
        print(f"  Result: {result}")
        assert "error" in result
        print("  ✓ Error returned correctly")
        print()

        # Test 6: Persistence
        print("Test 6: Test persistence")
        test_file2 = project_root / "test2.txt"
        test_file2.write_text("Persistence test")
        undo.snapshot_operation(
            operation="write",
            file_path=test_file2,
            old_content=None,
            new_content="Persistence test",
            description="Created test2.txt"
        )

        # Create new undo manager instance (simulates reopening)
        undo2 = UndoManager(flux_dir, project_root)
        history = undo2.get_history()
        print(f"  History entries after reload: {len(history)}")
        assert len(history) == 1
        print("  ✓ History persisted across instances")
        print()

        # Test 7: AST edit operation
        print("Test 7: AST edit operation")
        py_file = project_root / "test.py"
        old_py = "def foo():\n    pass\n"
        new_py = "def foo():\n    return 42\n"
        py_file.write_text(old_py)

        undo2.snapshot_operation(
            operation="ast_edit",
            file_path=py_file,
            old_content=old_py,
            new_content=new_py,
            description="Modified foo function"
        )
        py_file.write_text(new_py)

        result = undo2.undo_last()
        print(f"  Result: {result}")
        assert result["success"]
        assert py_file.read_text() == old_py
        print("  ✓ AST edit undone successfully")
        print()

        print("=" * 50)
        print("All tests passed! ✓")


if __name__ == "__main__":
    test_undo_system()
