"""Import analyzer to detect missing imports and verify function availability."""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class ImportAnalyzer:
    """Analyzes Python files for import issues and missing dependencies."""
    
    def __init__(self, project_root: Path):
        """Initialize analyzer with project root directory.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.module_cache: Dict[str, Set[str]] = {}
    
    def analyze_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze a Python file for import issues.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with analysis results including:
            - missing_imports: List of functions used but not imported
            - unused_imports: List of imported but unused symbols
            - suggestions: List of import suggestions
            - errors: List of errors encountered
        """
        result = {
            "file": str(file_path),
            "missing_imports": [],
            "unused_imports": [],
            "suggestions": [],
            "errors": [],
            "is_valid": True
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(file_path))
            
            # Extract imports and used symbols
            imports = self._extract_imports(tree)
            used_symbols = self._extract_used_symbols(tree)
            defined_symbols = self._extract_defined_symbols(tree)
            
            # Common builtins to skip
            common_builtins = {
                'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
                'len', 'range', 'print', 'input', 'open', 'file',
                'True', 'False', 'None', 'type', 'isinstance', 'issubclass',
                'object', 'super', 'property', 'classmethod', 'staticmethod'
            }
            
            # Find missing imports
            for symbol in used_symbols:
                if (symbol not in imports and 
                    symbol not in defined_symbols and 
                    symbol not in common_builtins and
                    symbol not in dir(__builtins__)):
                    # Try to find where this symbol might come from
                    suggestion = self._suggest_import(symbol, file_path)
                    result["missing_imports"].append({
                        "symbol": symbol,
                        "suggestion": suggestion
                    })
                    result["is_valid"] = False
            
            # Find unused imports
            for symbol in imports:
                if symbol not in used_symbols and not symbol.startswith('_'):
                    result["unused_imports"].append(symbol)
            
            # Generate suggestions
            if result["missing_imports"]:
                for missing in result["missing_imports"]:
                    if missing["suggestion"]:
                        result["suggestions"].append(
                            f"Add: {missing['suggestion']}"
                        )
        
        except SyntaxError as e:
            result["errors"].append({
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno
            })
            result["is_valid"] = False
        
        except Exception as e:
            result["errors"].append({
                "type": type(e).__name__,
                "message": str(e)
            })
            result["is_valid"] = False
        
        return result
    
    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """Extract all imported symbols from AST."""
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.add(name)
            
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == '*':
                        # Handle star imports (less precise)
                        continue
                    name = alias.asname if alias.asname else alias.name
                    imports.add(name)
        
        return imports
    
    def _extract_used_symbols(self, tree: ast.AST) -> Set[str]:
        """Extract all symbols (functions, classes) used in the code."""
        used = set()
        
        # Track annotation contexts to skip them
        annotation_nodes = set()
        for node in ast.walk(tree):
            # Skip type annotations
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns:
                    annotation_nodes.add(id(node.returns))
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    if arg.annotation:
                        annotation_nodes.add(id(arg.annotation))
            elif isinstance(node, ast.AnnAssign):
                if node.annotation:
                    annotation_nodes.add(id(node.annotation))
        
        # Extract actually used symbols (excluding annotations)
        for node in ast.walk(tree):
            # Skip if this node is part of an annotation
            if id(node) in annotation_nodes:
                continue
            
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Load, ast.Del)):
                used.add(node.id)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    used.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    # For module.function() calls
                    if isinstance(node.func.value, ast.Name):
                        used.add(node.func.value.id)
        
        return used
    
    def _extract_defined_symbols(self, tree: ast.AST) -> Set[str]:
        """Extract all symbols defined in this file."""
        defined = set()
        
        for node in ast.walk(tree):
            # Functions, classes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
                # Add function parameters
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in node.args.args:
                        defined.add(arg.arg)
                    for arg in node.args.posonlyargs:
                        defined.add(arg.arg)
                    for arg in node.args.kwonlyargs:
                        defined.add(arg.arg)
                    if node.args.vararg:
                        defined.add(node.args.vararg.arg)
                    if node.args.kwarg:
                        defined.add(node.args.kwarg.arg)
            
            # Variable assignments
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined.add(target.id)
            
            # For loops
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    defined.add(node.target.id)
            
            # With statements
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        defined.add(item.optional_vars.id)
            
            # Exception handlers
            elif isinstance(node, ast.ExceptHandler):
                if node.name:
                    defined.add(node.name)
        
        return defined
    
    def _suggest_import(self, symbol: str, file_path: Path) -> Optional[str]:
        """Suggest an import statement for a missing symbol.
        
        Args:
            symbol: The symbol to find
            file_path: Path to the file using the symbol
            
        Returns:
            Suggested import statement or None
        """
        # Common standard library imports
        stdlib_suggestions = {
            'Path': 'from pathlib import Path',
            'Dict': 'from typing import Dict',
            'List': 'from typing import List',
            'Optional': 'from typing import Optional',
            'Tuple': 'from typing import Tuple',
            'asyncio': 'import asyncio',
            'json': 'import json',
            're': 'import re',
            'os': 'import os',
            'sys': 'import sys',
            'datetime': 'from datetime import datetime',
            'time': 'import time',
        }
        
        if symbol in stdlib_suggestions:
            return stdlib_suggestions[symbol]
        
        # Search project files for this symbol
        suggestion = self._search_project_for_symbol(symbol, file_path)
        if suggestion:
            return suggestion
        
        return None
    
    def _search_project_for_symbol(self, symbol: str, current_file: Path) -> Optional[str]:
        """Search project files to find where a symbol is defined.
        
        Args:
            symbol: Symbol to find
            current_file: File that needs the import
            
        Returns:
            Import statement or None
        """
        try:
            # Search Python files in project
            for py_file in self.project_root.rglob('*.py'):
                if py_file == current_file:
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    tree = ast.parse(source)
                    defined = self._extract_defined_symbols(tree)
                    
                    if symbol in defined:
                        # Convert file path to module path
                        rel_path = py_file.relative_to(self.project_root)
                        module_path = str(rel_path.with_suffix('')).replace('/', '.')
                        
                        return f"from {module_path} import {symbol}"
                
                except Exception:
                    continue
        
        except Exception:
            pass
        
        return None
    
    def check_function_callable(self, file_path: Path, function_name: str) -> Tuple[bool, Optional[str]]:
        """Check if a function can be called in a file.
        
        Args:
            file_path: Path to the file
            function_name: Name of the function to check
            
        Returns:
            Tuple of (is_callable, error_message)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(file_path))
            
            imports = self._extract_imports(tree)
            defined = self._extract_defined_symbols(tree)
            
            # Check if function is available
            if function_name in imports or function_name in defined:
                return True, None
            
            # Check if it's a builtin
            if function_name in dir(__builtins__):
                return True, None
            
            # Function not found
            suggestion = self._suggest_import(function_name, file_path)
            if suggestion:
                return False, f"Function '{function_name}' not found. Suggestion: {suggestion}"
            else:
                return False, f"Function '{function_name}' not found and no import suggestion available."
        
        except Exception as e:
            return False, f"Error checking function: {str(e)}"
    
    def validate_imports_in_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate all imports in a file can be resolved.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(file_path))
            
            # Check each import
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._can_import_module(alias.name):
                            errors.append(f"Cannot import module '{alias.name}'")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self._can_import_module(node.module):
                        errors.append(f"Cannot import from module '{node.module}'")
        
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        
        except Exception as e:
            errors.append(f"Error validating imports: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _can_import_module(self, module_name: str) -> bool:
        """Check if a module can be imported.
        
        Args:
            module_name: Name of the module
            
        Returns:
            True if module can be imported
        """
        # Check if already imported
        if module_name in sys.modules:
            return True
        
        # Try to import (without actually importing)
        try:
            # Check standard library and installed packages
            import importlib.util
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            # Check if it's a project module
            module_path = self.project_root / module_name.replace('.', '/')
            return module_path.with_suffix('.py').exists() or (module_path / '__init__.py').exists()
