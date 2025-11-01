"""Filesystem navigation tools."""

import os
from pathlib import Path
from typing import List, Any, Dict
from flux.tools.base import Tool, ToolParameter


class ListFilesTool(Tool):
    """Tool for listing files and directories."""
    
    def __init__(self, cwd: Path):
        """Initialize with current working directory."""
        self.cwd = cwd
    
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def description(self) -> str:
        return """List files and directories in a given path.
Returns file names, types (file/directory), and sizes.
Useful for exploring project structure."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="Path to list (relative to current directory or absolute). Use '.' for current directory.",
                required=False
            ),
            ToolParameter(
                name="show_hidden",
                type="boolean",
                description="Whether to show hidden files (starting with '.'). Default: false",
                required=False
            )
        ]
    
    async def execute(self, path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
        """List files and directories."""
        try:
            target_path = Path(path)
            if not target_path.is_absolute():
                target_path = self.cwd / target_path
            
            if not target_path.exists():
                return {"error": "Path does not exist"}
            
            if not target_path.is_dir():
                return {"error": "Path is not a directory"}
            
            items = []
            for item in sorted(target_path.iterdir()):
                # Skip hidden files unless requested
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                item_info = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item.relative_to(self.cwd)) if item.is_relative_to(self.cwd) else str(item)
                }
                
                # Add size for files
                if item.is_file():
                    try:
                        item_info["size"] = item.stat().st_size
                    except:
                        item_info["size"] = None
                
                items.append(item_info)
            
            return {
                "path": str(target_path),
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            return {"error": str(e)}


class FindFilesTool(Tool):
    """Tool for finding files by pattern."""
    
    def __init__(self, cwd: Path):
        """Initialize with current working directory."""
        self.cwd = cwd
    
    @property
    def name(self) -> str:
        return "find_files"
    
    @property
    def description(self) -> str:
        return """Find files matching a pattern (e.g., '*.py', 'test_*.js').
Recursively searches directories while respecting .gitignore patterns.
Fast for finding specific file types or names."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="pattern",
                type="string",
                description="File pattern to search for (e.g., '*.py', 'config.*', 'test_*')",
                required=True
            ),
            ToolParameter(
                name="path",
                type="string",
                description="Directory to search in (relative or absolute). Default: current directory",
                required=False
            ),
            ToolParameter(
                name="max_results",
                type="number",
                description="Maximum number of results to return. Default: 100",
                required=False
            )
        ]
    
    async def execute(
        self,
        pattern: str,
        path: str = ".",
        max_results: int = 100
    ) -> Dict[str, Any]:
        """Find files matching pattern."""
        try:
            search_path = Path(path)
            if not search_path.is_absolute():
                search_path = self.cwd / search_path
            
            if not search_path.exists():
                return {"error": "Path does not exist"}
            
            # Common directories to skip
            skip_dirs = {
                'node_modules', 'venv', '.venv', 'env', '.git',
                'dist', 'build', '__pycache__', '.next', '.nuxt'
            }
            
            matches = []
            count = 0
            
            for root, dirs, files in os.walk(search_path):
                # Remove skip directories from search
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                root_path = Path(root)
                
                # Check files against pattern
                for file in files:
                    file_path = root_path / file
                    
                    # Simple pattern matching
                    if self._matches_pattern(file, pattern):
                        rel_path = file_path.relative_to(self.cwd) if file_path.is_relative_to(self.cwd) else file_path
                        matches.append({
                            "path": str(rel_path),
                            "name": file,
                            "directory": str(root_path.relative_to(self.cwd)) if root_path.is_relative_to(self.cwd) else str(root_path)
                        })
                        count += 1
                        
                        if count >= max_results:
                            break
                
                if count >= max_results:
                    break
            
            return {
                "pattern": pattern,
                "matches": matches,
                "count": len(matches),
                "truncated": count >= max_results
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Simple pattern matching."""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)
