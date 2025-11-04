"""Smart error parsing and auto-fix suggestion system."""

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedError:
    """Represents a parsed error from command output."""
    error_type: str  # e.g., "SyntaxError", "TypeError", "ImportError"
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion
        }


class ErrorParser:
    """
    Parse error messages from various languages and tools.

    Supports:
    - Python (tracebacks, pytest, mypy, pylint, ruff)
    - JavaScript/TypeScript (ESLint, TypeScript compiler, Jest)
    - Rust (cargo)
    - Go (go build/test)
    - General compilation errors
    """

    def __init__(self, cwd: Path):
        """Initialize error parser.

        Args:
            cwd: Current working directory for resolving relative paths
        """
        self.cwd = cwd

        # Compile regex patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for error detection."""
        # Python traceback
        self.python_traceback = re.compile(
            r'File "([^"]+)", line (\d+).*\n.*\n\s*(\w+Error|Exception): (.+)',
            re.MULTILINE
        )

        # Python single-line error
        self.python_error = re.compile(
            r'File "([^"]+)", line (\d+)(?:, in \w+)?.*\n.*\n\s*(\w+Error): (.+)'
        )

        # Pytest failure
        self.pytest_failure = re.compile(
            r'(FAILED|ERROR) (.+\.py)::(test_\w+)(?: - (.+))?'
        )

        # JavaScript/TypeScript error
        self.js_error = re.compile(
            r'(.+\.(?:js|ts|jsx|tsx)):(\d+):(\d+) - error TS(\d+): (.+)'
        )

        # ESLint error
        self.eslint_error = re.compile(
            r'(.+\.(?:js|ts|jsx|tsx))\n\s+(\d+):(\d+)\s+error\s+(.+?)\s+(\w+/[\w-]+)'
        )

        # Rust cargo error
        self.rust_error = re.compile(
            r'error\[E\d+\]: (.+)\n\s+--> (.+):(\d+):(\d+)'
        )

        # Go error
        self.go_error = re.compile(
            r'(.+\.go):(\d+):(\d+): (.+)'
        )

        # Generic error with file:line
        self.generic_error = re.compile(
            r'(.+\.(?:py|js|ts|jsx|tsx|rs|go|java|cpp|c|h)):(\d+):?(\d+)?: (.+)'
        )

        # Import error
        self.import_error = re.compile(
            r"ImportError: cannot import name ['\"](\w+)['\"] from ['\"](.+)['\"]"
        )

        # Module not found
        self.module_not_found = re.compile(
            r"ModuleNotFoundError: No module named ['\"](.+)['\"]"
        )

        # Undefined variable/name
        self.name_error = re.compile(
            r"NameError: name ['\"](\w+)['\"] is not defined"
        )

        # Type error
        self.type_error = re.compile(
            r"TypeError: (.+)"
        )

    def parse_output(self, output: str, command: str = "") -> List[ParsedError]:
        """Parse command output for errors.

        Args:
            output: Command output text
            command: The command that was run (helps with context)

        Returns:
            List of parsed errors
        """
        errors = []

        # Try language-specific parsers
        if 'python' in command.lower() or 'pytest' in command.lower() or '.py' in output:
            errors.extend(self._parse_python_errors(output))

        if 'npm' in command.lower() or 'node' in command.lower() or 'tsc' in command.lower():
            errors.extend(self._parse_js_errors(output))

        if 'cargo' in command.lower() or '.rs' in output:
            errors.extend(self._parse_rust_errors(output))

        if 'go ' in command.lower() or '.go' in output:
            errors.extend(self._parse_go_errors(output))

        # Try generic parser as fallback
        if not errors:
            errors.extend(self._parse_generic_errors(output))

        # Generate suggestions for each error
        for error in errors:
            error.suggestion = self._generate_suggestion(error)

        return errors

    def _parse_python_errors(self, output: str) -> List[ParsedError]:
        """Parse Python errors from output."""
        errors = []

        # Python tracebacks
        for match in self.python_traceback.finditer(output):
            file_path, line, error_type, message = match.groups()
            errors.append(ParsedError(
                error_type=error_type,
                message=message,
                file_path=file_path,
                line_number=int(line)
            ))

        # Pytest failures
        for match in self.pytest_failure.finditer(output):
            status, file_path, test_name, message = match.groups()
            errors.append(ParsedError(
                error_type="TestFailure",
                message=message or f"Test {test_name} failed",
                file_path=file_path
            ))

        # Import errors
        for match in self.import_error.finditer(output):
            name, module = match.groups()
            errors.append(ParsedError(
                error_type="ImportError",
                message=f"Cannot import '{name}' from '{module}'",
                suggestion=f"Check if '{name}' exists in {module} or if the import path is correct"
            ))

        # Module not found
        for match in self.module_not_found.finditer(output):
            module = match.group(1)
            errors.append(ParsedError(
                error_type="ModuleNotFoundError",
                message=f"No module named '{module}'",
                suggestion=f"Install missing module: pip install {module}"
            ))

        # Name errors
        for match in self.name_error.finditer(output):
            name = match.group(1)
            errors.append(ParsedError(
                error_type="NameError",
                message=f"Name '{name}' is not defined",
                suggestion=f"Did you forget to define or import '{name}'?"
            ))

        return errors

    def _parse_js_errors(self, output: str) -> List[ParsedError]:
        """Parse JavaScript/TypeScript errors."""
        errors = []

        # TypeScript errors
        for match in self.js_error.finditer(output):
            file_path, line, col, ts_code, message = match.groups()
            errors.append(ParsedError(
                error_type=f"TS{ts_code}",
                message=message,
                file_path=file_path,
                line_number=int(line),
                column=int(col)
            ))

        # ESLint errors
        for match in self.eslint_error.finditer(output):
            file_path, line, col, message, rule = match.groups()
            errors.append(ParsedError(
                error_type=f"ESLint:{rule}",
                message=message,
                file_path=file_path,
                line_number=int(line),
                column=int(col)
            ))

        return errors

    def _parse_rust_errors(self, output: str) -> List[ParsedError]:
        """Parse Rust cargo errors."""
        errors = []

        for match in self.rust_error.finditer(output):
            message, file_path, line, col = match.groups()
            errors.append(ParsedError(
                error_type="RustError",
                message=message,
                file_path=file_path,
                line_number=int(line),
                column=int(col)
            ))

        return errors

    def _parse_go_errors(self, output: str) -> List[ParsedError]:
        """Parse Go build/test errors."""
        errors = []

        for match in self.go_error.finditer(output):
            file_path, line, col, message = match.groups()
            errors.append(ParsedError(
                error_type="GoError",
                message=message,
                file_path=file_path,
                line_number=int(line),
                column=int(col)
            ))

        return errors

    def _parse_generic_errors(self, output: str) -> List[ParsedError]:
        """Parse generic file:line:message errors."""
        errors = []

        for match in self.generic_error.finditer(output):
            file_path, line, col, message = match.groups()
            errors.append(ParsedError(
                error_type="Error",
                message=message,
                file_path=file_path,
                line_number=int(line),
                column=int(col) if col else None
            ))

        return errors

    def _generate_suggestion(self, error: ParsedError) -> str:
        """Generate fix suggestion for an error.

        Args:
            error: Parsed error

        Returns:
            Suggestion string
        """
        # Already has suggestion from specific parser
        if error.suggestion:
            return error.suggestion

        # Import/module errors
        if "ImportError" in error.error_type or "ModuleNotFound" in error.error_type:
            if "module named" in error.message.lower():
                module = error.message.split("'")[1]
                return f"Install missing module: pip install {module}"
            return "Check import path and ensure the module/file exists"

        # Name not defined
        if "NameError" in error.error_type:
            return "Check variable name spelling or ensure it's defined/imported before use"

        # Type errors
        if "TypeError" in error.error_type:
            return "Check function arguments and types match expected signature"

        # Syntax errors
        if "SyntaxError" in error.error_type:
            return "Check code syntax - missing brackets, quotes, or colons?"

        # Attribute errors
        if "AttributeError" in error.error_type:
            return "Check if object has the attribute you're trying to access"

        # Test failures
        if "TestFailure" in error.error_type or "FAILED" in error.message:
            return "Review test expectations and actual behavior"

        # Generic suggestion
        if error.file_path and error.line_number:
            return f"Check {error.file_path}:{error.line_number} for the issue"

        return "Review the error message and fix the reported issue"

    def format_error(self, error: ParsedError, include_suggestion: bool = True) -> str:
        """Format error for display.

        Args:
            error: Parsed error
            include_suggestion: Whether to include the suggestion

        Returns:
            Formatted error string
        """
        parts = [f"[bold red]{error.error_type}[/bold red]: {error.message}"]

        if error.file_path:
            location = f"  📄 {error.file_path}"
            if error.line_number:
                location += f":{error.line_number}"
                if error.column:
                    location += f":{error.column}"
            parts.append(f"[cyan]{location}[/cyan]")

        if include_suggestion and error.suggestion:
            parts.append(f"  💡 [yellow]{error.suggestion}[/yellow]")

        return "\n".join(parts)

    def get_fix_context(self, error: ParsedError) -> Optional[Dict[str, Any]]:
        """Get context needed for LLM to generate a fix.

        Args:
            error: Parsed error

        Returns:
            Dictionary with file content, error details, etc.
        """
        if not error.file_path or not error.line_number:
            return None

        file_path = self.cwd / error.file_path if not Path(error.file_path).is_absolute() else Path(error.file_path)

        if not file_path.exists():
            return None

        try:
            # Read file and get surrounding lines
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Get context: 5 lines before and after
            start = max(0, error.line_number - 6)
            end = min(len(lines), error.line_number + 5)
            context_lines = lines[start:end]

            return {
                "file_path": str(error.file_path),
                "line_number": error.line_number,
                "error_type": error.error_type,
                "error_message": error.message,
                "code_context": "".join(context_lines),
                "start_line": start + 1,
                "end_line": end
            }

        except Exception:
            return None
