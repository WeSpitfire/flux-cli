"""Tool adapters for AI Orchestrator.

This module wraps existing Flux tools to make them compatible with
the AI orchestrator. Each adapter provides:
- Clear description for LLM understanding
- Parameter schema
- Execution wrapper
"""

from typing import Dict, Any, List
from pathlib import Path
from flux.core.orchestrator import ToolDefinition


def create_test_runner_tool(test_runner) -> ToolDefinition:
    """Create tool definition for test runner."""

    def execute(**params):
        """Run tests."""
        # test_runner.run_tests is NOT async
        result = test_runner.run_tests(**params)
        return {
            'passed': result.passed,
            'failed': result.failed,
            'total': result.total_tests,
            'output': str(result)[:500]
        }

    return ToolDefinition(
        name="run_tests",
        description="Run project tests and return results",
        executor=execute,
        schema={
            "pattern": {"type": "string", "optional": True, "description": "Test pattern to run (e.g., 'test_user')"}
        },
        requires_approval=False,
        is_destructive=False
    )


def create_auto_fixer_tool(auto_fixer) -> ToolDefinition:
    """Create tool definition for auto-fixer."""

    def execute(**params):
        """Fix code issues automatically."""
        from pathlib import Path
        files = params.get('files', [])

        if not files:
            # Analyze and fix all Python files in current directory
            import glob
            files = glob.glob('**/*.py', recursive=True)

        total_fixed = 0
        for file_path in files:
            path = Path(file_path)
            if not path.exists():
                continue

            # Analyze and apply fixes
            fixes = auto_fixer.analyze_file(path)
            if fixes:
                success, count = auto_fixer.apply_fixes(path, fixes)
                if success:
                    total_fixed += count

        return {'fixed_count': total_fixed, 'files_processed': len(files)}

    return ToolDefinition(
        name="auto_fix",
        description="Automatically fix code formatting, unused imports, and other safe issues",
        executor=execute,
        schema={
            "files": {"type": "array", "optional": True, "description": "Specific files to fix (empty = all files)"}
        },
        requires_approval=False,
        is_destructive=False  # Safe changes only
    )


def create_file_read_tool(tools_registry) -> ToolDefinition:
    """Create tool definition for reading files."""

    async def execute(**params):
        """Read files."""
        paths = params.get('paths', [])
        tool = tools_registry.get('read_files')
        return await tool.execute(paths=paths)

    return ToolDefinition(
        name="read_files",
        description="Read one or more files to understand current code",
        executor=execute,
        schema={
            "paths": {"type": "array", "description": "List of file paths to read"}
        },
        requires_approval=False,
        is_destructive=False
    )


def create_file_write_tool(tools_registry) -> ToolDefinition:
    """Create tool definition for writing files."""

    async def execute(**params):
        """Write to files."""
        file_path = params['file_path']
        content = params['content']
        tool = tools_registry.get('write_file')
        return await tool.execute(file_path=file_path, content=content)

    return ToolDefinition(
        name="write_file",
        description="Create or overwrite a file with new content",
        executor=execute,
        schema={
            "file_path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "File content"}
        },
        requires_approval=True,  # Creating files should be approved
        is_destructive=True
    )


def create_file_edit_tool(tools_registry) -> ToolDefinition:
    """Create tool definition for editing files."""

    async def execute(**params):
        """Edit existing files."""
        path = params['path']
        old_str = params['old_str']
        new_str = params['new_str']
        tool = tools_registry.get('edit_file')
        return await tool.execute(path=path, old_str=old_str, new_str=new_str)

    return ToolDefinition(
        name="edit_file",
        description="Edit an existing file by replacing text",
        executor=execute,
        schema={
            "path": {"type": "string", "description": "Path to file"},
            "old_str": {"type": "string", "description": "Text to find and replace"},
            "new_str": {"type": "string", "description": "Replacement text"}
        },
        requires_approval=True,
        is_destructive=True
    )


def create_git_diff_tool(git_integration) -> ToolDefinition:
    """Create tool definition for git diff."""

    def execute(**params):
        """Show git diff."""
        status = git_integration.get_status()
        if not status.has_changes:
            return {"has_changes": False}

        diff = git_integration.get_diff()
        return {
            "has_changes": True,
            "files_changed": status.total_changes,
            "diff": diff[:1000]  # Truncate for summary
        }

    return ToolDefinition(
        name="git_diff",
        description="Show what files have changed in git",
        executor=execute,
        schema={},
        requires_approval=False,
        is_destructive=False
    )


