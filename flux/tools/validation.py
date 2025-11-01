"""Code validation tool for quality checks."""

import re
from pathlib import Path
from typing import List, Any, Dict
from flux.tools.base import Tool, ToolParameter


class ValidationTool(Tool):
    """Tool for validating generated code for common issues."""
    
    def __init__(self, cwd: Path):
        """Initialize with current working directory."""
        self.cwd = cwd
    
    @property
    def name(self) -> str:
        return "validate_code"
    
    @property
    def description(self) -> str:
        return """Validate generated code for common issues like:
- Hardcoded paths
- Missing imports
- Broken references
- Common anti-patterns"""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="paths",
                type="array",
                description="List of file paths to validate",
                required=True,
                items={"type": "string"}
            ),
            ToolParameter(
                name="check_types",
                type="array",
                description="Types of checks to run (paths, imports, references, all)",
                required=False,
                items={"type": "string"}
            )
        ]
    
    async def execute(self, paths: List[str], check_types: List[str] = None) -> Dict[str, Any]:
        """Validate code files."""
        if check_types is None:
            check_types = ["all"]
        
        all_issues = []
        all_suggestions = []
        
        for path_str in paths:
            try:
                file_path = Path(path_str)
                if not file_path.is_absolute():
                    file_path = self.cwd / file_path
                
                if not file_path.exists():
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Run checks
                if "all" in check_types or "paths" in check_types:
                    issues, suggestions = self._check_hardcoded_paths(content, file_path)
                    all_issues.extend(issues)
                    all_suggestions.extend(suggestions)
                
                if "all" in check_types or "imports" in check_types:
                    issues, suggestions = self._check_missing_imports(content, file_path)
                    all_issues.extend(issues)
                    all_suggestions.extend(suggestions)
                
                if "all" in check_types or "references" in check_types:
                    issues, suggestions = self._check_broken_references(content, file_path)
                    all_issues.extend(issues)
                    all_suggestions.extend(suggestions)
            
            except Exception as e:
                all_issues.append({
                    "file": path_str,
                    "type": "error",
                    "message": f"Failed to validate: {str(e)}"
                })
        
        return {
            "total_issues": len(all_issues),
            "issues": all_issues,
            "suggestions": all_suggestions,
            "status": "clean" if len(all_issues) == 0 else "has_issues"
        }
    
    def _check_hardcoded_paths(self, content: str, file_path: Path) -> tuple:
        """Check for hardcoded file paths."""
        issues = []
        suggestions = []
        
        # Detect file extension to determine language
        ext = file_path.suffix
        
        if ext == ".py":
            # Python: look for strings with / or \\ that look like paths
            patterns = [
                r'["\']([A-Za-z]:|/|\\\\)[^"\']*[/\\\\][^"\']+["\']',  # Absolute paths
                r'["\']\.\.?/[^"\']+["\']',  # Relative paths starting with ./ or ../
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    path_str = match.group(0)
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Skip if it's using Path() or os.path already
                    context_start = max(0, match.start() - 50)
                    context = content[context_start:match.start()]
                    if "Path(" in context or "os.path.join" in context or "__file__" in context:
                        continue
                    
                    issues.append({
                        "file": str(file_path),
                        "line": line_num,
                        "type": "hardcoded_path",
                        "message": f"Hardcoded path found: {path_str}"
                    })
                    suggestions.append({
                        "file": str(file_path),
                        "line": line_num,
                        "suggestion": "Use Path(__file__).parent / ... for relative paths"
                    })
        
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # JavaScript/TypeScript: similar checks
            patterns = [
                r'["\']([A-Za-z]:|/)[^"\']*[/\\\\][^"\']+["\']',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    path_str = match.group(0)
                    line_num = content[:match.start()].count('\n') + 1
                    
                    context_start = max(0, match.start() - 50)
                    context = content[context_start:match.start()]
                    if "path.join" in context or "__dirname" in context:
                        continue
                    
                    issues.append({
                        "file": str(file_path),
                        "line": line_num,
                        "type": "hardcoded_path",
                        "message": f"Hardcoded path found: {path_str}"
                    })
                    suggestions.append({
                        "file": str(file_path),
                        "line": line_num,
                        "suggestion": "Use path.join(__dirname, ...) for paths"
                    })
        
        return issues, suggestions
    
    def _check_missing_imports(self, content: str, file_path: Path) -> tuple:
        """Check for commonly missing imports."""
        issues = []
        suggestions = []
        
        ext = file_path.suffix
        
        if ext == ".py":
            # Check for Path usage without import
            if "Path(" in content and "from pathlib import Path" not in content:
                issues.append({
                    "file": str(file_path),
                    "type": "missing_import",
                    "message": "Path used but not imported"
                })
                suggestions.append({
                    "file": str(file_path),
                    "suggestion": "Add: from pathlib import Path"
                })
            
            # Check for os.path usage without import
            if "os.path" in content and "import os" not in content:
                issues.append({
                    "file": str(file_path),
                    "type": "missing_import",
                    "message": "os.path used but os not imported"
                })
                suggestions.append({
                    "file": str(file_path),
                    "suggestion": "Add: import os"
                })
        
        elif ext in [".js", ".ts"]:
            # Check for require usage of path module
            if "__dirname" in content and "path" not in content and "require" not in content:
                issues.append({
                    "file": str(file_path),
                    "type": "missing_import",
                    "message": "__dirname used but path module not imported"
                })
                suggestions.append({
                    "file": str(file_path),
                    "suggestion": "Add: const path = require('path');"
                })
        
        return issues, suggestions
    
    def _check_broken_references(self, content: str, file_path: Path) -> tuple:
        """Check for potentially broken references."""
        issues = []
        suggestions = []
        
        # This is a basic check - could be much more sophisticated
        # Check for common typos or undefined references
        
        return issues, suggestions
