"""Code validator service to validate changes before task completion."""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from flux.core.import_analyzer import ImportAnalyzer
from flux.core.syntax_checker import SyntaxChecker


class ValidationResult:
    """Result of code validation."""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.suggestions: List[str] = []
        self.files_checked: List[str] = []
    
    def add_error(self, file: str, message: str, line: Optional[int] = None):
        """Add an error to the result."""
        self.is_valid = False
        self.errors.append({
            "file": file,
            "message": message,
            "line": line
        })
    
    def add_warning(self, file: str, message: str, line: Optional[int] = None):
        """Add a warning to the result."""
        self.warnings.append({
            "file": file,
            "message": message,
            "line": line
        })
    
    def add_suggestion(self, suggestion: str):
        """Add a suggestion to the result."""
        self.suggestions.append(suggestion)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "files_checked": self.files_checked,
            "summary": self.get_summary()
        }
    
    def get_summary(self) -> str:
        """Get a summary string."""
        if self.is_valid:
            return f"✓ All {len(self.files_checked)} files validated successfully"
        else:
            return f"✗ Validation failed: {len(self.errors)} errors, {len(self.warnings)} warnings"


class CodeValidator:
    """Validates code changes before task completion."""
    
    def __init__(self, project_root: Path):
        """Initialize validator.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.import_analyzer = ImportAnalyzer(project_root)
    
    def validate_before_completion(self, modified_files: List[Path]) -> ValidationResult:
        """Run all validation checks before completing a task.
        
        Args:
            modified_files: List of files that were modified
            
        Returns:
            ValidationResult with all check results
        """
        result = ValidationResult()
        
        for file_path in modified_files:
            if not file_path.exists():
                result.add_error(str(file_path), "File does not exist")
                continue
            
            # Only validate Python files
            if file_path.suffix != '.py':
                continue
            
            result.files_checked.append(str(file_path))
            
            # 1. Syntax check
            syntax_valid, syntax_error = self._check_syntax(file_path)
            if not syntax_valid:
                result.add_error(
                    str(file_path),
                    f"Syntax error: {syntax_error}",
                    line=getattr(syntax_error, 'lineno', None) if hasattr(syntax_error, 'lineno') else None
                )
                continue  # Skip other checks if syntax is invalid
            
            # 2. Import validation
            import_result = self.import_analyzer.analyze_file(file_path)
            if not import_result["is_valid"]:
                for missing in import_result["missing_imports"]:
                    result.add_error(
                        str(file_path),
                        f"Missing import for symbol '{missing['symbol']}'"
                    )
                    if missing["suggestion"]:
                        result.add_suggestion(f"{file_path.name}: {missing['suggestion']}")
            
            # 3. Import resolution check
            imports_valid, import_errors = self.import_analyzer.validate_imports_in_file(file_path)
            if not imports_valid:
                for error in import_errors:
                    result.add_error(str(file_path), error)
            
            # 4. Check for unused imports (warning only)
            if import_result["unused_imports"]:
                result.add_warning(
                    str(file_path),
                    f"Unused imports: {', '.join(import_result['unused_imports'])}"
                )
        
        return result
    
    def _check_syntax(self, file_path: Path) -> Tuple[bool, Optional[Exception]]:
        """Check if a Python file has valid syntax.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Tuple of (is_valid, error_if_any)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            ast.parse(source, filename=str(file_path))
            return True, None
        
        except SyntaxError as e:
            return False, e
        
        except Exception as e:
            return False, e
    
    def quick_import_test(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Try to import a Python file to catch runtime import errors.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Convert file path to module path
            rel_path = file_path.relative_to(self.project_root)
            module_path = str(rel_path.with_suffix('')).replace('/', '.')
            
            # Try to import using subprocess to avoid polluting current namespace
            result = subprocess.run(
                [sys.executable, '-c', f'import {module_path}'],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False, result.stderr
            
            return True, None
        
        except subprocess.TimeoutExpired:
            return False, "Import test timed out (possible infinite loop or blocking code)"
        
        except Exception as e:
            return False, f"Error during import test: {str(e)}"
    
    def validate_file_operation(self, file_path: Path, operation: str) -> ValidationResult:
        """Validate a file after an operation (write, edit).
        
        Args:
            file_path: Path to the file
            operation: Type of operation (write, edit)
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        result.files_checked.append(str(file_path))
        
        if not file_path.exists():
            result.add_error(str(file_path), f"File does not exist after {operation}")
            return result
        
        # For Python files, do syntax and import checks
        if file_path.suffix == '.py':
            # Syntax check
            syntax_valid, syntax_error = self._check_syntax(file_path)
            if not syntax_valid:
                result.add_error(
                    str(file_path),
                    f"Syntax error after {operation}: {syntax_error}"
                )
                return result
            
            # Import check
            import_result = self.import_analyzer.analyze_file(file_path)
            if not import_result["is_valid"]:
                for missing in import_result["missing_imports"]:
                    result.add_error(
                        str(file_path),
                        f"Missing import for '{missing['symbol']}' after {operation}"
                    )
                    if missing["suggestion"]:
                        result.add_suggestion(missing["suggestion"])
        
        return result
    
    def check_cross_file_consistency(self, modified_files: List[Path]) -> ValidationResult:
        """Check consistency across multiple modified files.
        
        Args:
            modified_files: List of modified files
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        # Build a map of defined symbols across all files
        defined_symbols: Dict[str, List[Path]] = {}
        
        for file_path in modified_files:
            if file_path.suffix != '.py':
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                tree = ast.parse(source)
                symbols = self.import_analyzer._extract_defined_symbols(tree)
                
                for symbol in symbols:
                    if symbol not in defined_symbols:
                        defined_symbols[symbol] = []
                    defined_symbols[symbol].append(file_path)
            
            except Exception:
                continue
        
        # Check for duplicate definitions
        for symbol, files in defined_symbols.items():
            if len(files) > 1:
                result.add_warning(
                    "cross-file",
                    f"Symbol '{symbol}' defined in multiple files: {[str(f) for f in files]}"
                )
        
        # Check that imports between modified files are consistent
        for file_path in modified_files:
            if file_path.suffix != '.py':
                continue
            
            try:
                import_result = self.import_analyzer.analyze_file(file_path)
                
                # Check if missing imports might be in other modified files
                for missing in import_result["missing_imports"]:
                    symbol = missing["symbol"]
                    if symbol in defined_symbols:
                        # Symbol is defined in one of the modified files
                        defining_files = defined_symbols[symbol]
                        result.add_suggestion(
                            f"{file_path.name}: Import '{symbol}' from {defining_files[0].name}"
                        )
            
            except Exception:
                continue
        
        return result
    
    def get_validation_report(self, result: ValidationResult) -> str:
        """Format a validation result as a human-readable report.
        
        Args:
            result: ValidationResult to format
            
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("CODE VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Files checked: {len(result.files_checked)}")
        lines.append(f"Status: {'✓ PASS' if result.is_valid else '✗ FAIL'}")
        lines.append("")
        
        if result.errors:
            lines.append(f"ERRORS ({len(result.errors)}):")
            for error in result.errors:
                line_info = f" (line {error['line']})" if error.get('line') else ""
                lines.append(f"  ✗ {error['file']}{line_info}")
                lines.append(f"    {error['message']}")
            lines.append("")
        
        if result.warnings:
            lines.append(f"WARNINGS ({len(result.warnings)}):")
            for warning in result.warnings:
                line_info = f" (line {warning['line']})" if warning.get('line') else ""
                lines.append(f"  ⚠ {warning['file']}{line_info}")
                lines.append(f"    {warning['message']}")
            lines.append("")
        
        if result.suggestions:
            lines.append(f"SUGGESTIONS ({len(result.suggestions)}):")
            for suggestion in result.suggestions:
                lines.append(f"  → {suggestion}")
            lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)
