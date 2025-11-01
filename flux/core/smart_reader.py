"""Smart file reading with context management."""

from pathlib import Path
from typing import List, Optional, Dict, Any
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript  
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser


class SmartReader:
    """Intelligently reads portions of files to save tokens."""
    
    # Language mappings (same as AST tool)
    LANGUAGES = {
        '.py': ('python', Language(tspython.language())),
        '.js': ('javascript', Language(tsjavascript.language())),
        '.jsx': ('javascript', Language(tsjavascript.language())),
        '.ts': ('typescript', Language(tstypescript.language_typescript())),
        '.tsx': ('tsx', Language(tstypescript.language_tsx())),
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
            
            return None
        except Exception:
            return None
    
    def read_lines(self, file_path: Path, start: int, end: int) -> str:
        """Read specific line range."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return ''.join(lines[start-1:end])
        except Exception:
            return ""
    
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
