"""Search tools."""

import asyncio
import subprocess
from pathlib import Path
from typing import List, Any, Dict
from flux.tools.base import Tool, ToolParameter


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
