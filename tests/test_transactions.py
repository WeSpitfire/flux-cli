#!/usr/bin/env python3
"""Test file transaction manager."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flux.core.file_transaction import FileTransaction


def test_successful_transaction():
    """Test that successful transaction commits changes."""
    print("\n=== Test 1: Successful Transaction ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)

        # Create test files
        (cwd / "a.txt").write_text("file a")
        (cwd / "b.txt").write_text("file b")

        # Execute transaction
        with FileTransaction(cwd) as txn:
            txn.write("c.txt", "new file c")
            txn.edit("a.txt", "file a", "modified a")
            txn.delete("b.txt")

        # Verify changes persisted
        if (cwd / "c.txt").exists() and (cwd / "c.txt").read_text() == "new file c":
            if (cwd / "a.txt").read_text() == "modified a":
                if not (cwd / "b.txt").exists():
                    print("✅ Transaction committed successfully")
                    return True

    print("❌ Transaction did not commit correctly")
    return False


def test_failed_transaction_rollback():
    """Test that failed transaction rolls back all changes."""
    print("\n=== Test 2: Failed Transaction Rollback ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)

        # Create test files
        (cwd / "a.txt").write_text("original a")
        (cwd / "b.txt").write_text("original b")

        # Execute transaction that will fail
        try:
            with FileTransaction(cwd) as txn:
                txn.write("c.txt", "new file c")
                txn.edit("a.txt", "original a", "modified a")
                txn.delete("b.txt")

                # Cause failure
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected

        # Verify rollback occurred
        if not (cwd / "c.txt").exists():
            if (cwd / "a.txt").read_text() == "original a":
                if (cwd / "b.txt").exists() and (cwd / "b.txt").read_text() == "original b":
                    print("✅ Transaction rolled back successfully")
                    return True

        print("❌ Transaction did not rollback correctly")
        print(f"   c.txt exists: {(cwd / 'c.txt').exists()}")
        print(f"   a.txt content: {(cwd / 'a.txt').read_text()}")
        print(f"   b.txt exists: {(cwd / 'b.txt').exists()}")
        return False


def test_move_operation():
    """Test move operation in transaction."""
    print("\n=== Test 3: Move Operation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)

        # Create test file
        (cwd / "source.txt").write_text("content")

        # Move file
        with FileTransaction(cwd) as txn:
            txn.move("source.txt", "dest.txt")

        # Verify move
        if not (cwd / "source.txt").exists():
            if (cwd / "dest.txt").exists() and (cwd / "dest.txt").read_text() == "content":
                print("✅ Move operation successful")
                return True

        print("❌ Move operation failed")
        return False


def test_move_rollback():
    """Test move operation rollback."""
    print("\n=== Test 4: Move Rollback ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)

        # Create test file
        (cwd / "source.txt").write_text("content")

        # Failed move transaction
        try:
            with FileTransaction(cwd) as txn:
                txn.move("source.txt", "dest.txt")
                raise ValueError("Fail after move")
        except ValueError:
            pass

        # Verify rollback - source restored, dest removed
        if (cwd / "source.txt").exists() and (cwd / "source.txt").read_text() == "content":
            if not (cwd / "dest.txt").exists():
                print("✅ Move rollback successful")
                return True

        print("❌ Move rollback failed")
        print(f"   source exists: {(cwd / 'source.txt').exists()}")
        print(f"   dest exists: {(cwd / 'dest.txt').exists()}")
        return False


def test_transaction_summary():
    """Test transaction summary."""
    print("\n=== Test 5: Transaction Summary ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)

        (cwd / "a.txt").write_text("a")
        (cwd / "b.txt").write_text("b")

        with FileTransaction(cwd) as txn:
            txn.write("c.txt", "c")
            txn.edit("a.txt", "a", "modified")
            txn.delete("b.txt")

            summary = txn.get_summary()

            if summary["total_operations"] == 3:
                if summary["executed"] == 3:
                    print("✅ Transaction summary correct")
                    print(f"   Operations: {summary['total_operations']}")
                    print(f"   Executed: {summary['executed']}")
                    return True

        print("❌ Transaction summary incorrect")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing File Transaction Manager\n")

    tests = [
        test_successful_transaction(),
        test_failed_transaction_rollback(),
        test_move_operation(),
        test_move_rollback(),
        test_transaction_summary()
    ]

    print("\n" + "=" * 50)
    passed = sum(tests)
    total = len(tests)

    if passed == total:
        print(f"✅ All {total} tests passed!")
        return 0
    else:
        print(f"❌ {total - passed}/{total} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
