"""File operation tools."""

import json
from pathlib import Path
from typing import List, Any, Dict, Optional
from flux.tools.base import Tool, ToolParameter
from flux.core.diff import DiffPreview
from flux.core.syntax_checker import SyntaxChecker
from flux.core.errors import file_not_found_error, search_not_found_error, syntax_error_response
from rich.console import Console


class ReadFilesTool(Tool):
    """Tool for reading file contents."""
    
    def __init__(self, cwd: Path, workflow_enforcer=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.workflow = workflow_enforcer
    
    @property
    def name(self) -> str:
        return "read_files"
    
    @property
    def description(self) -> str:
        return """Read file contents with line numbers.
        
USAGE: Pass list of file paths. Always read files BEFORE modifying them.
CACHING: Files are cached during workflow - reading same file twice uses cache.
ON ERROR: Use list_files or find_files to discover correct paths."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="paths",
                type="array",
                description="List of file paths to read (relative to current directory or absolute)",
                required=True
            )
    ]
    
    async def execute(self, paths: List[str]) -> Dict[str, Any]:
        """Read files and return their contents."""
        results = {}
        
        for path_str in paths:
            try:
                path = Path(path_str)
                if not path.is_absolute():
                    path = self.cwd / path
                
                if not path.exists():
                    # Find similar files to help agent
                    parent = path.parent if path.parent.exists() else self.cwd
                    try:
                        similar = [str(f.relative_to(self.cwd)) for f in parent.glob('*') if f.is_file()][:5]
                    except:
                        similar = None
                    results[path_str] = file_not_found_error(path_str, similar)
                    continue
                
                if not path.is_file():
                    results[path_str] = {"error": "Path is not a file"}
                    continue
                
                # Check cache first to avoid re-reading same file in workflow
                cached_content = None
                if self.workflow:
                    cached_content = self.workflow.get_cached_file(path)
                
                if cached_content is not None:
                    # Use cached content
                    content = cached_content
                    lines_count = content.count('\n')
                else:
                    # Read file with line numbers
                    with open(path, 'r', encoding='utf-8') as f:
                        file_lines = f.readlines()
                        content = "".join([f"{i+1}|{line}" for i, line in enumerate(file_lines)])
                        lines_count = len(file_lines)
                    
                    # Cache the content for reuse in this workflow
                    if self.workflow:
                        self.workflow.record_file_read(path, content)
                
                results[path_str] = {
                    "content": content,
                    "lines": lines_count,
                    "cached": cached_content is not None
                }
            except Exception as e:
                results[path_str] = {"error": str(e)}
        
        return results



class WriteFileTool(Tool):
    """Tool for writing/creating files."""
    
    def __init__(self, cwd: Path, undo_manager=None, workflow_enforcer=None, approval_manager=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return """Write content to a file, creating it if it doesn't exist. Overwrites existing files.
        
USAGE: Provide complete file path relative to current directory (e.g., 'flux/core/validators.py').
AUTO-ROLLBACK: Syntax errors automatically rolled back for Python files.
ON ERROR: Check file permissions and path validity."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path (relative to current directory or absolute)",
                required=True
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Content to write to the file",
                required=True
            ),
            ToolParameter(
                name="target_dir",
                type="string",
                description="DEPRECATED: Do not use. Provide complete path in 'path' parameter instead.",
                required=False
            )
        ]
    
    async def execute(self, path: str, content: str, target_dir: str = None) -> Dict[str, Any]:
        """Write content to file."""
        try:
            file_path = Path(path)
            
            # Handle path resolution
            if file_path.is_absolute():
                # Already absolute, use as-is
                pass
            elif target_dir:
                # If target_dir is provided, treat path as relative to cwd
                # (not relative to target_dir, to avoid duplication)
                # target_dir parameter is deprecated - path should be complete
                file_path = self.cwd / path
            else:
                # Normal case: relative to cwd
                file_path = self.cwd / path
            
            # Check workflow enforcement
            if self.workflow:
                check = self.workflow.check_modification_allowed(file_path, "write_file")
                if not check["allowed"]:
                    return {
                        "error": check["reason"],
                        "suggestions": check.get("suggestions", []),
                        "workflow_blocked": True
                    }
            
            # Snapshot for undo
            old_content = None
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_content = f.read()
                except Exception:
                    pass
            
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Request approval if approval manager is present
            if self.approval:
                approved = self.approval.request_approval(
                    operation="write_file",
                    file_path=file_path,
                    old_content=old_content,
                    new_content=content,
                    context={
                        "action": "Creating" if old_content is None else "Overwriting",
                        "size": f"{len(content)} bytes"
                    }
                )
                
                if not approved:
                    return {
                        "error": "Change rejected by user",
                        "rejected": True,
                        "path": str(file_path)
                    }
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Syntax check and auto-rollback if invalid
            if old_content is not None:
                validation = SyntaxChecker.validate_modification(
                    file_path, old_content, content
                )
                
                if validation["should_rollback"]:
                    # Rollback the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(old_content)
                    
                    return {
                        "error": "Syntax error introduced - changes rolled back",
                        "syntax_error": validation["error"],
                        "rolled_back": True,
                        "path": str(file_path)
                    }
            
            # Record undo snapshot
            if self.undo_manager:
                desc = "Created" if old_content is None else "Overwrote"
                self.undo_manager.snapshot_operation(
                    operation="write",
                    file_path=file_path,
                    old_content=old_content,
                    new_content=content,
                    description=f"{desc} {file_path.name}"
                )
            
            return {
                "success": True,
                "path": str(file_path),
                "bytes_written": len(content.encode('utf-8'))
            }
        except Exception as e:
            return {"error": str(e)}


