#!/usr/bin/env python3
"""Test script to verify the Flux fixes work correctly."""

import asyncio
import tempfile
from pathlib import Path
import sys

# Add flux to path
sys.path.insert(0, str(Path(__file__).parent))

from flux.tools.file_ops import WriteFileTool, MoveFileTool, DeleteFileTool


async def test_syntax_error_prevention():
    """Test that write_file prevents syntax errors."""
    print("\n=== Test 1: Syntax Error Prevention ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        tool = WriteFileTool(cwd)
        
        # Try to write invalid Python
        result = await tool.execute(
            path="test.py",
            content="# Bad Python\ninvalid syntax here"
        )
        
        if "error" in result:
            print("✅ Syntax error correctly detected and prevented")
            print(f"   Error: {result['error']}")
            return True
        else:
            print("❌ Syntax error was NOT caught!")
            print(f"   Result: {result}")
            return False


async def test_move_file():
    """Test that move_file works correctly."""
    print("\n=== Test 2: Move File ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        
        # Create a source file
        source = cwd / "source.py"
        source.write_text("# Valid Python\nprint('hello')\n")
        
        tool = MoveFileTool(cwd)
        
        # Move it
        result = await tool.execute(
            source="source.py",
            destination="dest.py"
        )
        
        if result.get("success"):
            dest = cwd / "dest.py"
            if dest.exists() and not source.exists():
                content = dest.read_text()
                if "hello" in content:
                    print("✅ File moved correctly with actual content")
                    return True
                else:
                    print("❌ File content was not preserved!")
                    print(f"   Content: {content}")
                    return False
            else:
                print("❌ File system state incorrect after move")
                print(f"   Source exists: {source.exists()}")
                print(f"   Dest exists: {dest.exists()}")
                return False
        else:
            print("❌ Move failed!")
            print(f"   Result: {result}")
            return False


async def test_move_prevents_syntax_errors():
    """Test that move_file validates destination."""
    print("\n=== Test 3: Move Validates Syntax ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        
        # Create a source file with bad Python
        source = cwd / "bad.py"
        source.write_text("invalid python syntax")
        
        tool = MoveFileTool(cwd)
        
        # Try to move it
        result = await tool.execute(
            source="bad.py",
            destination="moved.py"
        )
        
        if "error" in result and "syntax" in result["error"].lower():
            if source.exists():
                print("✅ Syntax error detected, source preserved")
                return True
            else:
                print("❌ Source was deleted despite syntax error!")
                return False
        else:
            print("❌ Syntax error was NOT caught!")
            print(f"   Result: {result}")
            return False


async def test_delete_file():
    """Test that delete_file works correctly."""
    print("\n=== Test 4: Delete File ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        
        # Create a file
        test_file = cwd / "delete_me.py"
        test_file.write_text("# To be deleted\n")
        
        tool = DeleteFileTool(cwd)
        
        # Delete it
        result = await tool.execute(path="delete_me.py")
        
        if result.get("success") and not test_file.exists():
            print("✅ File deleted correctly")
            return True
        else:
            print("❌ Delete failed!")
            print(f"   Result: {result}")
            print(f"   File exists: {test_file.exists()}")
            return False


async def main():
    """Run all tests."""
    print("🧪 Testing Flux Fixes\n")
    
    tests = [
        test_syntax_error_prevention(),
        test_move_file(),
        test_move_prevents_syntax_errors(),
        test_delete_file()
    ]
    
    results = await asyncio.gather(*tests)
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests passed!")
        return 0
    else:
        print(f"❌ {total - passed}/{total} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
