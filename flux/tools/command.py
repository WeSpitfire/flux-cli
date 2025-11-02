"""Command execution tool."""

import asyncio
import subprocess
import re
from pathlib import Path
from typing import List, Any, Dict, Tuple
from flux.tools.base import Tool, ToolParameter


def validate_command_string(command: str) -> Tuple[bool, str]:
    """Validate a command string for safety and correctness.
    
    Args:
        command: The shell command to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for shell metacharacters that could enable command injection
    unsafe_chars = [';', '&&', '||', '|', '`', '$(']
    for char in unsafe_chars:
        if char in command:
            return False, f"Command contains unsafe sequence '{char}' which could enable command injection."
    
    # Check for dangerous operations
    dangerous_patterns = [
        (r'rm\s+-rf\s+/', "Command contains 'rm -rf /' which could delete system files."),
        (r'rm\s+-rf\s+\*', "Command contains 'rm -rf *' which could delete all files."),
        (r':\(\)\{', "Command contains fork bomb pattern."),
        (r'>/dev/sd', "Command attempts to write directly to disk device."),
        (r'dd\s+if=.*of=/dev', "Command uses dd to write to device - potentially dangerous."),
    ]
    
    for pattern, message in dangerous_patterns:
        if re.search(pattern, command):
            return False, message
    
    return True, "Command is safe."


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
The command runs in the current working directory."""
    
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
        """Execute command and return result."""
        try:
            # Validate command
            is_valid, validation_message = validate_command_string(command)
            if not is_valid:
                return {
                    "error": validation_message,
                    "command": command
                }

            # Run command
            process = await asyncio.create_subprocess_shell(
                command,
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
                return {
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command
                }
            
            return {
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "success": process.returncode == 0
            }
        except Exception as e:
            return {
                "error": str(e),
                "command": command
            }
