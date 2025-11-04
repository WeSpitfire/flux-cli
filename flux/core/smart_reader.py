"""Smart file reading with context management."""

from pathlib import Path
from typing import List, Optional, Dict, Any
from tree_sitter_python._binding import language as python_language
from tree_sitter_javascript._binding import language as javascript_language  
from tree_sitter_typescript._binding import language_typescript, language_tsx
from tree_sitter import Parser


class SmartReader:
    """Intelligently reads portions of files to save tokens."""

    # Language mappings (same as AST tool)
    LANGUAGES = {
        '.py': ('python', python_language()),
        '.js': ('javascript', javascript_language()),
        '.jsx': ('javascript', javascript_language()),
        '.ts': ('typescript', language_typescript()),
        '.tsx': ('tsx', language_tsx()),
    }

    def read_function(self, file_path: Path, function_name: str) -> Optional[str]:
        """Read only a specific function from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lang_info = self._get_language(file_path)
            if not lang_info:
                return None

            lang_name, language = lang_info
            parser = Parser(language)
            tree = parser.parse(bytes(content, 'utf8'))

            # Find the function
            for node in self._walk_tree(tree.root_node):
                if node.type == 'function_definition' and lang_name == 'python':
                    name_node = node.child_by_field_name('name')
                    if name_node and name_node.text.decode('utf-8') == function_name:
                        return node.text.decode('utf-8')
                elif node.type == 'function_declaration' and lang_name in ['javascript', 'typescript']:
                    name_node = node.child_by_field_name('name')
                    if name_node and name_node.text.decode('utf-8') == function_name:
                        return node.text.decode('utf-8')

            return None
        except Exception:
            return None

    def read_class(self, file_path: Path, class_name: str) -> Optional[str]:
        """Read only a specific class from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lang_info = self._get_language(file_path)
            if not lang_info:
                return None

            lang_name, language = lang_info
            parser = Parser(language)
            tree = parser.parse(bytes(content, 'utf8'))

            # Find the class
            for node in self._walk_tree(tree.root_node):
                if node.type == 'class_definition' and lang_name == 'python':
                    name_node = node.child_by_field_name('name')
                    if name_node and name_node.text.decode('utf-8') == class_name:
                        return node.text.decode('utf-8')
                elif node.type == 'class_declaration' and lang_name in ['javascript', 'typescript', 'tsx']:
                    name_node = node.child_by_field_name('name')
                    if name_node and name_node.text.decode('utf-8') == class_name:
                        return node.text.decode('utf-8')

            return None
        except Exception:
            return None

    def read_classes(self, file_path: Path, class_names: List[str]) -> Dict[str, Optional[str]]:
        """Read multiple classes from a file at once.

        Args:
            file_path: Path to the file
            class_names: List of class names to read

        Returns:
            Dictionary mapping class names to their code (or None if not found)
        """
        result = {}
        for class_name in class_names:
            result[class_name] = self.read_class(file_path, class_name)
        return result

    def read_lines(self, file_path: Path, start: int, end: int) -> str:
        """Read specific line range.

        Args:
            file_path: Path to the file
            start: Starting line number (1-indexed)
            end: Ending line number (inclusive)

        Returns:
            Content of the specified line range
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return ''.join(lines[start-1:end])
        except Exception:
            return ""

    def read_line_range(self, file_path: Path, start: int, end: int) -> str:
        """Alias for read_lines for backward compatibility."""
        return self.read_lines(file_path, start, end)

    def summarize_file(self, file_path: Path, max_lines: int = 50) -> str:
        """Create a summary of file structure."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            lang_info = self._get_language(file_path)
            if not lang_info:
                # Non-code file, just show first N lines
                preview = '\n'.join(lines[:max_lines])
                if len(lines) > max_lines:
                    preview += f"\n... ({len(lines) - max_lines} more lines)"
                return preview

            lang_name, language = lang_info
            parser = Parser(language)
            tree = parser.parse(bytes(content, 'utf8'))

            summary = f"File: {file_path.name} ({len(lines)} lines)\n"

            # Extract functions and classes
            functions = []
            classes = []

            for node in self._walk_tree(tree.root_node):
                if lang_name == 'python':
                    if node.type == 'function_definition':
                        name_node = node.child_by_field_name('name')
                        if name_node:
                            functions.append(name_node.text.decode('utf-8'))
                    elif node.type == 'class_definition':
                        name_node = node.child_by_field_name('name')
                        if name_node:
                            classes.append(name_node.text.decode('utf-8'))

            if classes:
                summary += f"Classes: {', '.join(classes[:10])}\n"
            if functions:
                summary += f"Functions: {', '.join(functions[:10])}\n"

            return summary
        except Exception:
            return f"File: {file_path.name} (unable to parse)"

    def _get_language(self, file_path: Path):
        """Get language info for file."""
        suffix = file_path.suffix.lower()
        return self.LANGUAGES.get(suffix)

    def _walk_tree(self, node):
        """Walk AST tree recursively."""
        yield node
        for child in node.children:
            yield from self._walk_tree(child)
