"""Syntax validation for code files."""

import ast
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class SyntaxChecker:
    """Check syntax validity of code files."""

    @staticmethod
    def check_python(file_path: Path, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Check Python file syntax.

        Args:
            file_path: Path to the file
            content: Optional content to check (if None, reads from file)

        Returns:
            Dict with 'valid' bool and optional 'error' string
        """
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            # Try to parse the Python code
            ast.parse(content)
            return {"valid": True}
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"SyntaxError at line {e.lineno}: {e.msg}",
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error checking syntax: {str(e)}"
            }

    @staticmethod
    def check_javascript(file_path: Path, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Check JavaScript/TypeScript file syntax using Node.js.

        Args:
            file_path: Path to the file
            content: Optional content to check (if None, reads from file)

        Returns:
            Dict with 'valid' bool and optional 'error' string
        """
        try:
            # Check if node is available
            result = subprocess.run(
                ["which", "node"],
                capture_output=True,
                timeout=1
            )

            if result.returncode != 0:
                # Node not available, skip validation
                return {"valid": True, "skipped": "node not available"}

            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            # Use node to check syntax
            # This checks if the code can be parsed by V8
            check_script = f"""
            try {{
                Function({repr(content)});
                process.exit(0);
            }} catch (e) {{
                console.error('SyntaxError:', e.message);
                process.exit(1);
            }}
            """

            result = subprocess.run(
                ["node", "-e", check_script],
                capture_output=True,
                timeout=5,
                text=True
            )

            if result.returncode == 0:
                return {"valid": True}
            else:
                return {
                    "valid": False,
                    "error": result.stderr.strip()
                }
        except subprocess.TimeoutExpired:
            return {"valid": False, "error": "Syntax check timed out"}
        except Exception as e:
            return {"valid": False, "error": f"Error checking syntax: {str(e)}"}

    @staticmethod
    def check_file(file_path: Path, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Check syntax of a file based on its extension.

        Args:
            file_path: Path to the file
            content: Optional content to check (if None, reads from file)

        Returns:
            Dict with 'valid' bool and optional 'error' string
        """
        suffix = file_path.suffix.lower()

        if suffix == ".py":
            return SyntaxChecker.check_python(file_path, content)
        elif suffix in [".js", ".jsx", ".ts", ".tsx"]:
            return SyntaxChecker.check_javascript(file_path, content)
        else:
            # For other file types, assume valid
            return {"valid": True, "skipped": f"No syntax checker for {suffix}"}

    @staticmethod
    def validate_modification(
        file_path: Path,
        old_content: str,
        new_content: str
    ) -> Dict[str, Any]:
        """
        Validate that a modification doesn't break syntax.

        Args:
            file_path: Path to the file
            old_content: Original content
            new_content: New content to validate

        Returns:
            Dict with validation results and rollback recommendation
        """
        # Check if old content was valid
        old_check = SyntaxChecker.check_file(file_path, old_content)

        # Check if new content is valid
        new_check = SyntaxChecker.check_file(file_path, new_content)

        # If new content is invalid but old was valid, recommend rollback
        if not new_check["valid"] and old_check["valid"]:
            return {
                "valid": False,
                "should_rollback": True,
                "error": new_check.get("error", "Unknown syntax error"),
                "message": "Modification introduced syntax error. Recommend rollback."
            }

        # If both invalid or both valid, don't recommend rollback
        return {
            "valid": new_check["valid"],
            "should_rollback": False,
            "error": new_check.get("error"),
            "message": "Syntax check passed" if new_check["valid"] else "Syntax error detected"
        }
