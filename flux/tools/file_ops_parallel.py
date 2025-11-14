"""Enhanced file operations with parallel execution support.

This module provides parallel-optimized versions of file operations
for dramatic performance improvements when working with multiple files.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from flux.tools.base import Tool, ToolParameter
from flux.core.errors import file_not_found_error
from flux.core.smart_reader import SmartReader
from flux.tools.file_ops import validate_file_path


class ParallelReadFilesTool(Tool):
    """Parallel-optimized tool for reading multiple files concurrently."""

    def __init__(self, cwd: Path, workflow_enforcer=None, background_processor=None):
        """Initialize with current working directory."""
        self.cwd = cwd
        self.workflow = workflow_enforcer
        self.bg_processor = background_processor
        self.smart_reader = SmartReader()

    @property
    def name(self) -> str:
        return "read_files"

    @property
    def description(self) -> str:
        return """Read file contents with PARALLEL EXECUTION for multiple files.

PERFORMANCE OPTIMIZED:
- Multiple files are read in parallel (up to 10 concurrent)
- Cached results are returned instantly
- Smart chunking for large files
- Automatic batching by directory

READING MODES (choose based on need):
1. Full read: Just pass 'paths' - use for small files or when you need everything
2. Selective functions: Pass 'functions' list - read only specific functions
3. Selective classes: Pass 'classes' list - read only specific classes
4. Line range: Pass 'line_range' {start, end} - read specific lines only
5. Summary: Pass 'summarize: true' - get file structure without full content

CACHING: Files are cached during workflow - reading same file twice uses cache.
ON ERROR: Use list_files or find_files to discover correct paths."""

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="paths",
                type="array",
                description="List of file paths to read (relative to current directory or absolute)",
                required=True,
                items={"type": "string"}
            ),
            ToolParameter(
                name="functions",
                type="array",
                description="Optional: Read only specific functions (saves tokens for large files)",
                required=False,
                items={"type": "string"}
            ),
            ToolParameter(
                name="classes",
                type="array",
                description="Optional: Read only specific classes (saves tokens for large files)",
                required=False,
                items={"type": "string"}
            ),
            ToolParameter(
                name="line_range",
                type="object",
                description="Optional: Read only specific line range {start: int, end: int}",
                required=False
            ),
            ToolParameter(
                name="summarize",
                type="boolean",
                description="Optional: Get file summary (structure) instead of full content",
                required=False
            )
        ]

    async def execute(self, paths: List[str], functions: Optional[List[str]] = None,
                      classes: Optional[List[str]] = None, line_range: Optional[Dict] = None,
                      summarize: bool = False) -> Dict[str, Any]:
        """Read files in parallel for maximum performance."""
        
        # Define async function to read a single file
        async def read_single_file(path_str: str) -> Tuple[str, Dict[str, Any]]:
            """Read a single file asynchronously."""
            # Validate path first
            is_valid, error_msg = validate_file_path(path_str, self.cwd, "read")
            if not is_valid:
                return path_str, {
                    "error": {
                        "code": "INVALID_PATH",
                        "message": error_msg,
                        "path": path_str
                    }
                }

            try:
                path = Path(path_str)
                if not path.is_absolute():
                    path = self.cwd / path

                if not path.exists():
                    # Find similar files to help agent
                    parent = path.parent if path.parent.exists() else self.cwd
                    try:
                        similar = [str(f.relative_to(self.cwd)) for f in parent.glob('*') if f.is_file()][:5]
                    except:
                        similar = None
                    return path_str, file_not_found_error(path_str, similar)

                if not path.is_file():
                    return path_str, {"error": "Path is not a file"}

                # Check cache first
                cached_content = None
                cache_source = None

                if self.bg_processor:
                    cached_content = self.bg_processor.get_cached_file(path)
                    if cached_content:
                        cache_source = 'background'
                        self.bg_processor.record_time_saved(7)

                if cached_content is None and self.workflow:
                    cached_content = self.workflow.get_cached_file(path)
                    if cached_content:
                        cache_source = 'workflow'

                if cached_content is not None:
                    # Return cached content immediately
                    lines_count = cached_content.count('\n')
                    return path_str, {
                        "content": cached_content,
                        "lines": lines_count,
                        "mode": "cached",
                        "cached": True,
                        "cache_source": cache_source
                    }

                # Handle selective reading modes
                content = None
                mode = "full"

                # Use asyncio.to_thread for file I/O to avoid blocking
                if summarize:
                    content = await asyncio.to_thread(self.smart_reader.summarize_file, path)
                    mode = "summary"

                elif line_range:
                    start = line_range.get('start', 1)
                    end = line_range.get('end', 999999)
                    content = await asyncio.to_thread(self.smart_reader.read_lines, path, start, end)
                    mode = f"lines {start}-{end}"

                elif functions:
                    parts = []
                    for func_name in functions:
                        func_content = await asyncio.to_thread(
                            self.smart_reader.read_function, path, func_name
                        )
                        if func_content:
                            parts.append(f"# Function: {func_name}\n{func_content}")
                        else:
                            parts.append(f"# Function '{func_name}' not found")
                    content = "\n\n".join(parts)
                    mode = f"functions: {', '.join(functions)}"

                elif classes:
                    parts = []
                    for class_name in classes:
                        class_content = await asyncio.to_thread(
                            self.smart_reader.read_class, path, class_name
                        )
                        if class_content:
                            parts.append(f"# Class: {class_name}\n{class_content}")
                        else:
                            parts.append(f"# Class '{class_name}' not found")
                    content = "\n\n".join(parts)
                    mode = f"classes: {', '.join(classes)}"

                # Full file read (default)
                if content is None:
                    # Read file in thread pool to avoid blocking
                    content = await asyncio.to_thread(self._read_full_file, path)
                    
                    if content.startswith("File:") and "too large" in content:
                        mode = "auto-limited"
                    else:
                        # Cache the content for reuse
                        if self.workflow and len(content) < 50000:  # Don't cache huge files
                            self.workflow.record_file_read(path, content)

                lines_count = content.count('\n') if content else 0

                return path_str, {
                    "content": content,
                    "lines": lines_count,
                    "mode": mode,
                    "cached": False
                }

            except Exception as e:
                return path_str, {"error": str(e)}

        def _read_full_file(self, path: Path) -> str:
            """Read full file content with automatic large file handling."""
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    file_lines = f.readlines()
                    lines_count = len(file_lines)

                    # Auto-limit large files
                    if lines_count > 500:
                        from flux.core.large_file_handler import get_handler
                        handler = get_handler()
                        guide = handler.get_reading_guide(path)

                        return f"""File: {path.name} (unable to parse)

