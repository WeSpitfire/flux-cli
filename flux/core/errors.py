"""Structured error responses for tool operations."""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any


@dataclass
class ToolError:
    """Structured error response with recovery guidance."""

    code: str
    message: str
    suggestion: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
                "suggestion": self.suggestion
            }
        }
        if self.details:
            result["error"].update(self.details)
        return result


# Common error codes
class ErrorCode:
    """Standard error codes."""
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    SEARCH_TEXT_NOT_FOUND = "SEARCH_TEXT_NOT_FOUND"
    FUNCTION_EXISTS = "FUNCTION_EXISTS"
    FUNCTION_NOT_FOUND = "FUNCTION_NOT_FOUND"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    INVALID_OPERATION = "INVALID_OPERATION"
    WORKFLOW_VIOLATION = "WORKFLOW_VIOLATION"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


def file_not_found_error(path: str, similar_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Generate file not found error with suggestions."""
    details = {}
    if similar_files:
        details["similar_files"] = similar_files[:5]  # Top 5 matches

    return ToolError(
        code=ErrorCode.FILE_NOT_FOUND,
        message=f"File not found: {path}",
        suggestion="Use list_files('.') to see directory structure, or find_files to search by pattern",
        details=details if details else None
    ).to_dict()


def search_not_found_error(
    file_path: str,
    search_text: str,
    closest_match: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate search text not found error."""
    details = {}
    if closest_match:
        details["closest_match"] = closest_match

    return ToolError(
        code=ErrorCode.SEARCH_TEXT_NOT_FOUND,
        message=f"Search text not found in {file_path}",
        suggestion="Re-read the file to see current content. Whitespace and line breaks must match exactly.",
        details=details if details else None
    ).to_dict()


def function_exists_error(
    function_name: str,
    line_number: int,
    current_signature: Optional[str] = None
) -> Dict[str, Any]:
    """Generate function already exists error."""
    details = {
        "line_number": line_number
    }
    if current_signature:
        details["current_signature"] = current_signature

    return ToolError(
        code=ErrorCode.FUNCTION_EXISTS,
        message=f"Function '{function_name}' already exists at line {line_number}",
        suggestion=f"Use operation='modify_function' to update the existing function, or read the file to see what's there",
        details=details
    ).to_dict()


def function_not_found_error(
    function_name: str,
    available_functions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Generate function not found error."""
    details = {}
    if available_functions:
        details["available_functions"] = available_functions[:10]

    return ToolError(
        code=ErrorCode.FUNCTION_NOT_FOUND,
        message=f"Function '{function_name}' not found in file",
        suggestion="Use operation='add_function' to create a new function, or read the file to see available functions",
        details=details if details else None
    ).to_dict()


def syntax_error_response(
    error_message: str,
    line_number: Optional[int] = None,
    rolled_back: bool = True,
    original_content: Optional[str] = None,
    modified_content: Optional[str] = None
) -> Dict[str, Any]:
    """Generate enhanced syntax error response with indentation analysis."""
    details = {
        "rolled_back": rolled_back
    }
    if line_number:
        details["line_number"] = line_number

    # Analyze indentation if we have both contents
    suggestion = "Try edit_file instead for more precise control, or break the change into smaller steps"

    if original_content and modified_content and line_number and "indent" in error_message.lower():
        indent_analysis = _analyze_indentation_error(
            original_content,
            modified_content,
            line_number
        )
        if indent_analysis:
            details.update(indent_analysis)
            suggestion = indent_analysis.get("suggestion", suggestion)

    return ToolError(
        code=ErrorCode.SYNTAX_ERROR,
        message=f"Syntax error: {error_message}",
        suggestion=suggestion,
        details=details
    ).to_dict()


def _analyze_indentation_error(
    original: str,
    modified: str,
    error_line: int
) -> Optional[Dict[str, Any]]:
    """Analyze indentation mismatch and provide helpful context."""
    try:
        orig_lines = original.split('\n')
        mod_lines = modified.split('\n')

        if error_line > len(mod_lines) or error_line < 1:
            return None

        error_idx = error_line - 1
        error_line_text = mod_lines[error_idx] if error_idx < len(mod_lines) else ""

        # Calculate indentation
        error_indent = len(error_line_text) - len(error_line_text.lstrip())

        # Find expected indentation from previous non-empty lines
        expected_indent = None
        for i in range(error_idx - 1, max(0, error_idx - 10), -1):
            if i < len(orig_lines) and orig_lines[i].strip():
                expected_indent = len(orig_lines[i]) - len(orig_lines[i].lstrip())
                break

        # Show context around error
        context_start = max(0, error_idx - 2)
        context_end = min(len(mod_lines), error_idx + 3)

        context_lines = []
        for i in range(context_start, context_end):
            if i < len(mod_lines):
                marker = " ❌" if i == error_idx else ""
                indent_spaces = len(mod_lines[i]) - len(mod_lines[i].lstrip())
                context_lines.append(
                    f"  {i+1:3d}|{mod_lines[i][:80]}{marker}  (indent: {indent_spaces} spaces)"
                )

        # Build helpful suggestion
        if expected_indent is not None:
            indent_diff = error_indent - expected_indent
            if indent_diff > 0:
                direction = f"Remove {indent_diff} spaces"
            elif indent_diff < 0:
                direction = f"Add {-indent_diff} spaces"
            else:
                direction = "Check context"

            suggestion = (
                f"Indentation mismatch at line {error_line}. "
                f"Expected: {expected_indent} spaces (to match surrounding code), "
                f"Got: {error_indent} spaces. "
                f"{direction} to fix. "
                f"Read lines {context_start+1}-{context_end} to see the exact indentation pattern."
            )
        else:
            suggestion = (
                f"Indentation error at line {error_line}. "
                f"Current indent: {error_indent} spaces. "
                f"Read lines {context_start+1}-{context_end} to see the correct indentation."
            )

        return {
            "indentation_error": True,
            "expected_indent": expected_indent,
            "actual_indent": error_indent,
            "context": "\n".join(context_lines),
            "context_range": f"{context_start+1}-{context_end}",
            "suggestion": suggestion
        }

    except Exception:
        return None


def invalid_operation_error(
    operation: str,
    valid_operations: List[str]
) -> Dict[str, Any]:
    """Generate invalid operation error."""
    return ToolError(
        code=ErrorCode.INVALID_OPERATION,
        message=f"Invalid operation: '{operation}'",
        suggestion=f"Valid operations are: {', '.join(valid_operations)}",
        details={"valid_operations": valid_operations}
    ).to_dict()


def workflow_violation_error(
    file_path: str,
    reason: str,
    suggestions: List[str]
) -> Dict[str, Any]:
    """Generate workflow violation error."""
    return ToolError(
        code=ErrorCode.WORKFLOW_VIOLATION,
        message=f"Cannot modify {file_path}: {reason}",
        suggestion=suggestions[0] if suggestions else "Read the file before modifying it",
        details={"all_suggestions": suggestions} if len(suggestions) > 1 else None
    ).to_dict()
