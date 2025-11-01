"""AST-aware code editing using tree-sitter."""

from pathlib import Path
from typing import List, Any, Dict, Optional
from flux.tools.base import Tool, ToolParameter
from flux.core.diff import DiffPreview
from flux.core.syntax_checker import SyntaxChecker
from flux.core.file_analyzer import FileStructureAnalyzer
from flux.core.errors import (
    file_not_found_error,
    function_exists_error,
    function_not_found_error,
    invalid_operation_error,
    syntax_error_response
)
from rich.console import Console
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Node


class ASTEditTool(Tool):
    """Tool for AST-aware code editing."""
    
    # Language mappings
    LANGUAGES = {
        '.py': ('python', Language(tspython.language())),
        '.js': ('javascript', Language(tsjavascript.language())),
        '.jsx': ('javascript', Language(tsjavascript.language())),
        '.ts': ('typescript', Language(tstypescript.language_typescript())),
        '.tsx': ('tsx', Language(tstypescript.language_tsx())),
    }
    
    def __init__(self, cwd: Path, show_diff: bool = True, undo_manager=None, workflow_enforcer=None, approval_manager=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.show_diff = show_diff
        self.undo_manager = undo_manager
        self.workflow = workflow_enforcer
        self.approval = approval_manager
        self.console = Console()
        self.diff_preview = DiffPreview(self.console)
        self.analyzer = FileStructureAnalyzer()  # File structure intelligence
    
    @property
    def name(self) -> str:
        return "ast_edit"
    
    @property
    def description(self) -> str:
        return """AST-aware editing for Python functions and imports.
        
USAGE: Python files only. For JS/TS, use edit_file instead.
OPERATIONS: add_function, remove_function, modify_function, add_import, remove_import (ONLY these 5)
BEST FOR: Adding/modifying Python functions when you know the exact structure.
ON ERROR: Tool will suggest correct operation. If it fails, use edit_file instead."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path to edit",
                required=True
            ),
            ToolParameter(
                name="operation",
                type="string",
                description="MUST be one of: 'add_function', 'remove_function', 'modify_function', 'add_import', 'remove_import'. NO OTHER VALUES ALLOWED.",
                required=True,
                enum=['add_function', 'remove_function', 'modify_function', 'add_import', 'remove_import']
            ),
            ToolParameter(
                name="target",
                type="string",
                description="Target name (function/class name for operations)",
                required=True
            ),
            ToolParameter(
                name="code",
                type="string",
                description="New code to add/replace (for add/modify operations)",
                required=False
            )
        ]
    
    async def execute(
        self,
        path: str,
        operation: str,
        target: str,
        code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute AST-aware edit."""
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.cwd / file_path
            
            if not file_path.exists():
                return file_not_found_error(str(file_path))
            
            # Check workflow enforcement
            if self.workflow:
                check = self.workflow.check_modification_allowed(file_path, "ast_edit")
                if not check["allowed"]:
                    return {
                        "error": check["reason"],
                        "suggestions": check.get("suggestions", []),
                        "workflow_blocked": True
                    }
            
            # Get language for file
            lang_info = self._get_language(file_path)
            if not lang_info:
                return {
                    "error": f"Unsupported file type: {file_path.suffix}",
                    "hint": "Supported: .py, .js, .jsx, .ts, .tsx"
                }
            
            lang_name, language = lang_info
            
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse with tree-sitter
            parser = Parser(language)
            tree = parser.parse(bytes(content, 'utf8'))
            
            # Perform operation
            result = self._perform_operation(
                content, tree, operation, target, code, lang_name
            )
            
            if result.get("error"):
                return result
            
            # Get modified content
            new_content = result["new_content"]
            
            # Show diff preview if enabled (only if no approval manager, otherwise approval shows it)
            if self.show_diff and not self.approval:
                self.diff_preview.display_compact_diff(content, new_content, file_path.name)
            
            # Validate syntax before applying
            validation = SyntaxChecker.validate_modification(
                file_path, content, new_content
            )
            
            if validation["should_rollback"]:
                return syntax_error_response(
                    validation["error"],
                    line_number=validation.get("line"),
                    rolled_back=True
                )
            
            # Request approval if approval manager is present
            if self.approval:
                additions, deletions, _ = self.diff_preview.get_change_stats(content, new_content)
                approved = self.approval.request_approval(
                    operation="ast_edit",
                    file_path=file_path,
                    old_content=content,
                    new_content=new_content,
                    context={
                        "operation": operation,
                        "target": target,
                        "changes": f"+{additions} -{deletions}",
                        "lines": f"{len(content.splitlines())} → {len(new_content.splitlines())}"
                    }
                )
                
                if not approved:
                    return {
                        "error": "Change rejected by user",
                        "rejected": True,
                        "path": str(file_path)
                    }
            
            # Record undo snapshot before writing
            if self.undo_manager:
                self.undo_manager.snapshot_operation(
                    operation="ast_edit",
                    file_path=file_path,
                    old_content=content,
                    new_content=new_content,
                    description=f"AST edit: {operation} {target} in {file_path.name}"
                )
            
            # Write modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Get change stats
            additions, deletions, modifications = self.diff_preview.get_change_stats(content, new_content)
            
            return {
                "success": True,
                "operation": operation,
                "target": target,
                "path": str(file_path),
                "changes": result.get("changes", "Content modified"),
                "diff_summary": f"+{additions} -{deletions} ~{modifications}"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_language(self, file_path: Path) -> Optional[tuple]:
        """Get language info for file."""
        suffix = file_path.suffix.lower()
        return self.LANGUAGES.get(suffix)
    
    def _perform_operation(
        self,
        content: str,
        tree: Any,
        operation: str,
        target: str,
        code: Optional[str],
        lang_name: str
    ) -> Dict[str, Any]:
        """Perform the requested AST operation."""
        
        if operation == "add_function":
            return self._add_function(content, tree, target, code, lang_name)
        elif operation == "remove_function":
            return self._remove_function(content, tree, target, lang_name)
        elif operation == "modify_function":
            return self._modify_function(content, tree, target, code, lang_name)
        elif operation == "add_import":
            return self._add_import(content, tree, target, code, lang_name)
        elif operation == "remove_import":
            return self._remove_import(content, tree, target, lang_name)
        else:
            valid_ops = ["add_function", "remove_function", "modify_function", "add_import", "remove_import"]
            return invalid_operation_error(operation, valid_ops)
    
    def _add_function(
        self,
        content: str,
        tree: Any,
        name: str,
        code: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Add a new function to the file."""
        if not code:
            return {"error": "Code parameter required for add_function"}
        
        # Use FileStructureAnalyzer for Python files to prevent duplicates
        if lang_name == 'python':
            # Extract function name from code if not provided properly
            func_name = self._extract_function_name(code) or name
            
            # Get the file path from context (we need to pass it through)
            # For now, use tree-sitter as fallback
            existing = self._find_function_node(tree.root_node, func_name, lang_name)
            if existing:
                # Get line number for helpful error
                line_num = content[:existing.start_byte].count('\n') + 1
                # Extract signature if possible
                sig_end = content.find(':', existing.start_byte)
                signature = content[existing.start_byte:sig_end+1] if sig_end > 0 else None
                return function_exists_error(func_name, line_num, signature)
        else:
            # For other languages, use existing tree-sitter check
            existing = self._find_function_node(tree.root_node, name, lang_name)
            if existing:
                line_num = content[:existing.start_byte].count('\n') + 1
                return function_exists_error(name, line_num)
        
        # Find the best insertion point
        insertion_point = self._find_insertion_point(tree.root_node, lang_name, content)
        
        # Insert the function at the proper location
        if insertion_point == len(content):
            # Add at end
            if content.strip():
                new_content = content.rstrip() + '\n\n\n' + code.strip() + '\n'
            else:
                new_content = code.strip() + '\n'
        else:
            # Insert at specific position
            new_content = (
                content[:insertion_point] +
                '\n\n' + code.strip() + '\n' +
                content[insertion_point:]
            )
        
        return {
            "new_content": new_content,
            "changes": f"Added function '{name}'"
        }
    
    def _remove_function(
        self,
        content: str,
        tree: Any,
        name: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Remove a function from the file."""
        # Find function definition node
        func_node = self._find_function_node(tree.root_node, name, lang_name)
        
        if not func_node:
            # List available functions to help
            available = self._list_functions(tree.root_node, lang_name)
            return function_not_found_error(name, available)
        
        # Remove the function's text
        start_byte = func_node.start_byte
        end_byte = func_node.end_byte
        
        new_content = (
            content[:start_byte] +
            content[end_byte:]
        )
        
        # Clean up extra blank lines
        new_content = self._clean_blank_lines(new_content)
        
        return {
            "new_content": new_content,
            "changes": f"Removed function '{name}'"
        }
    
    def _modify_function(
        self,
        content: str,
        tree: Any,
        name: str,
        code: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Modify an existing function."""
        if not code:
            return {"error": "Code parameter required for modify_function"}
        
        # Find function definition node
        func_node = self._find_function_node(tree.root_node, name, lang_name)
        
        if not func_node:
            available = self._list_functions(tree.root_node, lang_name)
            return function_not_found_error(name, available)
        
        # Replace the function's text
        start_byte = func_node.start_byte
        end_byte = func_node.end_byte
        
        new_content = (
            content[:start_byte] +
            code.strip() + '\n' +
            content[end_byte:]
        )
        
        return {
            "new_content": new_content,
            "changes": f"Modified function '{name}'"
        }
    
    def _add_import(
        self,
        content: str,
        tree: Any,
        module: str,
        code: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Add an import statement."""
        if not code:
            return {"error": "Code parameter required for add_import (the import statement)"}
        
        # Find where to insert (after existing imports or at top)
        lines = content.split('\n')
        insert_line = 0
        
        # Find last import
        for i, line in enumerate(lines):
            if lang_name == 'python' and (line.startswith('import ') or line.startswith('from ')):
                insert_line = i + 1
            elif lang_name in ['javascript', 'typescript', 'tsx'] and (line.startswith('import ') or line.startswith('const ') or line.startswith('require(')):
                insert_line = i + 1
        
        # Insert the import
        lines.insert(insert_line, code.strip())
        new_content = '\n'.join(lines)
        
        return {
            "new_content": new_content,
            "changes": f"Added import for '{module}'"
        }
    
    def _remove_import(
        self,
        content: str,
        tree: Any,
        module: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Remove an import statement."""
        lines = content.split('\n')
        new_lines = []
        removed = False
        
        for line in lines:
            # Simple text matching for import removal
            if module in line and ('import' in line or 'require' in line):
                removed = True
                continue
            new_lines.append(line)
        
        if not removed:
            return {"error": f"Import for '{module}' not found"}
        
        new_content = '\n'.join(new_lines)
        
        return {
            "new_content": new_content,
            "changes": f"Removed import for '{module}'"
        }
    
    def _find_function_node(self, node: Node, name: str, lang_name: str) -> Optional[Node]:
        """Find a function definition node by name."""
        # Node types vary by language
        if lang_name == 'python':
            func_types = ['function_definition']
            name_field = 'name'
        elif lang_name in ['javascript', 'typescript', 'tsx']:
            func_types = ['function_declaration', 'function', 'arrow_function', 'method_definition']
            name_field = 'name'
        else:
            return None
        
        # Recursively search for function
        if node.type in func_types:
            # Check if this is the function we're looking for
            for child in node.children:
                if child.type == 'identifier' and child.text.decode('utf-8') == name:
                    return node
        
        # Recurse into children
        for child in node.children:
            result = self._find_function_node(child, name, lang_name)
            if result:
                return result
        
        return None
    
    def _clean_blank_lines(self, content: str) -> str:
        """Clean up excessive blank lines."""
        lines = content.split('\n')
        cleaned = []
        blank_count = 0
        
        for line in lines:
            if line.strip():
                cleaned.append(line)
                blank_count = 0
            else:
                blank_count += 1
                if blank_count <= 2:  # Allow max 2 blank lines
                    cleaned.append(line)
        
        return '\n'.join(cleaned)
    
    def _find_insertion_point(self, node: Node, lang_name: str, content: str) -> int:
        """Find the best place to insert a new function."""
        # Find the last function or class definition
        last_definition_end = 0
        
        for child in node.children:
            if lang_name == 'python':
                if child.type in ['function_definition', 'class_definition']:
                    last_definition_end = max(last_definition_end, child.end_byte)
            elif lang_name in ['javascript', 'typescript', 'tsx']:
                if child.type in ['function_declaration', 'class_declaration']:
                    last_definition_end = max(last_definition_end, child.end_byte)
        
        # If we found definitions, insert after the last one
        if last_definition_end > 0:
            return last_definition_end
        
        # Otherwise, insert at end
        return len(content)
    
    def _extract_function_name(self, code: str) -> Optional[str]:
        """Extract function name from function definition code."""
        import ast
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        except:
            pass
        return None
    
    def _list_functions(self, node: Node, lang_name: str) -> List[str]:
        """List all function names in the file for error messages."""
        functions = []
        
        # Node types vary by language
        if lang_name == 'python':
            func_types = ['function_definition']
        elif lang_name in ['javascript', 'typescript', 'tsx']:
            func_types = ['function_declaration', 'function', 'method_definition']
        else:
            return functions
        
        def recurse(n: Node):
            if n.type in func_types:
                # Find the name identifier
                for child in n.children:
                    if child.type == 'identifier':
                        functions.append(child.text.decode('utf-8'))
                        break
            for child in n.children:
                recurse(child)
        
        recurse(node)
        return functions