This file has {lines_count} lines, which is too large to read at once.

{guide}
"""
                    else:
                        # Normal file - read with line numbers
                        return "".join([f"{i+1}|{line}" for i, line in enumerate(file_lines)])
            except Exception as e:
                raise e

        # Create tasks for all files
        tasks = [read_single_file(path) for path in paths]
        
        # Execute all reads in parallel with concurrency limit
        # Limit to 10 concurrent reads to avoid file descriptor exhaustion
        semaphore = asyncio.Semaphore(10)
        
        async def read_with_limit(task):
            async with semaphore:
                return await task
        
        limited_tasks = [read_with_limit(task) for task in tasks]
        results_list = await asyncio.gather(*limited_tasks)
        
        # Convert list of results to dictionary
        results = {path: result for path, result in results_list}
        
        # Add performance statistics
        total_files = len(paths)
        cached_files = sum(1 for r in results.values() if r.get('cached', False))
        
        if total_files > 1:
            results['_performance'] = {
                'total_files': total_files,
                'cached_files': cached_files,
                'parallel_execution': True,
                'concurrency': min(10, total_files)
            }
        
        return results


class BatchFileOperations:
    """Utility class for batch file operations with optimal performance."""
    
    @staticmethod
    async def batch_write_files(files: List[Dict[str, Any]], cwd: Path) -> Dict[str, Any]:
        """Write multiple files in parallel.
        
        Args:
            files: List of dicts with 'path' and 'content' keys
            cwd: Current working directory
        
        Returns:
            Dictionary with results for each file
        """
        async def write_single(file_info: Dict) -> Tuple[str, Dict]:
            path_str = file_info['path']
            content = file_info['content']
            
            # Validate path
            is_valid, error_msg = validate_file_path(path_str, cwd, "write")
            if not is_valid:
                return path_str, {"error": error_msg}
            
            try:
                path = Path(path_str)
                if not path.is_absolute():
                    path = cwd / path
                
                # Create parent directories if needed
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file in thread pool
                await asyncio.to_thread(path.write_text, content, encoding='utf-8')
                
                return path_str, {
                    "success": True,
                    "lines": content.count('\n'),
                    "size": len(content)
                }
            except Exception as e:
                return path_str, {"error": str(e)}
        
        # Execute all writes in parallel
        tasks = [write_single(f) for f in files]
        results_list = await asyncio.gather(*tasks)
        
        return {path: result for path, result in results_list}
    
    @staticmethod
    async def batch_delete_files(paths: List[str], cwd: Path) -> Dict[str, Any]:
        """Delete multiple files in parallel.
        
        Args:
            paths: List of file paths to delete
            cwd: Current working directory
        
        Returns:
            Dictionary with results for each file
        """
        async def delete_single(path_str: str) -> Tuple[str, Dict]:
            # Validate path
            is_valid, error_msg = validate_file_path(path_str, cwd, "delete")
            if not is_valid:
                return path_str, {"error": error_msg}
            
            try:
                path = Path(path_str)
                if not path.is_absolute():
                    path = cwd / path
                
                if not path.exists():
                    return path_str, {"error": "File does not exist"}
                
                # Delete file in thread pool
                await asyncio.to_thread(path.unlink)
                
                return path_str, {"success": True, "deleted": True}
            except Exception as e:
                return path_str, {"error": str(e)}
        
        # Execute all deletes in parallel
        tasks = [delete_single(p) for p in paths]
        results_list = await asyncio.gather(*tasks)
        
        return {path: result for path, result in results_list}


# Export the parallel version as the default
ReadFilesTool = ParallelReadFilesTool