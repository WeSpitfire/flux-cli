"""Regression tests for previously fixed bugs.

These tests ensure that bugs we've fixed don't come back.
"""

import pytest
from pathlib import Path
from flux.core.config import Config
from flux.core.context_manager import ContextManager
from flux.llm.prompts import get_system_prompt


def test_main_py_no_broken_code():
    """Regression: Ensure main.py doesn't have broken search command code.

    Bug: Lines 21-33 in main.py had invalid @cli.command() decorator
    that referenced undefined variables (cli, click, grep_search).

    Fix: Removed lines 21-33 entirely.
    """
    main_py = Path("flux/main.py")
    content = main_py.read_text()

    # Should NOT contain the broken code
    assert "@cli.command()" not in content, "main.py should not have @cli.command() decorator"
    assert "grep_search" not in content, "main.py should not reference grep_search"
    assert "click.argument" not in content, "main.py should not use click decorators"


def test_haiku_context_limits():
    """Regression: Ensure Haiku gets proper context limits.

    Bug: Haiku with 8K context was using default 8K max_history,
    leaving no room for system prompt, tool schemas, and response.

    Fix: Haiku now gets 3K max_history automatically.
    """
    # Create config with Haiku
    import os
    original_model = os.environ.get("FLUX_MODEL")
    os.environ["FLUX_MODEL"] = "claude-3-haiku-20240307"

    try:
        config = Config()

        # Haiku should have reduced limits
        assert config.max_history == 3000, f"Haiku max_history should be 3000, got {config.max_history}"
        assert config.max_context_tokens == 3000, f"Haiku max_context_tokens should be 3000"
    finally:
        # Restore original
        if original_model:
            os.environ["FLUX_MODEL"] = original_model
        else:
            os.environ.pop("FLUX_MODEL", None)


def test_sonnet_context_limits():
    """Ensure Sonnet gets appropriate context limits."""
    import os
    original_model = os.environ.get("FLUX_MODEL")
    os.environ["FLUX_MODEL"] = "claude-3-5-sonnet-20241022"

    try:
        config = Config()

        # Sonnet should have default limits (not reduced)
        assert config.max_history == 8000, f"Sonnet max_history should be 8000, got {config.max_history}"
        assert config.max_context_tokens >= 150000, f"Sonnet should have large context"
    finally:
        if original_model:
            os.environ["FLUX_MODEL"] = original_model
        else:
            os.environ.pop("FLUX_MODEL", None)


def test_context_pruning_aggressive_for_small_models():
    """Regression: Small models should get more aggressive pruning.

    Bug: Context pruning used 75% target for all models,
    causing Haiku to overflow frequently.

    Fix: Small models (<5000 tokens) use 50% target and keep fewer recent messages.
    """
    # Small model context manager
    small_cm = ContextManager(max_context_tokens=3000)

    # Create fake history that exceeds budget
    history = [
        {"role": "user", "content": "A" * 1000},
        {"role": "assistant", "content": "B" * 1000},
        {"role": "user", "content": "C" * 1000},
        {"role": "assistant", "content": "D" * 1000},
        {"role": "user", "content": "E" * 1000},
        {"role": "assistant", "content": "F" * 1000},
    ]

    pruned = small_cm.prune_history(history)

    # Should aggressively prune
    assert len(pruned) < len(history), "Small model should prune messages"

    # Estimate tokens (chars // 3)
    total_chars = sum(len(str(m.get("content", ""))) for m in pruned)
    estimated_tokens = total_chars // 3

    # Should target 50% of max (1500 tokens)
    assert estimated_tokens <= 1500, f"Pruned history too large: {estimated_tokens} tokens"


