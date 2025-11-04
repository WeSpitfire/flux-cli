#!/usr/bin/env python3
"""Test file caching in workflow system."""

import asyncio
from pathlib import Path
from flux.core.workflow import WorkflowEnforcer
from flux.tools.file_ops import ReadFilesTool


async def test_file_caching():
    """Test that file reading uses cache on second read."""

    print("=" * 60)
    print("Testing File Caching Feature")
    print("=" * 60)

    # Setup
    cwd = Path.cwd()
    workflow = WorkflowEnforcer(cwd)
    workflow.start_workflow()

    reader = ReadFilesTool(cwd, workflow_enforcer=workflow)

    # Test file
    test_file = "flux/core/workflow.py"

    print(f"\n📖 First read of {test_file}...")
    result1 = await reader.execute([test_file])

    if test_file in result1:
        first_read = result1[test_file]
        is_cached_1 = first_read.get('cached', False)
        lines_1 = first_read.get('lines', 0)

        print(f"   ✓ Read successful")
        print(f"   - Lines: {lines_1}")
        print(f"   - Cached: {is_cached_1}")

        if is_cached_1:
            print("   ❌ ERROR: First read should NOT be cached!")
            return False
    else:
        print(f"   ❌ ERROR: {result1}")
        return False

    print(f"\n📖 Second read of {test_file} (should use cache)...")
    result2 = await reader.execute([test_file])

    if test_file in result2:
        second_read = result2[test_file]
        is_cached_2 = second_read.get('cached', False)
        lines_2 = second_read.get('lines', 0)

        print(f"   ✓ Read successful")
        print(f"   - Lines: {lines_2}")
        print(f"   - Cached: {is_cached_2}")

        if not is_cached_2:
            print("   ❌ ERROR: Second read should be cached!")
            return False

        if lines_1 != lines_2:
            print(f"   ❌ ERROR: Line counts don't match! {lines_1} vs {lines_2}")
            return False
    else:
        print(f"   ❌ ERROR: {result2}")
        return False

    # Check workflow state
    print("\n📊 Workflow State:")
    print(f"   - Files in cache: {len(workflow.context.file_cache)}")
    print(f"   - Files read: {len(workflow.context.files_read)}")

    if len(workflow.context.file_cache) != 1:
        print(f"   ❌ ERROR: Expected 1 file in cache, got {len(workflow.context.file_cache)}")
        return False

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\n🎉 File caching is working correctly!")
    print("\nBenefits:")
    print("  • Reduces disk I/O when reading same file multiple times")
    print("  • Speeds up workflows that need to re-read files")
    print("  • Cache is per-workflow and automatically cleared")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_file_caching())
    exit(0 if success else 1)
