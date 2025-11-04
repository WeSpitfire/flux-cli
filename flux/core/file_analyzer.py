"""
File Structure Analyzer - Prevents duplicate code and provides file intelligence

This analyzer parses Python files to extract complete structure information,
enabling tools to make informed decisions about code modifications.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict


@dataclass
class MethodInfo:
    """Information about a class method"""
    name: str
    line_number: int
    end_line: int
    args: List[str]
    decorators: List[str] = field(default_factory=list)
    is_property: bool = False
    is_staticmethod: bool = False
    is_classmethod: bool = False


@dataclass
class ClassInfo:
    """Information about a class"""
    name: str
    line_number: int
    end_line: int
    methods: List[MethodInfo] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)

    @property
    def method_names(self) -> List[str]:
        return [m.name for m in self.methods]

    @property
    def last_method_line(self) -> int:
        """Line number of the last method in the class"""
        if not self.methods:
            return self.line_number
        return max(m.end_line for m in self.methods)

    def get_method(self, name: str) -> Optional[MethodInfo]:
        """Get method by name"""
        for method in self.methods:
            if method.name == name:
                return method
        return None


@dataclass
class FunctionInfo:
    """Information about a top-level function"""
    name: str
    line_number: int
    end_line: int
    args: List[str]
    decorators: List[str] = field(default_factory=list)


@dataclass
class ImportInfo:
    """Information about an import"""
    module: str
    names: List[str]  # Empty for 'import x', populated for 'from x import y'
    line_number: int


@dataclass
class FileStructure:
    """Complete structure of a Python file"""
    file_path: Path
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    total_lines: int = 0

    @property
    def class_names(self) -> List[str]:
        return [c.name for c in self.classes]

    @property
    def function_names(self) -> List[str]:
        return [f.name for f in self.functions]

    @property
    def all_function_names(self) -> List[str]:
        """All function names including methods in classes"""
        names = self.function_names.copy()
        for cls in self.classes:
            names.extend(cls.method_names)
        return names

    @property
    def last_definition_line(self) -> int:
        """Line number of the last class or function definition"""
        last_line = 0
        if self.classes:
            last_line = max(last_line, max(c.end_line for c in self.classes))
        if self.functions:
            last_line = max(last_line, max(f.end_line for f in self.functions))
        return last_line

    def get_class(self, name: str) -> Optional[ClassInfo]:
        """Get class by name"""
        for cls in self.classes:
            if cls.name == name:
                return cls
        return None

    def get_function(self, name: str) -> Optional[FunctionInfo]:
        """Get function by name"""
        for func in self.functions:
            if func.name == name:
                return func
        return None


class FileStructureAnalyzer:
    """
    Analyzes Python files to extract complete structure information.

    This analyzer provides the intelligence needed to:
    - Detect duplicate functions/methods/classes
    - Find proper insertion points for new code
    - Understand file organization and dependencies
    - Validate that methods/functions exist before calling them
    """

    def analyze(self, file_path: Path) -> FileStructure:
        """
        Analyze a Python file and return its complete structure.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            FileStructure with all classes, functions, imports

        Raises:
            SyntaxError: If file has invalid Python syntax
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python syntax in {file_path}: {e}")

        structure = FileStructure(
            file_path=file_path,
            total_lines=len(content.splitlines())
        )

        # Extract all top-level nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                structure.classes.append(self._extract_class_info(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods)
                if self._is_top_level(node, tree):
                    structure.functions.append(self._extract_function_info(node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                structure.imports.append(self._extract_import_info(node))

        return structure

    def can_add_function(self, file_path: Path, func_name: str,
                        target_class: Optional[str] = None) -> tuple[bool, str]:
        """
        Check if a function/method can be added without conflicts.

        Args:
            file_path: Path to file
            func_name: Name of function to add
            target_class: If adding to a class, the class name

        Returns:
            Tuple of (can_add: bool, message: str)
        """
        structure = self.analyze(file_path)

        if target_class:
            cls = structure.get_class(target_class)
            if not cls:
                return False, f"Class '{target_class}' not found in {file_path.name}"

            if func_name in cls.method_names:
                method = cls.get_method(func_name)
                return False, (
                    f"Method '{func_name}' already exists in class '{target_class}' "
                    f"at line {method.line_number}. Use modify_function instead."
                )
        else:
            if func_name in structure.function_names:
                func = structure.get_function(func_name)
                return False, (
                    f"Function '{func_name}' already exists at line {func.line_number}. "
                    f"Use modify_function instead."
                )

        return True, "OK"

    def find_best_insertion_point(self, file_path: Path,
                                  target_class: Optional[str] = None) -> int:
        """
        Find the best line number to insert new code.

        Args:
            file_path: Path to file
            target_class: If adding to a class, the class name

        Returns:
            Line number where new code should be inserted
        """
        structure = self.analyze(file_path)

        if target_class:
            cls = structure.get_class(target_class)
            if cls:
                # Insert after last method, or after class definition if no methods
                return cls.last_method_line + 1
            else:
                # Class not found, append to end
                return structure.total_lines + 1
        else:
            # Insert after last top-level definition
            if structure.last_definition_line > 0:
                return structure.last_definition_line + 2  # Extra line for spacing
            else:
                # Empty file or only imports
                return structure.total_lines + 1

    def _extract_class_info(self, node: ast.ClassDef) -> ClassInfo:
        """Extract information from a class definition"""
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_function_info(item)
                # Convert to MethodInfo
                methods.append(MethodInfo(
                    name=method_info.name,
                    line_number=method_info.line_number,
                    end_line=method_info.end_line,
                    args=method_info.args,
                    decorators=method_info.decorators,
                    is_property='property' in method_info.decorators,
                    is_staticmethod='staticmethod' in method_info.decorators,
                    is_classmethod='classmethod' in method_info.decorators
                ))

        base_classes = [self._get_name(base) for base in node.bases]

        return ClassInfo(
            name=node.name,
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            methods=methods,
            base_classes=base_classes
        )

    def _extract_function_info(self, node: ast.FunctionDef) -> FunctionInfo:
        """Extract information from a function definition"""
        args = [arg.arg for arg in node.args.args]
        decorators = [self._get_name(dec) for dec in node.decorator_list]

        return FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            args=args,
            decorators=decorators
        )

    def _extract_import_info(self, node) -> ImportInfo:
        """Extract information from an import statement"""
        if isinstance(node, ast.Import):
            # import x, y, z
            return ImportInfo(
                module=node.names[0].name,
                names=[],
                line_number=node.lineno
            )
        else:  # ast.ImportFrom
            # from x import y, z
            return ImportInfo(
                module=node.module or '',
                names=[alias.name for alias in node.names],
                line_number=node.lineno
            )

    def _is_top_level(self, node, tree: ast.Module) -> bool:
        """Check if a function is top-level (not a method)"""
        for item in tree.body:
            if item is node:
                return True
            if isinstance(item, ast.ClassDef):
                if node in item.body:
                    return False
        return False

    def _get_name(self, node) -> str:
        """Extract name from various AST nodes"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        else:
            return str(node)