class EditFileTool(Tool):
    """Tool for editing files with diff-based replacements."""
    
    def __init__(self, cwd: Path, show_diff: bool = True, undo_manager=None, workflow_enforcer=None, approval_manager=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.show_diff = show_diff
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
        self.console = Console()
        self.diff_preview = DiffPreview(self.console)
    
    @property
    def name(self) -> str:
        return "edit_file"
    
    @property
    def description(self) -> str:
        return """Edit files by replacing exact text matches. Most reliable tool for code changes.
        
USAGE: Read file first, copy EXACT text to replace (whitespace matters), provide new text.
BEST FOR: Any code changes, especially JS/TS/CSS/HTML/JSON. Preserves undo history.
ON ERROR: Re-read file to see current content - text must match exactly including all spaces/tabs."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path (relative to current directory or absolute)",
                required=True
            ),
            ToolParameter(
                name="search",
                type="string",
                description="Exact text to search for in the file (must match exactly)",
                required=True
            ),
            ToolParameter(
                name="replace",
                type="string",
                description="Text to replace the search text with",
                required=True
            )
        ]
    
    async def execute(self, path: str, search: str, replace: str) -> Dict[str, Any]:
        """Edit file by replacing search with replace."""
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.cwd / file_path
            
            # Check workflow enforcement
            if self.workflow:
                check = self.workflow.check_modification_allowed(file_path, "edit_file")
                if not check["allowed"]:
                    return {
                        "error": check["reason"],
                        "suggestions": check.get("suggestions", []),
                        "workflow_blocked": True
                    }
            
            if not file_path.exists():
                return {"error": "File not found"}
            
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if search text exists
            if search not in content:
                # Try to find closest match for better error message
                lines = content.split('\n')
                closest_match = None
                for i, line in enumerate(lines, 1):
                    if any(word in line for word in search.split()[:3]):
                        closest_match = {"line": i, "text": line[:80]}
                        break
                return search_not_found_error(str(file_path), search, closest_match)
            
            # Count occurrences
            count = content.count(search)
            if count > 1:
                return {
                    "error": f"Search text appears {count} times in file",
                    "hint": "Make search text more specific to match only one occurrence"
                }
            
            # Replace
            new_content = content.replace(search, replace, 1)
            
            # Show diff preview if enabled (only if no approval manager, otherwise approval shows it)
            if self.show_diff and not self.approval:
                self.diff_preview.display_compact_diff(content, new_content, file_path.name)
            
            # Validate syntax before writing
            validation = SyntaxChecker.validate_modification(
                file_path, content, new_content
            )
            
            if validation["should_rollback"]:
                return syntax_error_response(
                    validation["error"],
                    line_number=validation.get("line"),
                    rolled_back=True
                )
            
            # Request approval if approval manager is present
            if self.approval:
                additions, deletions, _ = self.diff_preview.get_change_stats(content, new_content)
                approved = self.approval.request_approval(
                    operation="edit_file",
                    file_path=file_path,
                    old_content=content,
                    new_content=new_content,
                    context={
                        "changes": f"+{additions} -{deletions}",
                        "lines": f"{len(content.splitlines())} → {len(new_content.splitlines())}"
                    }
                )
                
                if not approved:
                    return {
                        "error": "Change rejected by user",
                        "rejected": True,
                        "path": str(file_path)
                    }
            
            # Record undo snapshot before writing
            if self.undo_manager:
                self.undo_manager.snapshot_operation(
                    operation="edit",
                    file_path=file_path,
                    old_content=content,
                    new_content=new_content,
                    description=f"Edited {file_path.name}"
                )
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            additions, deletions, modifications = self.diff_preview.get_change_stats(content, new_content)
            
            return {
                "success": True,
                "path": str(file_path),
                "old_lines": len(content.splitlines()),
                "new_lines": len(new_content.splitlines()),
                "diff_summary": f"+{additions} -{deletions} ~{modifications}"
            }
        except Exception as e:
            return {"error": str(e)}
