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
        
CRITICAL FOR MOVING FILES: You MUST use read_files FIRST to get actual content before moving.
NEVER write placeholder content like 'test_file.py content' - this destroys the file!

WORKFLOW for moving files:
1. read_files(['source.py']) - Get actual content
2. write_file('destination.py', actual_content) - Write with real content
3. Use separate tool to delete source if move successful

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
                    # Check severity - if there are syntax errors, this is critical
                    has_syntax_error = any(
                        'syntax' in e.get('message', '').lower() or 
                        e.get('type') == 'syntax_error'
                        for e in validation_result.errors
                    )
                    
                    if has_syntax_error:
                        # CRITICAL: Syntax error - return as error, not success
                        # Rollback if we have old content
                        if old_content is not None:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(old_content)
                            return {
                                "error": "Syntax error in written file - changes rolled back",
                                "syntax_errors": [
                                    f"{e['message']}" for e in validation_result.errors
                                ],
                                "rolled_back": True,
                                "path": str(file_path)
                            }
                        else:
                            # New file with syntax error - delete it
                            file_path.unlink()
                            return {
                                "error": "Syntax error in new file - file deleted",
                                "syntax_errors": [
                                    f"{e['message']}" for e in validation_result.errors
                                ],
                                "file_deleted": True,
                                "path": str(file_path)
                            }
                    else:
                        # Non-critical warnings (imports, etc) - report as warnings
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


class MoveFileTool(Tool):
    """Tool for moving files safely with validation."""
    
    def __init__(self, cwd: Path, undo_manager=None, workflow_enforcer=None, approval_manager=None, dry_run=False):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
        self.dry_run = dry_run
    
    @property
    def name(self) -> str:
        return "move_file"
    
    @property
    def description(self) -> str:
        return """Move or rename a file from source to destination. Validates content before deleting source.
        
SAFETY: Reads source, writes to destination, validates, then deletes source only if successful.
USE THIS instead of write_file + manual delete when moving files.
ON ERROR: Source file is preserved if move fails."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="source",
                type="string",
                description="Source file path (relative to current directory or absolute)",
                required=True
            ),
            ToolParameter(
                name="destination",
                type="string",
                description="Destination file path (relative to current directory or absolute)",
                required=True
            ),
            ToolParameter(
                name="dry_run",
                type="boolean",
                description="If true, show what would be done without executing",
                required=False
            )
        ]
    
    async def execute(self, source: str, destination: str, dry_run: bool = None) -> Dict[str, Any]:
        """Move file from source to destination."""
        # Use instance dry_run if parameter not provided
        if dry_run is None:
            dry_run = self.dry_run
        # Validate both paths
        is_valid_src, error_msg_src = validate_file_path(source, self.cwd, "read")
        if not is_valid_src:
            return {
                "error": {
                    "code": "INVALID_SOURCE_PATH",
                    "message": error_msg_src,
                    "path": source
                }
            }
        
        is_valid_dst, error_msg_dst = validate_file_path(destination, self.cwd, "write")
        if not is_valid_dst:
            return {
                "error": {
                    "code": "INVALID_DESTINATION_PATH",
                    "message": error_msg_dst,
                    "path": destination
                }
            }
        
        try:
            src_path = Path(source)
            if not src_path.is_absolute():
                src_path = self.cwd / src_path
            
            dst_path = Path(destination)
            if not dst_path.is_absolute():
                dst_path = self.cwd / dst_path
            
            # Check source exists
            if not src_path.exists():
                return {"error": f"Source file not found: {source}"}
            
            if not src_path.is_file():
                return {"error": f"Source is not a file: {source}"}
            
            # Check destination doesn't exist
            if dst_path.exists():
                return {
                    "error": f"Destination already exists: {destination}",
                    "suggestion": "Use write_file or edit_file if you want to overwrite."
                }
            
            # Check workflow enforcement
            if self.workflow:
                check = self.workflow.check_modification_allowed(src_path, "move_file")
                if not check["allowed"]:
                    return {
                        "error": check["reason"],
                        "suggestions": check.get("suggestions", []),
                        "workflow_blocked": True
                    }
            
            # Read source content
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # DRY RUN: Show what would be done without executing
            if dry_run:
                # Validate syntax if Python file
                syntax_valid = True
                if dst_path.suffix == '.py':
                    validation = SyntaxChecker.check_file(src_path, content)
                    syntax_valid = validation["valid"]
                
                return {
                    "dry_run": True,
                    "would_move": {
                        "source": str(src_path),
                        "destination": str(dst_path),
                        "bytes": len(content.encode('utf-8')),
                        "lines": len(content.splitlines()),
                        "syntax_valid": syntax_valid,
                        "destination_dir_exists": dst_path.parent.exists(),
                        "would_create_dirs": not dst_path.parent.exists()
                    },
                    "message": "Dry run: no changes made"
                }
            
            # Request approval if approval manager is present
            if self.approval:
                approved = self.approval.request_approval(
                    operation="move_file",
                    file_path=src_path,
                    old_content=content,
                    new_content=f"Moving to: {destination}",
                    context={
                        "action": "Moving",
                        "from": str(src_path),
                        "to": str(dst_path),
                        "size": f"{len(content)} bytes"
                    }
                )
                
                if not approved:
                    return {
                        "error": "Move rejected by user",
                        "rejected": True,
                        "source": str(src_path)
                    }
            
            # Create destination directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to destination
            with open(dst_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Validate destination file (for Python files)
            if dst_path.suffix == '.py':
                validation = SyntaxChecker.check_file(dst_path, content)
                if not validation["valid"]:
                    # Delete invalid destination
                    dst_path.unlink()
                    return {
                        "error": "Moved file has syntax error - move aborted",
                        "syntax_error": validation.get("error"),
                        "source_preserved": True,
                        "source": str(src_path)
                    }
            
            # Record undo snapshot before deleting source
            if self.undo_manager:
                self.undo_manager.snapshot_operation(
                    operation="move",
                    file_path=src_path,
                    old_content=content,
                    new_content=None,  # File deleted
                    description=f"Moved {src_path.name} to {dst_path}"
                )
            
            # Delete source only after successful validation
            src_path.unlink()
            
            return {
                "success": True,
                "source": str(src_path),
                "destination": str(dst_path),
                "bytes": len(content.encode('utf-8'))
            }
        except Exception as e:
            return {"error": f"Move failed: {str(e)}"}


class DeleteFileTool(Tool):
    """Tool for deleting files with safety checks."""
    
    def __init__(self, cwd: Path, undo_manager=None, workflow_enforcer=None, approval_manager=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
    
    @property
    def name(self) -> str:
        return "delete_file"
    
    @property
    def description(self) -> str:
        return """Delete a file with undo support.
        
