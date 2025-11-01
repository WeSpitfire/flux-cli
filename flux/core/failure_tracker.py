"""Track tool failures and suggest alternative strategies."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolFailure:
    """Record of a tool failure."""
    tool_name: str
    error_code: Optional[str]
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    input_params: Optional[Dict] = None


class FailureTracker:
    """Track tool failures and detect retry loops."""
    
    def __init__(self):
        """Initialize failure tracker."""
        self.failures: List[ToolFailure] = []
        self.failure_count_by_tool: Dict[str, int] = {}
    
    def record_failure(self, 
                      tool_name: str,
                      error_code: Optional[str],
                      error_message: str,
                      input_params: Optional[Dict] = None) -> None:
        """Record a tool failure."""
        failure = ToolFailure(
            tool_name=tool_name,
            error_code=error_code,
            error_message=error_message,
            input_params=input_params
        )
        self.failures.append(failure)
        
        # Update count
        self.failure_count_by_tool[tool_name] = self.failure_count_by_tool.get(tool_name, 0) + 1
    
    def get_recent_failures(self, tool_name: str, limit: int = 5) -> List[ToolFailure]:
        """Get recent failures for a specific tool."""
        tool_failures = [f for f in self.failures if f.tool_name == tool_name]
        return tool_failures[-limit:]
    
    def is_retry_loop(self, tool_name: str, threshold: int = 2) -> bool:
        """Check if we're in a retry loop."""
        return self.failure_count_by_tool.get(tool_name, 0) >= threshold
    
    def get_retry_guidance(self, tool_name: str) -> Optional[str]:
        """Get guidance for breaking out of retry loop."""
        if not self.is_retry_loop(tool_name):
            return None
        
        recent_failures = self.get_recent_failures(tool_name)
        if not recent_failures:
            return None
        
        # Get the most recent error
        latest = recent_failures[-1]
        error_code = latest.error_code or ""
        
        # Generate specific guidance based on tool and error
        if tool_name == "edit_file":
            if "SYNTAX_ERROR" in error_code or "indent" in latest.error_message.lower():
                return self._edit_file_indentation_guidance(latest)
            elif "SEARCH_TEXT_NOT_FOUND" in error_code:
                return self._edit_file_search_guidance(latest)
            else:
                return self._edit_file_general_guidance()
        
        elif tool_name == "ast_edit":
            return self._ast_edit_guidance(latest)
        
        elif tool_name == "write_file":
            if "SYNTAX_ERROR" in error_code:
                return self._write_file_syntax_guidance(latest)
        
        # General fallback
        return (
            f"**RETRY LOOP DETECTED**: {tool_name} has failed {len(recent_failures)} times in a row.\n\n"
            f"**STOP** repeating the same approach. Try a completely different strategy:\n"
            f"1. Read MORE context to understand the issue\n"
            f"2. Break the change into smaller steps\n"
            f"3. Use a different tool\n"
            f"4. Ask for clarification if unclear\n"
        )
    
    def _edit_file_indentation_guidance(self, failure: ToolFailure) -> str:
        """Specific guidance for edit_file indentation errors."""
        return (
            f"**INDENTATION ERROR LOOP DETECTED**: edit_file has failed {self.failure_count_by_tool['edit_file']} times with indentation errors.\n\n"
            f"The text-based edit_file tool is **failing because of whitespace**. Try these alternatives:\n\n"
            f"**Option 1: Read More Context (Recommended)**\n"
            f"```\n"
            f"Use read_files to see a WIDER range of lines around your target.\n"
            f"Look at the EXACT indentation (count spaces/tabs) of surrounding code.\n"
            f"Copy the EXACT indentation pattern.\n"
            f"```\n\n"
            f"**Option 2: Use AST Editing (Python only)**\n"
            f"```\n"
            f"For Python files, use ast_edit tool instead.\n"
            f"It handles indentation automatically and is more reliable.\n"
            f"```\n\n"
            f"**Option 3: Break Into Smaller Steps**\n"
            f"```\n"
            f"Instead of adding multiple lines at once:\n"
            f"1. First, add just the 'if' statement\n"
            f"2. Then add the content inside\n"
            f"3. Then add the 'continue'\n"
            f"```\n\n"
            f"**DO NOT** try edit_file again with the same approach!\n"
        )
    
    def _edit_file_search_guidance(self, failure: ToolFailure) -> str:
        """Guidance for edit_file search not found errors."""
        return (
            f"**SEARCH NOT FOUND LOOP**: edit_file can't find your search text.\n\n"
            f"The search string you're using doesn't match the file EXACTLY.\n\n"
            f"**Try these steps:**\n\n"
            f"1. **Read the file again**: Use read_files to see current content\n"
            f"2. **Copy exact text**: Copy/paste EXACTLY from the read output\n"
            f"   - Include ALL whitespace\n"
            f"   - Match line breaks exactly\n"
            f"   - Check for hidden characters\n"
            f"3. **Make search more specific**: Add more context lines to make it unique\n\n"
            f"**Common issues:**\n"
            f"- Missing or extra spaces\n"
            f"- Different line endings (\\n vs \\r\\n)\n"
            f"- Tabs vs spaces\n"
            f"- Text has changed since last read\n"
        )
    
    def _edit_file_general_guidance(self) -> str:
        """General guidance for edit_file failures."""
        return (
            f"**EDIT_FILE FAILURE LOOP**: This approach isn't working.\n\n"
            f"**Try a different strategy:**\n\n"
            f"1. **Verify file content**: Re-read the file to see current state\n"
            f"2. **Smaller changes**: Edit 3-5 lines at a time instead of large blocks\n"
            f"3. **Alternative tool**: Try ast_edit for Python or write_file for new files\n"
            f"4. **Manual fix**: If stuck, explain what you tried and ask for help\n"
        )
    
    def _ast_edit_guidance(self, failure: ToolFailure) -> str:
        """Guidance for ast_edit failures."""
        return (
            f"**AST_EDIT FAILURE LOOP**: AST editing isn't working.\n\n"
            f"**Fallback to edit_file:**\n"
            f"1. Read the file with read_files\n"
            f"2. Use edit_file with EXACT text matching\n"
            f"3. Copy indentation from surrounding code\n\n"
            f"AST editing may fail if:\n"
            f"- Syntax is already broken\n"
            f"- File is not valid Python\n"
            f"- Target location is ambiguous\n"
        )
    
    def _write_file_syntax_guidance(self, failure: ToolFailure) -> str:
        """Guidance for write_file syntax errors."""
        return (
            f"**WRITE_FILE SYNTAX ERROR**: The file you're creating has syntax errors.\n\n"
            f"**Fix the content:**\n"
            f"1. Check for indentation consistency (all spaces or all tabs)\n"
            f"2. Verify brackets/parens are balanced\n"
            f"3. Check for missing colons (:) in Python\n"
            f"4. Validate string quotes are closed\n\n"
            f"**Or break it down:**\n"
            f"1. Create a minimal valid file first\n"
            f"2. Use edit_file to add functionality piece by piece\n"
        )
    
    def reset(self) -> None:
        """Reset failure tracking (e.g., after successful operation)."""
        self.failures.clear()
        self.failure_count_by_tool.clear()
    
    def clear_tool_failures(self, tool_name: str) -> None:
        """Clear failures for a specific tool (e.g., after success)."""
        self.failures = [f for f in self.failures if f.tool_name != tool_name]
        if tool_name in self.failure_count_by_tool:
            del self.failure_count_by_tool[tool_name]