def test_haiku_gets_concise_prompt():
    """Regression: Haiku should get concise system prompt.

    Bug: All models used same 207-line system prompt,
    wasting Haiku's limited context.

    Fix: Haiku gets 39-line SYSTEM_PROMPT_HAIKU.
    """
    haiku_prompt = get_system_prompt("claude-3-haiku-20240307")
    sonnet_prompt = get_system_prompt("claude-3-5-sonnet-20241022")

    # Haiku prompt should be much shorter
    assert len(haiku_prompt) < len(sonnet_prompt), "Haiku prompt should be shorter than Sonnet"

    # Haiku prompt should be concise (roughly 39 lines = ~1500 chars)
    assert len(haiku_prompt) < 2000, f"Haiku prompt too long: {len(haiku_prompt)} chars"

    # Should contain key instructions
    assert "CRITICAL RULES" in haiku_prompt
    assert "Always read files before editing" in haiku_prompt


def test_gpt35_also_gets_concise_prompt():
    """GPT-3.5 should also get concise prompt (small context)."""
    gpt35_prompt = get_system_prompt("gpt-3.5-turbo")

    # Should get same concise prompt as Haiku
    assert len(gpt35_prompt) < 2000, "GPT-3.5 should get concise prompt"
    assert "CRITICAL RULES" in gpt35_prompt


def test_no_orphaned_tool_results():
    """Regression: Ensure no orphaned tool results in conversation history.

    Bug: Line 1560 in cli.py created orphaned tool results with random UUIDs
    that didn't match any tool_use blocks, causing API errors.

    Fix: Auto-read content included directly in main tool result instead.

    This test would need actual CLI integration to fully test, but we can
    check the code structure.
    """
    cli_py = Path("flux/ui/cli.py")
    content = cli_py.read_text()

    # Should NOT create separate tool result with random UUID
    assert "uuid.uuid4()" not in content or "read_tool_id" not in content, \
        "CLI should not create orphaned tool results with random UUIDs"

    # Should include auto-read content in main result
    assert 'result["auto_read_content"]' in content, \
        "Auto-read content should be included in main result"


def test_failure_blocking_threshold():
    """Regression: Failure tracker should block after 2 failures, not 3.

    Bug: Original threshold was 3, allowing too many retry attempts.

    Fix: Changed to threshold=2 in multiple places.
    """
    cli_py = Path("flux/ui/cli.py")
    content = cli_py.read_text()

    # Should use threshold=2 for retry loop detection
    assert "threshold=2" in content, "Should use threshold=2 for retry loop blocking"

    # Verify in context
    assert "is_retry_loop(tool_name, threshold=2)" in content


def test_ast_edit_not_available_for_haiku():
    """Regression: ast_edit should not be registered for Haiku.

    Bug: ast_edit had high failure rate on Haiku but was still available.

    Fix: Conditionally skip ast_edit registration for Haiku and GPT-3.5.
    """
    cli_py = Path("flux/ui/cli.py")
    content = cli_py.read_text()

    # Should have conditional registration
    assert 'if "haiku" not in config.model.lower()' in content, \
        "Should conditionally register ast_edit"
    assert "ASTEditTool" in content, "ASTEditTool should still be imported"


def test_analyze_command_exists():
    """Regression: /analyze command should be available.

    Feature: Added /analyze command for large file analysis.
    """
    cli_py = Path("flux/ui/cli.py")
    content = cli_py.read_text()

    # Should have /analyze command
    assert "'/analyze '" in content or '"/analyze ' in content, \
        "/analyze command should be implemented"
    assert "analyze_file_structure" in content, \
        "analyze_file_structure method should exist"


def test_tool_metrics_tracking():
    """Regression: Tool metrics should be tracked.

    Feature: Added tool success tracking.
    """
    cli_py = Path("flux/ui/cli.py")
    content = cli_py.read_text()

    # Should initialize tool metrics
    assert "ToolSuccessTracker" in content
    assert "tool_metrics" in content
    assert "record_attempt" in content


def test_auto_clear_at_90_percent():
    """Regression: Context should auto-clear at 90% capacity.

    Bug: Previously showed warnings, requiring manual user action.

    Fix: Automatically clears at 90%, preserving task context.
    """
    cli_py = Path("flux/ui/cli.py")
    content = cli_py.read_text()

    # Should have auto-clear logic
    assert "usage_percent >= 90" in content
    assert "self.llm.clear_history()" in content

    # Should preserve task
    assert "current_task" in content


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
