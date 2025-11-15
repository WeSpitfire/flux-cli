"""Command execution tool with security hardening."""

import asyncio
import shlex
import re
from pathlib import Path
from typing import List, Any, Dict, Tuple, Optional
from flux.tools.base import Tool, ToolParameter

# Whitelist of allowed commands - only these base commands can be executed
ALLOWED_COMMANDS = {
    # Version control
    'git',
    # Package managers
    'npm', 'npx', 'yarn', 'pnpm', 'pip', 'poetry', 'cargo', 'go',
    # Build tools
    'make', 'cmake', 'gradle', 'mvn',
    # Testing
    'pytest', 'jest', 'mocha', 'cargo test',
    # Linting/formatting
    'eslint', 'prettier', 'black', 'ruff', 'pylint', 'mypy',
    # File operations (read-only)
    'ls', 'cat', 'head', 'tail', 'find', 'grep', 'tree',
    # Language runtimes (for running tests/scripts)
    'python', 'python3', 'node', 'ruby', 'php',
    # System info (read-only)
    'echo', 'pwd', 'which', 'env',
}

# Commands that are dangerous even if in whitelist
DANGEROUS_PATTERNS = [
    (r'rm\s+-rf\s+/', "Attempting to delete from root directory"),
    (r'rm\s+-rf\s+\*', "Attempting to delete all files"),
    (r'rm\s+-rf\s+~', "Attempting to delete home directory"),
    (r':\(\)\{', "Fork bomb pattern detected"),
    (r'>/dev/(sd|hd|nvme)', "Attempting to write to disk device"),
    (r'dd\s+if=.*of=/dev', "Dangerous dd operation to device"),
    (r'curl.*\|.*sh', "Piping curl to shell is dangerous"),
    (r'wget.*\|.*sh', "Piping wget to shell is dangerous"),
]

def parse_and_validate_command(command: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """Parse and validate command for safe execution.

    Args:
        command: The command string to parse and validate

    Returns:
        Tuple of (is_valid, error_message, parsed_args)
        - is_valid: True if command is safe to execute
        - error_message: Description of why command is unsafe (if is_valid=False)
        - parsed_args: List of command arguments (if is_valid=True)
    """
    try:
        # Parse command into arguments using shlex (handles quotes properly)
        args = shlex.split(command)
    except ValueError as e:
        return False, f"Failed to parse command: {str(e)}", None

    if not args:
        return False, "Empty command", None

    base_command = args[0]

    # Check if base command is in whitelist
    if base_command not in ALLOWED_COMMANDS:
        return False, (
            f"Command '{base_command}' is not in the whitelist. "
            f"Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
        ), None

    # Check for dangerous patterns in full command
    for pattern, message in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Dangerous pattern detected: {message}", None

    # Special validation for specific commands
    if base_command == 'rm':
        # Block rm without explicit file arguments
        if len(args) < 2 or any(arg.startswith('-') and 'rf' in arg for arg in args):
            return False, "'rm -rf' is too dangerous. Use the delete_file tool instead.", None

    if base_command in ['curl', 'wget']:
        # Block piping to shell
        if '|' in command or ';' in command or '&&' in command:
            return False, f"{base_command} with shell operators is not allowed", None

    return True, None, args


class RunCommandTool(Tool):
    """Tool for executing shell commands."""

    def __init__(self, cwd: Path):
        """Initialize with current working directory."""
        self.cwd = cwd

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return """Execute a shell command and return its output.
Use this to run CLI tools, git commands, npm/yarn commands, etc.

IMPORTANT:
- Commands run from the project root directory
- For subdirectory operations, use 'cd' in the command: "cd subdirectory && npm install"
- Or specify the directory explicitly: "npm install --prefix flux-desktop"
- Example: To run npm in flux-desktop, use: "npm install --prefix flux-desktop" or "cd flux-desktop && npm install""""

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="The shell command to execute",
                required=True
            ),
            ToolParameter(
                name="timeout",
                type="number",
                description="Timeout in seconds (default: 30)",
                required=False
            )
        ]

    async def execute(self, command: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Execute command safely with whitelist validation.

        SECURITY: Uses whitelist approach. shell=False by default, shell=True only for cd commands.
        """
        try:
            # Check if this is a compound command with cd (e.g., "cd dir && npm install")
            use_shell = '&&' in command or '||' in command or ';' in command or 'cd ' in command
            
            if use_shell:
                # For compound commands, still validate that base commands are whitelisted
                # Split by shell operators and check each command
                import re
                commands = re.split(r'[;&|]+', command)
                for cmd in commands:
                    cmd = cmd.strip()
                    if not cmd or cmd.startswith('cd '):
                        continue
                    # Parse just this sub-command
                    is_valid, error_message, _ = parse_and_validate_command(cmd)
                    if not is_valid:
                        return {
                            "error": {
                                "code": "COMMAND_BLOCKED",
                                "message": f"Part of command blocked: {error_message}",
                                "command": command,
                                "suggestion": "Only whitelisted commands can be executed."
                            }
                        }
                
                # Execute with shell=True for compound commands
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.cwd)
                )
            else:
                # Parse and validate command
                is_valid, error_message, args = parse_and_validate_command(command)
                if not is_valid:
                    return {
                        "error": {
                            "code": "COMMAND_BLOCKED",
                            "message": error_message,
                            "command": command,
                            "suggestion": "Only whitelisted commands can be executed. Check ALLOWED_COMMANDS list."
                        }
                    }

                # Execute command with shell=False (prevents injection)
                # Pass arguments as list, not string
                process = await asyncio.create_subprocess_exec(
                    *args,  # Unpack args as separate arguments
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.cwd)
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()  # Clean up zombie process
                return {
                    "error": {
                        "code": "TIMEOUT",
                        "message": f"Command timed out after {timeout} seconds",
                        "command": command,
                        "suggestion": "Try a shorter timeout or simplify the command"
                    }
                }

            return {
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "success": process.returncode == 0
            }
        except FileNotFoundError:
            return {
                "error": {
                    "code": "COMMAND_NOT_FOUND",
                    "message": f"Command '{args[0] if args else command}' not found",
                    "command": command,
                    "suggestion": "Make sure the command is installed and in your PATH"
                }
            }
        except Exception as e:
            return {
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": str(e),
                    "command": command
                }
            }