SAFETY: Content is backed up in undo manager before deletion.
WARNING: Use with caution - deletion is immediate but can be undone.
ON ERROR: Check file path and permissions."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path to delete (relative to current directory or absolute)",
                required=True
            )
        ]
    
    async def execute(self, path: str) -> Dict[str, Any]:
        """Delete a file."""
        # Validate path
        is_valid, error_msg = validate_file_path(path, self.cwd, "delete")
        if not is_valid:
            return {
                "error": {
                    "code": "INVALID_PATH",
                    "message": error_msg,
                    "path": path
                }
            }
        
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.cwd / file_path
            
            # Check file exists
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            
            if not file_path.is_file():
                return {"error": f"Path is not a file: {path}"}
            
            # Check workflow enforcement
            if self.workflow:
                check = self.workflow.check_modification_allowed(file_path, "delete_file")
                if not check["allowed"]:
                    return {
                        "error": check["reason"],
                        "suggestions": check.get("suggestions", []),
                        "workflow_blocked": True
                    }
            
            # Read content for undo
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Request approval if approval manager is present
            if self.approval:
                approved = self.approval.request_approval(
                    operation="delete_file",
                    file_path=file_path,
                    old_content=content,
                    new_content=None,
                    context={
                        "action": "Deleting",
                        "size": f"{len(content)} bytes",
                        "lines": len(content.splitlines())
                    }
                )
                
                if not approved:
                    return {
                        "error": "Deletion rejected by user",
                        "rejected": True,
                        "path": str(file_path)
                    }
            
            # Record undo snapshot
            if self.undo_manager:
                self.undo_manager.snapshot_operation(
                    operation="delete",
                    file_path=file_path,
                    old_content=content,
                    new_content=None,
                    description=f"Deleted {file_path.name}"
                )
            
            # Delete file
            file_path.unlink()
            
            return {
                "success": True,
                "path": str(file_path),
                "can_undo": self.undo_manager is not None
            }
        except Exception as e:
            return {"error": f"Delete failed: {str(e)}"}


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
