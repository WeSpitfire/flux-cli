"""Smart indentation detection and normalization utilities."""

from typing import Tuple, Optional


class IndentationHelper:
    """Helper class for detecting and normalizing indentation."""

    @staticmethod
    def detect_indentation(content: str, line_number: int) -> Tuple[str, int]:
        """
        Detect the indentation at a specific line.

        Args:
            content: File content
            line_number: Line number (1-indexed)

        Returns:
            Tuple of (indent_string, indent_count)
        """
        lines = content.split('\n')
        if line_number < 1 or line_number > len(lines):
            return ("", 0)

        line = lines[line_number - 1]
        indent = len(line) - len(line.lstrip())

        # Detect if using tabs or spaces
        if line and line[0] == '\t':
            # Count tabs
            tab_count = 0
            for char in line:
                if char == '\t':
                    tab_count += 1
                else:
                    break
            return ("\t" * tab_count, tab_count)
        else:
            # Count spaces
            return (" " * indent, indent)

    @staticmethod
    def detect_indentation_from_context(content: str,
                                        target_line: int,
                                        look_back: int = 10) -> Tuple[str, int]:
        """
        Detect expected indentation from surrounding context.

        Args:
            content: File content
            target_line: Target line number (1-indexed)
            look_back: How many lines to look back

        Returns:
            Tuple of (indent_string, indent_count)
        """
        lines = content.split('\n')

        # Look back to find a non-empty line with indentation
        start = max(0, target_line - 1 - look_back)
        for i in range(target_line - 2, start - 1, -1):
            if i >= 0 and i < len(lines) and lines[i].strip():
                line = lines[i]
                indent = len(line) - len(line.lstrip())

                # Detect tabs vs spaces
                if line and line[0] == '\t':
                    tab_count = 0
                    for char in line:
                        if char == '\t':
                            tab_count += 1
                        else:
                            break
                    return ("\t" * tab_count, tab_count)
                else:
                    return (" " * indent, indent)

        return ("", 0)

    @staticmethod
    def detect_indent_style(content: str) -> str:
        """
        Detect whether file uses tabs or spaces.

        Returns:
            "tabs", "spaces", or "mixed"
        """
        lines = content.split('\n')
        tab_lines = 0
        space_lines = 0

        for line in lines:
            if not line.strip():
                continue
            if line[0] == '\t':
                tab_lines += 1
            elif line[0] == ' ':
                space_lines += 1

        if tab_lines > space_lines * 2:
            return "tabs"
        elif space_lines > tab_lines * 2:
            return "spaces"
        else:
            return "mixed"

    @staticmethod
    def normalize_indentation(text: str,
                             target_indent_str: str,
                             target_indent_count: Optional[int] = None) -> str:
        """
        Normalize indentation of multi-line text.

        Takes text with arbitrary indentation and normalizes it to match
        the target indentation while preserving relative indentation.

        Args:
            text: Text to normalize
            target_indent_str: Target indentation string (e.g., "    " or "\\t")
            target_indent_count: Target indentation count (optional, derived from string if not provided)

        Returns:
            Normalized text
        """
        if not text or '\n' not in text:
            # Single line - just apply target indent if line is not empty
            if text.strip():
                return target_indent_str + text.lstrip()
            return text

        lines = text.split('\n')
        if not lines:
            return text

        # Find minimum indentation (ignoring empty lines)
        min_indent = float('inf')
        for line in lines:
            if line.strip():  # Ignore empty lines
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)

        if min_indent == float('inf'):
            min_indent = 0

        # Normalize each line
        normalized = []
        for line in lines:
            if not line.strip():
                # Empty line - keep empty
                normalized.append("")
            else:
                # Remove minimum indent
                stripped = line[min_indent:] if len(line) >= min_indent else line.lstrip()

                # Calculate relative indentation
                relative_indent = len(line) - len(line.lstrip()) - min_indent

                # Detect if original uses tabs or spaces
                if line and line[0] == '\t':
                    # Original uses tabs - preserve tab-based relative indent
                    if '\t' in target_indent_str:
                        # Target also uses tabs
                        relative = '\t' * (relative_indent // 4)  # Assume 4 spaces per tab
                    else:
                        # Target uses spaces, convert tabs
                        relative = ' ' * relative_indent
                else:
                    # Original uses spaces
                    if '\t' in target_indent_str:
                        # Target uses tabs, convert spaces
                        relative = '\t' * (relative_indent // 4)
                    else:
                        # Both use spaces
                        relative = ' ' * relative_indent

                # Apply target indent + relative indent
                normalized.append(target_indent_str + relative + stripped.lstrip())

        return '\n'.join(normalized)

    @staticmethod
    def count_indent(line: str) -> int:
        """
        Count indentation of a line.

        Returns:
            Number of indent units (spaces or tabs)
        """
        if not line:
            return 0

        if line[0] == '\t':
            count = 0
            for char in line:
                if char == '\t':
                    count += 1
                else:
                    break
            return count
        else:
            return len(line) - len(line.lstrip())

    @staticmethod
    def get_indent_unit(content: str) -> str:
        """
        Detect the indentation unit used in a file.

        Returns:
            The indent unit (e.g., "    " for 4 spaces, "  " for 2 spaces, "\\t" for tab)
        """
        lines = content.split('\n')
        indents = []

        # Collect indentation levels
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indents.append(indent)

        if not indents:
            return "    "  # Default to 4 spaces

        # Find GCD of all indents to determine unit size
        from math import gcd
        from functools import reduce

        if len(indents) == 1:
            unit_size = indents[0]
        else:
            unit_size = reduce(gcd, indents)

        if unit_size == 0:
            unit_size = 4

        # Check if uses tabs
        style = IndentationHelper.detect_indent_style(content)
        if style == "tabs":
            return "\t"
        else:
            return " " * unit_size
