"""Intelligent handling of large files for LLM interactions."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import ast
import re


class LargeFileHandler:
    """
    Handles large files intelligently to avoid overwhelming LLM context.

    Strategies:
    1. Provide file summary (structure, key elements)
    2. Allow targeted reads (functions, classes, line ranges)
    3. Suggest chunking strategies
    4. Auto-detect what user likely needs
    """

    # Thresholds
    LARGE_FILE_LINES = 500
    VERY_LARGE_FILE_LINES = 1000
    MAX_CHUNK_LINES = 300

    def __init__(self):
        """Initialize handler."""
        pass

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a file and determine best reading strategy.

        Returns:
            {
                "lines": int,
                "is_large": bool,
                "is_very_large": bool,
                "language": str,
                "structure": Dict (if parseable),
                "suggested_strategy": str,
                "chunks": List[Dict] (suggested reading chunks)
            }
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                line_count = len(lines)
        except Exception as e:
            return {
                "error": str(e),
                "suggested_strategy": "Unable to analyze file"
            }

        is_large = line_count >= self.LARGE_FILE_LINES
        is_very_large = line_count >= self.VERY_LARGE_FILE_LINES

        # Detect language from extension
        language = self._detect_language(file_path)

        # Try to parse structure
        structure = None
        if language == "python":
            structure = self._parse_python_structure(content)
        elif language in ["javascript", "typescript"]:
            structure = self._parse_js_structure(content)

        # Suggest strategy
        suggested_strategy = self._suggest_strategy(line_count, structure)

        # Generate chunks
        chunks = self._generate_chunks(lines, line_count, structure)

        return {
            "path": str(file_path),
            "lines": line_count,
            "is_large": is_large,
            "is_very_large": is_very_large,
            "language": language,
            "structure": structure,
            "suggested_strategy": suggested_strategy,
            "chunks": chunks
        }

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
        }
        return lang_map.get(ext, 'unknown')

    def _parse_python_structure(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse Python file structure using AST."""
        try:
            tree = ast.parse(content)

            classes = []
            functions = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                        "method_count": len(methods)
                    })
                elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                    # Top-level functions only
                    if node.col_offset == 0:
                        functions.append({
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args]
                        })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif node.module:
                        imports.append(node.module)

            return {
                "classes": classes,
                "functions": functions,
                "imports": imports[:20],  # Limit to first 20
                "class_count": len(classes),
                "function_count": len(functions),
                "import_count": len(imports)
            }
        except SyntaxError:
            return {"error": "Syntax error - cannot parse"}
        except Exception as e:
            return {"error": str(e)}

    def _parse_js_structure(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse JavaScript/TypeScript structure using regex (simplified)."""
        try:
            # Simple regex-based parsing for JS/TS
            classes = re.findall(r'class\s+(\w+)', content)
            functions = re.findall(r'(?:function|const|let|var)\s+(\w+)\s*(?:=\s*)?(?:\([^)]*\)|async)', content)
            imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
            exports = re.findall(r'export\s+(?:default\s+)?(?:class|function|const)\s+(\w+)', content)

            return {
                "classes": classes[:50],
                "functions": functions[:50],
                "imports": imports[:20],
                "exports": exports[:20],
                "class_count": len(classes),
                "function_count": len(functions),
                "import_count": len(imports),
                "export_count": len(exports)
            }
        except Exception as e:
            return {"error": str(e)}

    def _suggest_strategy(self, line_count: int, structure: Optional[Dict]) -> str:
        """Suggest best reading strategy based on file analysis."""
        if line_count < self.LARGE_FILE_LINES:
            return "read_full"
        elif line_count < self.VERY_LARGE_FILE_LINES:
            if structure and (structure.get("class_count", 0) > 0 or structure.get("function_count", 0) > 0):
                return "read_by_element"  # Read specific classes/functions
            else:
                return "read_chunks"  # Read in chunks
        else:
            return "summarize_then_target"  # Get summary first, then read specific parts

    def _generate_chunks(self, lines: List[str], line_count: int, structure: Optional[Dict]) -> List[Dict[str, Any]]:
        """Generate suggested reading chunks."""
        chunks = []

        # If we have structure, suggest element-based chunks
        if structure:
            if "classes" in structure:
                for cls in structure.get("classes", [])[:10]:
                    chunks.append({
                        "type": "class",
                        "name": cls.get("name") if isinstance(cls, dict) else cls,
                        "start_line": cls.get("line", 0) if isinstance(cls, dict) else 0,
                        "description": f"Class: {cls.get('name') if isinstance(cls, dict) else cls}"
                    })

            if "functions" in structure:
                for func in structure.get("functions", [])[:10]:
                    chunks.append({
                        "type": "function",
                        "name": func.get("name") if isinstance(func, dict) else func,
                        "start_line": func.get("line", 0) if isinstance(func, dict) else 0,
                        "description": f"Function: {func.get('name') if isinstance(func, dict) else func}"
                    })

        # If no structure or as fallback, suggest line-based chunks
        if not chunks or line_count > self.VERY_LARGE_FILE_LINES:
            chunk_size = self.MAX_CHUNK_LINES
            for i in range(0, line_count, chunk_size):
                end = min(i + chunk_size, line_count)
                chunks.append({
                    "type": "lines",
                    "start_line": i + 1,
                    "end_line": end,
                    "description": f"Lines {i + 1}-{end}"
                })

        return chunks[:20]  # Limit to 20 chunks

    def create_summary(self, file_path: Path, analysis: Optional[Dict] = None) -> str:
        """
        Create a human-readable summary of a large file.

        Args:
            file_path: Path to file
            analysis: Pre-computed analysis (if available)

        Returns:
            Formatted summary string
        """
        if not analysis:
            analysis = self.analyze_file(file_path)

        if "error" in analysis:
            return f"Error analyzing {file_path.name}: {analysis['error']}"

        summary_lines = [
            f"📄 File: {file_path.name}",
            f"📏 Lines: {analysis['lines']}",
            f"🔤 Language: {analysis['language']}",
            ""
        ]

        # Add structure info
        structure = analysis.get("structure")
        if structure and not structure.get("error"):
            if "class_count" in structure:
                summary_lines.append(f"📦 Classes: {structure['class_count']}")
                if structure.get("classes"):
                    for cls in structure["classes"][:5]:
                        name = cls.get("name") if isinstance(cls, dict) else cls
                        line = cls.get("line", "?") if isinstance(cls, dict) else "?"
                        summary_lines.append(f"   • {name} (line {line})")
                    if structure["class_count"] > 5:
                        summary_lines.append(f"   ... and {structure['class_count'] - 5} more")

            if "function_count" in structure:
                summary_lines.append(f"⚡ Functions: {structure['function_count']}")
                if structure.get("functions"):
                    for func in structure["functions"][:5]:
                        name = func.get("name") if isinstance(func, dict) else func
                        line = func.get("line", "?") if isinstance(func, dict) else "?"
                        summary_lines.append(f"   • {name} (line {line})")
                    if structure["function_count"] > 5:
                        summary_lines.append(f"   ... and {structure['function_count'] - 5} more")

            if "import_count" in structure:
                summary_lines.append(f"📥 Imports: {structure['import_count']}")

        # Add reading suggestion
        summary_lines.extend([
            "",
            f"💡 Suggested strategy: {analysis['suggested_strategy']}",
        ])

        # Add chunk suggestions
        if analysis.get("chunks"):
            summary_lines.append("")
            summary_lines.append("📑 Suggested reading chunks:")
            for chunk in analysis["chunks"][:5]:
                summary_lines.append(f"   • {chunk['description']}")
            if len(analysis["chunks"]) > 5:
                summary_lines.append(f"   ... and {len(analysis['chunks']) - 5} more")

        return "\n".join(summary_lines)

    def get_reading_guide(self, file_path: Path) -> str:
        """
        Get a guide for how to read this file effectively.

        Returns:
            Formatted guide with specific read_files commands
        """
        analysis = self.analyze_file(file_path)

        if "error" in analysis:
            return f"Error: {analysis['error']}"

        guide_lines = [
            f"📖 Reading Guide for {file_path.name}",
            f"{'=' * 60}",
            "",
            self.create_summary(file_path, analysis),
            "",
            "🔧 How to read this file:",
            ""
        ]

        strategy = analysis["suggested_strategy"]

        if strategy == "read_full":
            guide_lines.append("✓ File is small enough - read the whole thing:")
            guide_lines.append(f"   read_files(paths=['{file_path}'])")

        elif strategy == "read_by_element":
            guide_lines.append("✓ Read specific elements (recommended):")
            guide_lines.append("")

            structure = analysis.get("structure", {})
            if structure.get("classes"):
                guide_lines.append("   Read a class:")
                class_name = structure["classes"][0].get("name") if isinstance(structure["classes"][0], dict) else structure["classes"][0]
                guide_lines.append(f"   read_files(paths=['{file_path}'], classes=['{class_name}'])")
                guide_lines.append("")

            if structure.get("functions"):
                guide_lines.append("   Read a function:")
                func_name = structure["functions"][0].get("name") if isinstance(structure["functions"][0], dict) else structure["functions"][0]
                guide_lines.append(f"   read_files(paths=['{file_path}'], functions=['{func_name}'])")
                guide_lines.append("")

        elif strategy in ["read_chunks", "summarize_then_target"]:
            guide_lines.append("✓ Read in chunks (recommended):")
            guide_lines.append("")
            chunks = analysis.get("chunks", [])
            for i, chunk in enumerate(chunks[:3], 1):
                if chunk["type"] == "lines":
                    guide_lines.append(f"   Chunk {i}: {chunk['description']}")
                    guide_lines.append(f"   read_files(paths=['{file_path}'], line_range={{'start': {chunk['start_line']}, 'end': {chunk['end_line']}}})")
                    guide_lines.append("")

        guide_lines.extend([
            "",
            "💡 Tips:",
            "   • Use 'summarize: true' to get just the structure",
            "   • Combine line_range with functions/classes for context",
            "   • Read multiple small chunks in one call if related"
        ])

        return "\n".join(guide_lines)


# Singleton instance
_handler = None


def get_handler() -> LargeFileHandler:
    """Get the global handler instance."""
    global _handler
    if _handler is None:
        _handler = LargeFileHandler()
    return _handler
