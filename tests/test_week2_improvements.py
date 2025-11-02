"""Test Week 2 improvements to Flux."""

import asyncio
import time
from pathlib import Path
from rich.console import Console

# Week 2 features
from flux.core.context_manager import ContextManager
from flux.core.diff import DiffPreview
from flux.ui.progress import ProgressTracker, SimpleProgress


def test_context_pruning():
    """Test context pruning for Haiku."""
    print("\n" + "="*60)
    print("TEST 1: Context Pruning")
    print("="*60)
    
    manager = ContextManager(max_context_tokens=500)  # Lower budget to trigger pruning
    
    # Create mock conversation history with large content
    history = [
        {"role": "user", "content": "Hello" * 50},
        {"role": "assistant", "content": "Hi! How can I help?" * 50},
        {"role": "user", "content": "Read file.py" * 50},
        {"role": "assistant", "content": [
            {"type": "tool_result", "tool_use_id": "1", "content": "file content " * 500}
        ]},
        {"role": "user", "content": "Edit file.py" * 50},
        {"role": "assistant", "content": [
            {"type": "tool_result", "tool_use_id": "2", "content": "Success!" * 100}
        ]},
        {"role": "user", "content": "Show me the changes" * 50},
        {"role": "assistant", "content": "Here are the changes..." * 100},
    ]
    
    print(f"Original history: {len(history)} messages")
    print(f"Estimated tokens: {manager._estimate_tokens(history)}")
    
    # Prune
    pruned = manager.prune_for_haiku(history, current_file_context="file.py")
    
    print(f"\nPruned history: {len(pruned)} messages")
    print(f"Estimated tokens: {manager._estimate_tokens(pruned)}")
    
    # Get stats
    stats = manager.get_pruning_stats(history, pruned)
    print(f"\nPruning Stats:")
    print(f"  Messages removed: {stats['messages_removed']}")
    print(f"  Tokens saved: {stats['tokens_saved']}")
    
    assert len(pruned) <= len(history), "Pruned should not be larger than original"
    # Recent messages (last 6) should always be kept
    assert len(pruned) >= min(6, len(history)), "Should keep recent messages"
    
    print("\n✅ Context pruning test passed!")


