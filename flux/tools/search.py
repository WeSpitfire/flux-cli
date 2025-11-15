"""Search tools."""

import asyncio
import subprocess
from pathlib import Path
from typing import List, Any, Dict
from flux.tools.base import Tool, ToolParameter
from flux.core.tree_events import emit_search_result
from flux.core.semantic_search import SemanticSearchEngine


class GrepSearchTool(Tool):
    """Tool for searching code using grep/ripgrep."""

    def __init__(self, cwd: Path, workflow_enforcer=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.workflow = workflow_enforcer

    @property
    def name(self) -> str:
        return "grep_search"

    @property
    def description(self) -> str:
        return """Search for patterns in files using grep.
Useful for finding specific function names, class names, strings, or patterns in code.
Returns matching lines with file paths and line numbers."""

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="pattern",
                type="string",
                description="The pattern to search for (supports regex)",
                required=True
            ),
            ToolParameter(
                name="file_pattern",
                type="string",
                description="File pattern to search in (e.g., '*.py', '*.js'). Default: all files",
                required=False
            ),
            ToolParameter(
                name="case_sensitive",
                type="boolean",
                description="Whether search should be case sensitive. Default: false",
                required=False
            )
        ]

    async def execute(
        self,
        pattern: str,
        file_pattern: str = "*",
        case_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Search for pattern in files."""
        try:
            # Build grep command (try rg first, fall back to grep)
            rg_available = subprocess.run(
                ["which", "rg"],
                capture_output=True
            ).returncode == 0

            if rg_available:
                cmd = ["rg", "--line-number", "--with-filename"]
                if not case_sensitive:
                    cmd.append("--ignore-case")
                # Exclude common directories
                cmd.extend([
                    "--glob", "!node_modules/**",
                    "--glob", "!venv/**",
                    "--glob", "!.git/**",
                    "--glob", "!dist/**",
                    "--glob", "!build/**",
                    "--glob", "!__pycache__/**",
                    "--glob", file_pattern,
                    pattern, "."
                ])
            else:
                cmd = ["grep", "-rn"]
                if not case_sensitive:
                    cmd.append("-i")
                cmd.extend([
                    "--exclude-dir=node_modules",
                    "--exclude-dir=venv",
                    "--exclude-dir=.git",
                    "--exclude-dir=dist",
                    "--exclude-dir=build",
                    "--exclude-dir=__pycache__",
                    "--include", file_pattern,
                    pattern, "."
                ])

            # Run search
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.cwd)
            )

            stdout, stderr = await process.communicate()

            if process.returncode not in [0, 1]:  # 1 means no matches
                return {
                    "error": stderr.decode('utf-8', errors='replace'),
                    "matches": []
                }

            # Parse results
            output = stdout.decode('utf-8', errors='replace')
            matches = []

            for line in output.strip().split('\n'):
                if not line:
                    continue

                parts = line.split(':', 2)
                if len(parts) >= 3:
                    matches.append({
                        "file": parts[0],
                        "line": parts[1],
                        "content": parts[2]
                    })

            # Record search for workflow tracking
            if self.workflow:
                self.workflow.record_search(pattern)

            # Emit tree events for files with matches
            try:
                for match in matches:
                    emit_search_result(pattern, match["file"], 1)
            except Exception:
                pass  # Don't fail on event emission errors

            return {
                "pattern": pattern,
                "matches": matches,
                "count": len(matches)
            }
        except Exception as e:
            return {
                "error": str(e),
                "matches": []
            }


class SemanticSearchTool(Tool):
    """Tool for semantic code search using embeddings."""

    def __init__(self, cwd: Path, llm_client=None):
        """Initialize with current working directory.
        
        Args:
            cwd: Current working directory
            llm_client: LLM client for embeddings
        """
        self.cwd = cwd
        self.llm_client = llm_client
        self.engine = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "semantic_search"

    @property
    def description(self) -> str:
        return """Search code semantically using natural language to find implementations and patterns.

USE THIS TOOL WHEN:
- User asks exploratory questions: "where do we...", "show me...", "how does..."
- User wants to find code by concept/pattern (not exact symbol name)
- User is exploring unfamiliar codebase or understanding architecture
- User asks about implementation approach or design patterns

EXAMPLES:
- "where do we handle authentication?" → query: "authentication logic"
- "show me error handling" → query: "error handling patterns"
- "find database connection code" → query: "database connection"
- "how do we validate input?" → query: "input validation"

DO NOT USE FOR:
- Exact symbol names like "validateEmail function" (use grep_search)
- Specific file names like "auth.py" (use read_files)
- String literals or exact text matches (use grep_search)

Returns: Code chunks with similarity scores (0-1), file paths, and line numbers."""

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Natural language description of what code you're looking for",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of results to return (default: 5)",
                required=False
            ),
            ToolParameter(
                name="file_filter",
                type="string",
                description="Optional file path pattern to filter results",
                required=False
            )
        ]

    async def _ensure_initialized(self) -> None:
        """Ensure the search engine is initialized."""
        if not self._initialized:
            self.engine = SemanticSearchEngine(
                project_path=self.cwd,
                llm_client=self.llm_client
            )
            # Check if index exists, if not suggest indexing
            if not self.engine.indexed_files:
                # Don't auto-index on first search - let user decide
                pass
            self._initialized = True

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        file_filter: str = None
    ) -> Dict[str, Any]:
        """Search for code semantically.
        
        Args:
            query: Natural language search query
            max_results: Maximum results to return
            file_filter: Optional file path filter
            
        Returns:
            Search results with similarity scores
        """
        try:
            await self._ensure_initialized()
            
            # Check if project is indexed
            if not self.engine.indexed_files:
                return {
                    "error": "Project not indexed. Run /index to build codebase graph and enable semantic search.",
                    "results": [],
                    "suggestion": "index"
                }
            
            # Perform semantic search
            results = await self.engine.search(
                query=query,
                k=max_results,
                file_filter=file_filter
            )
            
            # Emit tree events for matching files
            try:
                for result in results:
                    emit_search_result(query, result['file_path'], result['score'])
            except Exception:
                pass  # Don't fail on event emission errors
            
            return {
                "query": query,
                "results": results,
                "count": len(results),
                "message": f"Found {len(results)} semantic matches"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "results": []
            }