def create_git_commit_tool(git_integration) -> ToolDefinition:
    """Create tool definition for git commit."""

    async def execute(**params):
        """Commit changes."""
        message = params.get('message', 'Update files')
        result = git_integration.commit(message)
        return result

    return ToolDefinition(
        name="git_commit",
        description="Commit changes to git with a message",
        executor=execute,
        schema={
            "message": {"type": "string", "description": "Commit message"}
        },
        requires_approval=True,
        is_destructive=True
    )


def create_command_runner_tool(tools_registry) -> ToolDefinition:
    """Create tool definition for running commands."""

    async def execute(**params):
        """Run shell command."""
        command = params['command']
        tool = tools_registry.get('run_command')
        return await tool.execute(command=command)

    return ToolDefinition(
        name="run_command",
        description="Run a shell command and return output",
        executor=execute,
        schema={
            "command": {"type": "string", "description": "Shell command to execute"}
        },
        requires_approval=True,  # Shell commands can be dangerous
        is_destructive=True
    )


def create_grep_tool(tools_registry) -> ToolDefinition:
    """Create tool definition for searching code."""

    async def execute(**params):
        """Search codebase."""
        query = params['query']
        tool = tools_registry.get('grep_search')
        return await tool.execute(query=query)

    return ToolDefinition(
        name="search_code",
        description="Search for text/code patterns in the codebase",
        executor=execute,
        schema={
            "query": {"type": "string", "description": "Text or regex pattern to search for"}
        },
        requires_approval=False,
        is_destructive=False
    )


def create_codebase_index_tool(codebase_graph) -> ToolDefinition:
    """Create tool definition for building codebase index."""

    async def execute(**params):
        """Build codebase graph."""
        if codebase_graph:
            await codebase_graph.build_graph()
            return {"status": "indexed", "files": len(codebase_graph.files)}
        return {"status": "failed"}

    return ToolDefinition(
        name="index_codebase",
        description="Build semantic index of codebase for intelligent suggestions",
        executor=execute,
        schema={},
        requires_approval=False,
        is_destructive=False
    )


def create_suggestions_tool(suggestions_engine) -> ToolDefinition:
    """Create tool definition for getting AI suggestions."""

    def execute(**params):
        """Get proactive suggestions."""
        if suggestions_engine:
            suggestions = suggestions_engine.get_suggestions(priority=params.get('priority'))
            return {
                "count": len(suggestions),
                "suggestions": [s.to_dict() for s in suggestions[:5]]
            }
        return {"count": 0, "suggestions": []}

    return ToolDefinition(
        name="get_suggestions",
        description="Get proactive suggestions for code improvements",
        executor=execute,
        schema={
            "priority": {"type": "string", "optional": True, "description": "Filter by priority (high/medium/low)"}
        },
        requires_approval=False,
        is_destructive=False
    )


def register_all_tools(
    orchestrator,
    cli_instance
) -> None:
    """Register all Flux tools with the orchestrator.

    Args:
        orchestrator: AIOrchestrator instance
        cli_instance: CLI instance with all tools
    """
    # Test runner
    orchestrator.register_tool(
        create_test_runner_tool(cli_instance.test_runner)
    )

    # Auto-fixer
    orchestrator.register_tool(
        create_auto_fixer_tool(cli_instance.auto_fixer)
    )

    # File operations
    orchestrator.register_tool(
        create_file_read_tool(cli_instance.tools)
    )
    orchestrator.register_tool(
        create_file_write_tool(cli_instance.tools)
    )
    orchestrator.register_tool(
        create_file_edit_tool(cli_instance.tools)
    )

    # Git operations
    orchestrator.register_tool(
        create_git_diff_tool(cli_instance.git)
    )
    orchestrator.register_tool(
        create_git_commit_tool(cli_instance.git)
    )

    # Command execution
    orchestrator.register_tool(
        create_command_runner_tool(cli_instance.tools)
    )

    # Search
    orchestrator.register_tool(
        create_grep_tool(cli_instance.tools)
    )

    # Intelligence features
    orchestrator.register_tool(
        create_codebase_index_tool(cli_instance.codebase_graph)
    )

    if cli_instance.suggestions_engine:
        orchestrator.register_tool(
            create_suggestions_tool(cli_instance.suggestions_engine)
        )