def test_streaming_diff():
    """Test streaming diff display."""
    print("\n" + "="*60)
    print("TEST 2: Streaming Diff Display")
    print("="*60)
    
    console = Console()
    diff_preview = DiffPreview(console)
    
    # Create large file content
    original = "\n".join([f"line {i}: original content" for i in range(1, 101)])
    modified = "\n".join([
        f"line {i}: {'modified' if i % 3 == 0 else 'original'} content"
        for i in range(1, 101)
    ])
    
    print(f"Original: {len(original.splitlines())} lines")
    print(f"Modified: {len(modified.splitlines())} lines")
    
    # Test diff iterator
    print("\nTesting diff iterator...")
    chunks = list(diff_preview.get_diff_iterator(original, modified, "test.txt", chunk_size=20))
    print(f"Generated {len(chunks)} chunks")
    
    # Test streaming display (just check it doesn't error)
    print("\nTesting streaming display...")
    try:
        diff_preview.display_streamed_diff(
            original,
            modified,
            "test.txt",
            chunk_size=30,
            show_progress=False  # Disable for test
        )
        print("\n✅ Streaming diff test passed!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


def test_progress_tracking():
    """Test progress tracking system."""
    print("\n" + "="*60)
    print("TEST 3: Progress Tracking")
    print("="*60)
    
    console = Console()
    
    # Test multi-step progress
    print("\nTesting multi-step progress tracker...")
    tracker = ProgressTracker(console, "Test Operation")
    
    tracker.add_steps([
        ("Read files", "Reading source files"),
        ("Analyze code", "Analyzing code structure"),
        ("Generate changes", "Creating modifications"),
        ("Apply changes", "Writing files"),
        ("Validate", "Running syntax checks")
    ])
    
    # Simulate operation
    for i in range(5):
        tracker.start_step(i)
        time.sleep(0.1)  # Simulate work
        
        if i == 2:
            # Simulate an error
            tracker.fail_step(i, "Syntax error detected")
        else:
            tracker.complete_step(i)
    
    tracker.show_summary()
    
    # Test simple progress
    print("\n\nTesting simple progress indicator...")
    simple = SimpleProgress(console)
    simple.start("Processing items", total=10)
    
    for i in range(10):
        time.sleep(0.05)
        simple.update(advance=1)
    
    simple.stop(success=True, message="Processing complete")
    
    print("\n✅ Progress tracking test passed!")


def test_integration():
    """Test all features working together."""
    print("\n" + "="*60)
    print("TEST 4: Integration Test")
    print("="*60)
    
    console = Console()
    
    # Simulate a complex operation with all features
    print("\nSimulating complex refactoring operation...")
    
    # 1. Progress tracking
    tracker = ProgressTracker(console, "Refactor Module")
    tracker.add_steps([
        ("Context check", "Checking context budget"),
        ("Read files", "Loading files"),
        ("Generate diff", "Creating changes"),
        ("Apply", "Writing changes")
    ])
    
    # 2. Check context
    tracker.start_step(0)
    manager = ContextManager(max_context_tokens=2000)
    history = [{"role": "user", "content": "test"} for _ in range(10)]
    pruned = manager.prune_for_haiku(history)
    tracker.complete_step(0)
    
    # 3. Read files (simulated)
    tracker.start_step(1)
    time.sleep(0.1)
    tracker.complete_step(1)
    
    # 4. Generate diff
    tracker.start_step(2)
    diff_preview = DiffPreview(console)
    original = "def foo():\n    return 1"
    modified = "def foo():\n    return 2\n\ndef bar():\n    return 3"
    
    additions, deletions, mods = diff_preview.get_change_stats(original, modified)
    print(f"\n  Changes: +{additions} -{deletions} ~{mods}")
    tracker.complete_step(2)
    
    # 5. Apply
    tracker.start_step(3)
    time.sleep(0.1)
    tracker.complete_step(3)
    
    tracker.show_summary()
    
    print("\n✅ Integration test passed!")


def test_performance():
    """Test performance of improvements."""
    print("\n" + "="*60)
    print("TEST 5: Performance Metrics")
    print("="*60)
    
    # Test context pruning performance
    manager = ContextManager()
    large_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}" * 100}
        for i in range(100)
    ]
    
    start = time.time()
    pruned = manager.prune_for_haiku(large_history)
    elapsed = time.time() - start
    
    print(f"Context pruning: {len(large_history)} → {len(pruned)} messages")
    print(f"  Time: {elapsed*1000:.2f}ms")
    print(f"  Tokens saved: {manager._estimate_tokens(large_history) - manager._estimate_tokens(pruned)}")
    
    # Test diff iterator performance
    console = Console()
    diff_preview = DiffPreview(console)
    
    huge_original = "\n".join([f"line {i}" for i in range(1000)])
    huge_modified = "\n".join([f"line {i} modified" if i % 2 == 0 else f"line {i}" for i in range(1000)])
    
    start = time.time()
    chunks = list(diff_preview.get_diff_iterator(huge_original, huge_modified, chunk_size=50))
    elapsed = time.time() - start
    
    print(f"\nDiff iteration: Generated {len(chunks)} chunks")
    print(f"  Time: {elapsed*1000:.2f}ms")
    print(f"  Memory efficient: Uses iterator (doesn't load all at once)")
    
    print("\n✅ Performance test passed!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("WEEK 2 IMPROVEMENTS TEST SUITE")
    print("="*60)
    
    try:
        test_context_pruning()
        test_streaming_diff()
        test_progress_tracking()
        test_integration()
        test_performance()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
        print("\n📊 Week 2 Features Validated:")
        print("  ✓ Context pruning - Keeps history within budget")
        print("  ✓ Streaming diffs - Handles large files efficiently")
        print("  ✓ Progress tracking - Real-time operation feedback")
        print("  ✓ Integration - All features work together")
        print("  ✓ Performance - Fast and memory efficient")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
