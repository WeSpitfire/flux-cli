"""Auto-fixer for safe, deterministic code improvements.

This module automatically fixes safe issues in the background without user intervention.
Only fixes that are:
1. Zero risk (no semantic changes)
2. Deterministic (not AI guesswork)
3. Easily reversible
4. Universally accepted as improvements

Examples:
- Remove unused imports
- Fix formatting (trailing whitespace, blank lines)
- Add missing semicolons (JS)
- Fix quote consistency
- Remove commented-out code (optional)
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FixType(Enum):
    """Types of auto-fixes."""
    UNUSED_IMPORT = "unused_import"
    TRAILING_WHITESPACE = "trailing_whitespace"
    BLANK_LINES = "blank_lines"
    QUOTE_CONSISTENCY = "quote_consistency"
    SEMICOLON = "semicolon"
    COMMENTED_CODE = "commented_code"


@dataclass
class AutoFix:
    """Represents an automatic fix applied to a file."""
    fix_type: FixType
    file_path: Path
    line_number: Optional[int]
    description: str
    old_content: str
    new_content: str
    reversible: bool = True


class AutoFixer:
    """Automatically fixes safe code issues in the background."""

    def __init__(self, cwd: Path, enabled: bool = True):
        """Initialize AutoFixer.

        Args:
            cwd: Current working directory
            enabled: Whether auto-fixing is enabled
        """
        self.cwd = cwd
        self.enabled = enabled
        self.fix_history: List[AutoFix] = []

        # Configuration
        self.config = {
            'fix_unused_imports': True,
            'fix_trailing_whitespace': True,
            'fix_blank_lines': True,
            'fix_quote_consistency': True,
            'fix_semicolons': False,  # JS/TS only, optional
            'remove_commented_code': False,  # Optional, can be risky
        }

    def can_auto_fix(self, file_path: Path) -> bool:
        """Check if file type is supported for auto-fixing.

        Args:
            file_path: Path to file

        Returns:
            True if file type is supported
        """
        supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yaml', '.yml'}
        return file_path.suffix in supported_extensions

    def analyze_file(self, file_path: Path) -> List[AutoFix]:
        """Analyze file for fixable issues.

        Args:
            file_path: Path to file to analyze

        Returns:
            List of potential fixes
        """
        if not self.enabled or not self.can_auto_fix(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return []

        fixes = []

        # Python-specific fixes
        if file_path.suffix == '.py':
            fixes.extend(self._detect_unused_imports_python(file_path, content))

        # Universal fixes (all file types)
        if self.config['fix_trailing_whitespace']:
            fixes.extend(self._detect_trailing_whitespace(file_path, content))

        if self.config['fix_blank_lines']:
            fixes.extend(self._detect_excessive_blank_lines(file_path, content))

        if self.config['fix_quote_consistency']:
            fixes.extend(self._detect_quote_inconsistency(file_path, content))

        return fixes

    def apply_fixes(self, file_path: Path, fixes: List[AutoFix]) -> Tuple[bool, int]:
        """Apply fixes to a file.

        Args:
            file_path: Path to file
            fixes: List of fixes to apply

        Returns:
            Tuple of (success, number of fixes applied)
        """
        if not fixes:
            return True, 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return False, 0

        # Apply fixes in order
        modified_content = content
        applied_count = 0

        for fix in fixes:
            old_content = modified_content
            modified_content = self._apply_single_fix(modified_content, fix)

            if modified_content != old_content:
                applied_count += 1
                # Store in history for undo
                self.fix_history.append(fix)

        # Write back if changes were made
        if applied_count > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                return True, applied_count
            except Exception:
                return False, 0

        return True, 0

    def _apply_single_fix(self, content: str, fix: AutoFix) -> str:
        """Apply a single fix to content.

        Args:
            content: File content
            fix: Fix to apply

        Returns:
            Modified content
        """
        if fix.fix_type == FixType.TRAILING_WHITESPACE:
            # Remove trailing whitespace from all lines
            lines = content.split('\n')
            lines = [line.rstrip() for line in lines]
            return '\n'.join(lines)

        elif fix.fix_type == FixType.BLANK_LINES:
            # Reduce multiple blank lines to maximum of 2
            return re.sub(r'\n{4,}', '\n\n\n', content)

        elif fix.fix_type == FixType.UNUSED_IMPORT:
            # Remove specific unused import line
            return content.replace(fix.old_content, fix.new_content)

        elif fix.fix_type == FixType.QUOTE_CONSISTENCY:
            # Apply quote consistency fix
            return content.replace(fix.old_content, fix.new_content)

        return content

    def _detect_unused_imports_python(self, file_path: Path, content: str) -> List[AutoFix]:
        """Detect unused imports in Python files.

        Args:
            file_path: Path to Python file
            content: File content

        Returns:
            List of unused import fixes
        """
        if not self.config['fix_unused_imports']:
            return []

        fixes = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        # Find all imports
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node.lineno

        # Find all name references
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle module.attribute access
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Find unused imports
        lines = content.split('\n')
        for import_name, line_num in imports.items():
            # Skip special imports (often used indirectly)
            if import_name in ('typing', 'Optional', 'List', 'Dict', 'Tuple', 'Any'):
                continue

            if import_name not in used_names:
                # Get the full import line
                if 0 <= line_num - 1 < len(lines):
                    old_line = lines[line_num - 1]

                    # Only remove if it's a simple single import
                    # Don't remove from multi-import lines
                    if old_line.strip().startswith('import ') or old_line.strip().startswith('from '):
                        if ',' not in old_line:  # Single import only
                            fixes.append(AutoFix(
                                fix_type=FixType.UNUSED_IMPORT,
                                file_path=file_path,
                                line_number=line_num,
                                description=f"Remove unused import: {import_name}",
                                old_content=old_line + '\n',
                                new_content='',
                                reversible=True
                            ))

        return fixes

    def _detect_trailing_whitespace(self, file_path: Path, content: str) -> List[AutoFix]:
        """Detect trailing whitespace.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            List of trailing whitespace fixes
        """
        lines = content.split('\n')
        has_trailing = any(line != line.rstrip() for line in lines)

        if has_trailing:
            return [AutoFix(
                fix_type=FixType.TRAILING_WHITESPACE,
                file_path=file_path,
                line_number=None,
                description="Remove trailing whitespace",
                old_content=content,
                new_content='\n'.join(line.rstrip() for line in lines),
                reversible=True
            )]

        return []

    def _detect_excessive_blank_lines(self, file_path: Path, content: str) -> List[AutoFix]:
        """Detect excessive blank lines (more than 2 consecutive).

        Args:
            file_path: Path to file
            content: File content

        Returns:
            List of blank line fixes
        """
        if re.search(r'\n{4,}', content):
            return [AutoFix(
                fix_type=FixType.BLANK_LINES,
                file_path=file_path,
                line_number=None,
                description="Reduce excessive blank lines",
                old_content=content,
                new_content=re.sub(r'\n{4,}', '\n\n\n', content),
                reversible=True
            )]

        return []

    def _detect_quote_inconsistency(self, file_path: Path, content: str) -> List[AutoFix]:
        """Detect quote inconsistency in strings.

        Only fixes if one style is clearly dominant (>80%).

        Args:
            file_path: Path to file
            content: File content

        Returns:
            List of quote consistency fixes
        """
        # Skip for now - too risky without proper parsing
        # Would need language-specific string detection
        return []

    def undo_last_fix(self) -> Optional[AutoFix]:
        """Undo the last auto-fix.

        Returns:
            The undone fix, or None if nothing to undo
        """
        if not self.fix_history:
            return None

        fix = self.fix_history.pop()

        try:
            # Read current content
            with open(fix.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Reverse the fix
            restored_content = content.replace(fix.new_content, fix.old_content)

            # Write back
            with open(fix.file_path, 'w', encoding='utf-8') as f:
                f.write(restored_content)

            return fix
        except Exception:
            return None

    def get_fix_summary(self) -> Dict[str, int]:
        """Get summary of fixes applied in current session.

        Returns:
            Dictionary of fix type to count
        """
        summary = {}
        for fix in self.fix_history:
            fix_type_name = fix.fix_type.value
            summary[fix_type_name] = summary.get(fix_type_name, 0) + 1
        return summary

    def clear_history(self):
        """Clear fix history."""
        self.fix_history.clear()
