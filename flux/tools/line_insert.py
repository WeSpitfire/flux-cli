"""Line-based code insertion tool with automatic indentation handling."""

from pathlib import Path
from typing import List, Any, Dict
from flux.tools.base import Tool, ToolParameter
from flux.core.indentation import IndentationHelper
from flux.core.syntax_checker import SyntaxChecker
from flux.core.errors import syntax_error_response


class InsertAtLineTool(Tool):
    """Insert code at specific line numbers with automatic indentation."""
    
    def __init__(self, cwd: Path, undo_manager=None, workflow_enforcer=None, approval_manager=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
    
    @property
    def name(self) -> str:
        return "insert_at_line"
    
    @property
    def description(self) -> str:
        return """Insert code at a specific line number with AUTOMATIC indentation handling.

BEST FOR: Adding new code when you know the exact line number.
NO NEED to worry about indentation - it's automatically detected and applied!

ADVANTAGES over edit_file:
- No search/replace text matching required
- Indentation handled automatically
- Can't fail due to whitespace issues
- Perfect for adding new blocks of code

USAGE:
1. Read the file to see line numbers
2. Find where to insert (e.g., after line 207)
3. Provide the code WITHOUT worrying about exact indentation
4. Tool automatically matches surrounding indentation

MODE OPTIONS:
- 'before': Insert before the line number
- 'after': Insert after the line number (most common)
- 'replace': Replace the line"""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path",
                required=True
            ),
            ToolParameter(
                name="line_number",
                type="number",
                description="Line number to insert at (1-indexed)",
                required=True
            ),
            ToolParameter(
                name="code",
                type="string",
                description="Code to insert (indentation will be auto-corrected)",
                required=True
            ),
            ToolParameter(
                name="mode",
                type="string",
                description="Insert mode: 'before', 'after', or 'replace' (default: 'after')",
                required=False
            )
        ]
    
    async def execute(self, 
                     path: str, 
                     line_number: int, 
                     code: str,
                     mode: str = "after") -> Dict[str, Any]:
        """Insert code at line number with automatic indentation."""
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.cwd / file_path
            
            # Check workflow enforcement
            if self.workflow:
                check = self.workflow.check_modification_allowed(file_path, "insert_at_line")
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
                original_content = f.read()
            
            lines = original_content.split('\n')
            
            # Validate line number
            if line_number < 1 or line_number > len(lines) + 1:
                return {
                    "error": f"Invalid line number: {line_number}. File has {len(lines)} lines."
                }
            
            # Detect indentation at target line
            if mode == "before":
                target_line = line_number
            elif mode == "after":
                target_line = min(line_number + 1, len(lines))
            else:  # replace
                target_line = line_number
            
            indent_str, indent_count = IndentationHelper.detect_indentation_from_context(
                original_content,
                target_line,
                look_back=10
            )
            
            # Normalize code indentation
            normalized_code = IndentationHelper.normalize_indentation(
                code,
                indent_str,
                indent_count
            )
            
            # Insert code based on mode
            new_lines = lines.copy()
            
            if mode == "before":
                # Insert before line
                new_lines.insert(line_number - 1, normalized_code)
            elif mode == "replace":
                # Replace line
                new_lines[line_number - 1] = normalized_code
            else:  # after (default)
                # Insert after line
                new_lines.insert(line_number, normalized_code)
            
            # Create new content
            new_content = '\n'.join(new_lines)
            
            # Validate syntax before writing
            validation = SyntaxChecker.validate_modification(
                file_path, original_content, new_content
            )
            
            if validation["should_rollback"]:
                return syntax_error_response(
                    validation["error"],
                    line_number=validation.get("line"),
                    rolled_back=False,  # Haven't written yet
                    original_content=original_content,
                    modified_content=new_content
                )
            
            # Request approval if approval manager is present
            if self.approval:
                approved = self.approval.request_approval(
                    operation="insert_at_line",
                    file_path=file_path,
                    old_content=original_content,
                    new_content=new_content,
                    context={
                        "line_number": line_number,
                        "mode": mode,
                        "lines_added": len(normalized_code.split('\n'))
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
                f.write(new_content)
            
            # Record undo snapshot
            if self.undo_manager:
                self.undo_manager.snapshot_operation(
                    operation="insert",
                    file_path=file_path,
                    old_content=original_content,
                    new_content=new_content,
                    description=f"Inserted at line {line_number} in {file_path.name}"
                )
            
            return {
                "success": True,
                "path": str(file_path),
                "line_number": line_number,
                "mode": mode,
                "lines_added": len(normalized_code.split('\n')),
                "indentation_applied": f"{indent_count} {'spaces' if ' ' in indent_str else 'tabs'}",
                "total_lines": len(new_lines)
            }
            
        except Exception as e:
            return {"error": str(e)}
