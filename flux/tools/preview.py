"""Diff preview tool for checking changes before applying."""

import difflib
from pathlib import Path
from typing import List, Any, Dict
from flux.tools.base import Tool, ToolParameter


class PreviewEditTool(Tool):
    """Preview what an edit_file operation would look like without applying it."""

    def __init__(self, cwd: Path):
        """Initialize with current working directory."""
        self.cwd = cwd

    @property
    def name(self) -> str:
        return "preview_edit"

    @property
    def description(self) -> str:
        return """Preview what an edit_file operation would change WITHOUT applying it.

Use this BEFORE edit_file if you're unsure about:
- Indentation correctness
- Search text matching
- Scope of changes

Shows a unified diff preview so you can verify the change looks correct.
If preview looks wrong, you can adjust your search/replace before using edit_file."""

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path to preview changes for",
                required=True
            ),
            ToolParameter(
                name="search",
                type="string",
                description="Text to search for (same as edit_file)",
                required=True
            ),
            ToolParameter(
                name="replace",
                type="string",
                description="Text to replace with (same as edit_file)",
                required=True
            )
        ]

    async def execute(self, path: str, search: str, replace: str) -> Dict[str, Any]:
        """Preview the edit without applying it."""
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.cwd / file_path

            if not file_path.exists():
                return {"error": "File not found"}

            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                original = f.read()

            # Check if search text exists
            if search not in original:
                return {
                    "found": False,
                    "error": "Search text not found in file",
                    "suggestion": "The search text doesn't exist. Check spelling and whitespace."
                }

            # Count occurrences
            count = original.count(search)
            if count > 1:
                return {
                    "found": True,
                    "occurrences": count,
                    "warning": f"Search text appears {count} times - edit_file will fail. Make search more specific."
                }

            # Generate modified content
            modified = original.replace(search, replace, 1)

            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm=''
            ))

            diff_text = ''.join(diff_lines)

            # Analyze the change
            added_lines = len([l for l in diff_lines if l.startswith('+')])
            removed_lines = len([l for l in diff_lines if l.startswith('-')])

            # Check for potential indentation issues
            warnings = []

            # Check if replacement has different indentation
            search_lines = search.split('\n')
            replace_lines = replace.split('\n')

            if len(search_lines) == len(replace_lines):
                for s_line, r_line in zip(search_lines, replace_lines):
                    s_indent = len(s_line) - len(s_line.lstrip())
                    r_indent = len(r_line) - len(r_line.lstrip())
                    if s_indent != r_indent and s_line.strip() and r_line.strip():
                        warnings.append(
                            f"Indentation change detected: {s_indent} spaces → {r_indent} spaces. "
                            f"Verify this is intentional."
                        )
                        break

            return {
                "preview": diff_text,
                "found": True,
                "occurrences": 1,
                "changes": {
                    "lines_added": added_lines,
                    "lines_removed": removed_lines,
                    "lines_modified": min(added_lines, removed_lines)
                },
                "warnings": warnings if warnings else None,
                "next_step": "If this looks correct, use edit_file with the same search/replace parameters."
            }

        except Exception as e:
            return {"error": str(e)}
