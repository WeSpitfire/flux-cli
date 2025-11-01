"""Test WriteFileTool path handling fix."""

import asyncio
from pathlib import Path
from flux.tools.file_ops import WriteFileTool


async def test_write_file_paths():
    """Test various path scenarios."""
    cwd = Path("/Users/developer/SynologyDrive/flux-cli")
    tool = WriteFileTool(cwd)
    
    print("Testing WriteFileTool path handling...\n")
    
    # Test 1: Simple relative path
    print("Test 1: Simple relative path")
    result = await tool.execute(
        path="test_output1.txt",
        content="Test content 1"
    )
    print(f"  Path: test_output1.txt")
    print(f"  Result: {result['path']}")
    expected = str(cwd / "test_output1.txt")
    assert result['path'] == expected, f"Expected {expected}, got {result['path']}"
    print("  ✓ PASS\n")
    
    # Test 2: Nested relative path
    print("Test 2: Nested relative path")
    result = await tool.execute(
        path="test_dir/test_output2.txt",
        content="Test content 2"
    )
    print(f"  Path: test_dir/test_output2.txt")
    print(f"  Result: {result['path']}")
    expected = str(cwd / "test_dir/test_output2.txt")
    assert result['path'] == expected, f"Expected {expected}, got {result['path']}"
    print("  ✓ PASS\n")
    
    # Test 3: With deprecated target_dir (should ignore it now)
    print("Test 3: With deprecated target_dir parameter")
    result = await tool.execute(
        path="flux/core/test_output3.txt",
        content="Test content 3",
        target_dir="flux/core"  # This should be ignored
    )
    print(f"  Path: flux/core/test_output3.txt")
    print(f"  Target dir (ignored): flux/core")
    print(f"  Result: {result['path']}")
    expected = str(cwd / "flux/core/test_output3.txt")
    assert result['path'] == expected, f"Expected {expected}, got {result['path']}"
    # Make sure it didn't duplicate
    assert "flux/core/flux/core" not in result['path'], "Path was duplicated!"
    print("  ✓ PASS - No duplication!\n")
    
    # Cleanup
    import os
    for f in ["test_output1.txt", "test_dir/test_output2.txt", "flux/core/test_output3.txt"]:
        try:
            os.remove(cwd / f)
        except:
            pass
    try:
        os.rmdir(cwd / "test_dir")
    except:
        pass
    
    print("="*60)
    print("✅ All path handling tests PASSED!")
    print("="*60)
    print("\nFix verified:")
    print("  - Simple paths work correctly")
    print("  - Nested paths work correctly")
    print("  - No path duplication with target_dir")
    print("  - target_dir parameter now safely ignored")


if __name__ == "__main__":
    asyncio.run(test_write_file_paths())
