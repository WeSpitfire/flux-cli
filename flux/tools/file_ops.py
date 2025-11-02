"""File operation tools."""

import json
import re
from pathlib import Path
from typing import List, Any, Dict, Optional, Tuple
from flux.tools.base import Tool, ToolParameter
from flux.core.diff import DiffPreview
from flux.core.syntax_checker import SyntaxChecker
from flux.core.errors import file_not_found_error, search_not_found_error, syntax_error_response
from flux.core.code_validator import CodeValidator
from rich.console import Console


def validate_file_path(path_str: str, cwd: Path, operation: str = "access") -> Tuple[bool, Optional[str]]:
    """Validate a file path for safety.
    
    Args:
        path_str: The path string to validate
        cwd: Current working directory
        operation: Type of operation (read, write, delete)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        path = Path(path_str)
        
        # Resolve to absolute path
        if not path.is_absolute():
            path = cwd / path
        path = path.resolve()
        
        # Check for path traversal attempts that escape project
        # Allow going outside cwd but flag suspicious patterns
        path_str_lower = str(path).lower()
        
        # Block access to sensitive system directories
        dangerous_paths = [
            '/etc/passwd', '/etc/shadow', '/etc/sudoers',
            '/boot', '/sys', '/proc',
            'c:\\windows\\system32', 'c:\\windows\\syswow64',
        ]
        
        for dangerous in dangerous_paths:
            if dangerous.lower() in path_str_lower:
                return False, f"Access to system path '{dangerous}' is not allowed for security reasons."
        
        # Check for null bytes (path injection)
        if '\x00' in path_str:
            return False, "Path contains null byte - potential path injection attack."
        
        # Warn about paths with unusual characters
        if re.search(r'[<>:"|?*]', path_str) and operation == "write":
            return False, f"Path contains invalid characters for {operation} operation."
        
        # For delete operations, be extra careful
        if operation == "delete":
            # Don't allow deleting root or critical directories
            critical_dirs = ['/', '/home', '/usr', '/var', str(Path.home())]
            if str(path) in critical_dirs:
                return False, f"Cannot delete critical directory: {path}"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid path: {str(e)}"


class ReadFilesTool(Tool):
    """Tool for reading file contents."""
    
    def __init__(self, cwd: Path, workflow_enforcer=None, background_processor=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.workflow = workflow_enforcer
        self.bg_processor = background_processor
    
    @property
    def name(self) -> str:
        return "read_files"
    
    @property
    def description(self) -> str:
        return """Read file contents with line numbers.
        
CRITICAL: ALWAYS use this BEFORE any edit operation (100% of time, no exceptions).
USAGE: Pass list of file paths. Read entire file or use line numbers to find exact content.
CACHING: Files are cached during workflow - reading same file twice uses cache.
ON ERROR: Use list_files or find_files to discover correct paths."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="paths",
                type="array",
                description="List of file paths to read (relative to current directory or absolute)",
                required=True,
                items={"type": "string"}
            )
    ]
    
    async def execute(self, paths: List[str]) -> Dict[str, Any]:
        """Read files and return their contents."""
        results = {}
        
        for path_str in paths:
            # Validate path first
            is_valid, error_msg = validate_file_path(path_str, self.cwd, "read")
            if not is_valid:
                results[path_str] = {
                    "error": {
                        "code": "INVALID_PATH",
                        "message": error_msg,
                        "path": path_str
                    }
                }
                continue
            
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
                
                # Check background processor cache first (from smart preloading)
                cached_content = None
                cache_source = None
                
                if self.bg_processor:
                    cached_content = self.bg_processor.get_cached_file(path)
                    if cached_content:
                        cache_source = 'background'
                        # Record time saved (typical file read is ~5-10ms)
                        self.bg_processor.record_time_saved(7)
                
                # Fall back to workflow cache
                if cached_content is None and self.workflow:
                    cached_content = self.workflow.get_cached_file(path)
                    if cached_content:
                        cache_source = 'workflow'
                
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
    
    def __init__(self, cwd: Path, undo_manager=None, workflow_enforcer=None, approval_manager=None, code_validator=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
        self.code_validator = code_validator or CodeValidator(cwd)
    
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
        # Validate path first
        is_valid, error_msg = validate_file_path(path, self.cwd, "write")
        if not is_valid:
            return {
                "error": {
                    "code": "INVALID_PATH",
                    "message": error_msg,
                    "path": path,
                    "suggestion": "Check the file path for invalid characters or access to restricted directories."
                }
            }
        
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
            
            # CODE VALIDATION: Check for import errors after write
            if file_path.suffix == '.py' and self.code_validator:
                validation_result = self.code_validator.validate_file_operation(file_path, "write")
                if not validation_result.is_valid:
                    # Add validation warnings/errors to response
                    result = {
                        "success": True,
                        "path": str(file_path),
                        "bytes_written": len(content.encode('utf-8')),
                        "validation_warnings": [
                            f"{e['message']}" for e in validation_result.errors
                        ]
                    }
                    if validation_result.suggestions:
                        result["validation_suggestions"] = validation_result.suggestions
                    
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
                    
                    return result
            
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
    
    def __init__(self, cwd: Path, show_diff: bool = True, undo_manager=None, workflow_enforcer=None, approval_manager=None, code_validator=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.show_diff = show_diff
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
        self.console = Console()
        self.diff_preview = DiffPreview(self.console)
        self.code_validator = code_validator or CodeValidator(cwd)
    
    @property
    def name(self) -> str:
        return "edit_file"
    
    @property
    def description(self) -> str:
        return """Edit files by replacing exact text matches. MOST RELIABLE TOOL - use for 90% of edits.
        
WORKFLOW: 1) read_files first 2) copy EXACT text from output 3) provide replacement
BEST FOR: All code modifications (Python, JS, TS, etc). Works with all languages.
KEY: Make MINIMAL changes (3-10 lines). DON'T replace entire functions (100+ lines).
     Find exact insertion point, include 2-3 lines before/after as context for search.
     Match exact whitespace/indentation from file read.
ON ERROR: Re-read file, copy exact text including all spaces/tabs. Check indentation carefully."""
    
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
        # Validate path first
        is_valid, error_msg = validate_file_path(path, self.cwd, "write")
        if not is_valid:
            return {
                "error": {
                    "code": "INVALID_PATH",
                    "message": error_msg,
                    "path": path,
                    "suggestion": "Check the file path for invalid characters or access to restricted directories."
                }
            }
        
        # Validate search and replace strings
        if not search:
            return {
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Search string cannot be empty.",
                    "suggestion": "Provide the exact text you want to replace."
                }
            }
        
        if len(search) < 3:
            return {
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Search string is too short (minimum 3 characters).",
                    "suggestion": "Use a longer search string to avoid unintended replacements."
                }
            }
        
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
                    rolled_back=True,
                    original_content=content,
                    modified_content=new_content
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
            
            result = {
                "success": True,
                "path": str(file_path),
                "old_lines": len(content.splitlines()),
                "new_lines": len(new_content.splitlines()),
                "diff_summary": f"+{additions} -{deletions} ~{modifications}"
            }
            
            # CODE VALIDATION: Check for import errors after edit
            if file_path.suffix == '.py' and self.code_validator:
                validation_result = self.code_validator.validate_file_operation(file_path, "edit")
                if not validation_result.is_valid:
                    result["validation_warnings"] = [
                        f"{e['message']}" for e in validation_result.errors
                    ]
                    if validation_result.suggestions:
                        result["validation_suggestions"] = validation_result.suggestions
            
            return result
        except Exception as e:
            return {"error": str(e)}
