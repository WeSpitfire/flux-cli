"""Codebase Intelligence - Semantic understanding of entire projects.

This module builds a semantic graph of the codebase, understanding:
- File relationships and dependencies
- Function/class usage patterns
- Import chains
- Related code discovery
- Architecture patterns
"""

import ast
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import re


@dataclass
class CodeEntity:
    """Represents a code entity (function, class, variable)."""
    name: str
    type: str  # 'function', 'class', 'variable', 'import'
    file_path: str
    line_number: int
    defined_in: Optional[str] = None  # Parent class/function
    docstring: Optional[str] = None
    references: List[str] = field(default_factory=list)  # Where it's used
    dependencies: List[str] = field(default_factory=list)  # What it uses


@dataclass
class FileNode:
    """Represents a file in the codebase."""
    path: str
    language: str
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)  # Functions/classes defined
    dependencies: List[str] = field(default_factory=list)  # Other files it depends on
    dependents: List[str] = field(default_factory=list)  # Files that depend on it
    entities: List[CodeEntity] = field(default_factory=list)
    last_modified: Optional[float] = None


class CodebaseGraph:
    """Builds and maintains a semantic graph of the codebase."""
    
    CACHE_VERSION = "1.0"
    
    def __init__(self, root_path: Path, cache_dir: Optional[Path] = None):
        self.root_path = root_path
        self.cache_dir = cache_dir or (root_path / ".flux" / "cache")
        self.cache_file = self.cache_dir / "codebase_graph.json"
        self.files: Dict[str, FileNode] = {}
        self.entities: Dict[str, CodeEntity] = {}
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self._language_parsers = {
            '.py': self._parse_python_file,
            '.js': self._parse_javascript_file,
            '.ts': self._parse_javascript_file,
            '.jsx': self._parse_javascript_file,
            '.tsx': self._parse_javascript_file,
        }
    
    def build_graph(self, max_files: int = 1000, use_cache: bool = True) -> None:
        """Build the complete codebase graph.
        
        Args:
            max_files: Maximum number of files to parse
            use_cache: Whether to use cached graph if valid
        """
        # Try to load from cache if enabled
        if use_cache and self._load_from_cache():
            # Print to stderr so it doesn't interfere with JSON output
            import sys
            print(f"✅ Loaded cached graph: {len(self.files)} files, {len(self.entities)} entities", file=sys.stderr)
            return
        
        import sys
        print(f"🔍 Building codebase graph from {self.root_path}...", file=sys.stderr)
        
        # Find all code files
        code_files = self._find_code_files(max_files)
        print(f"   Found {len(code_files)} code files", file=sys.stderr)
        
        # Parse each file
        for i, file_path in enumerate(code_files):
            if i % 50 == 0:
                print(f"   Parsing... {i}/{len(code_files)}", file=sys.stderr)
            self._parse_file(file_path)
        
        # Build dependency graph
        self._build_dependency_graph()
        
        print(f"✅ Graph built: {len(self.files)} files, {len(self.entities)} entities", file=sys.stderr)
        
        # Save to cache
        self._save_to_cache()
    
    def find_related_files(self, query: str, current_file: Optional[str] = None, limit: int = 10) -> List[Tuple[str, float]]:
        """Find files related to a query or current file.
        
        Returns list of (file_path, relevance_score) tuples.
        """
        scores: Dict[str, float] = defaultdict(float)
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        for file_path, file_node in self.files.items():
            score = 0.0
            
            # Current file context
            if current_file and file_path == current_file:
                score += 10.0
            
            # Direct dependencies
            if current_file and current_file in self.files:
                if file_path in self.files[current_file].dependencies:
                    score += 5.0
                if file_path in self.files[current_file].dependents:
                    score += 5.0
            
            # Filename match
            file_name = os.path.basename(file_path).lower()
            if query_lower in file_name:
                score += 3.0
            
            # Word overlap in filename
            file_words = set(re.findall(r'\w+', file_name))
            overlap = len(query_words & file_words)
            score += overlap * 2.0
            
            # Entity name matches
            for entity in file_node.entities:
                if query_lower in entity.name.lower():
                    score += 2.0
                if entity.docstring and query_lower in entity.docstring.lower():
                    score += 1.0
            
            # Import matches
            for imp in file_node.imports:
                if any(word in imp.lower() for word in query_words):
                    score += 1.0
            
            if score > 0:
                scores[file_path] = score
        
        # Sort by score and return top results
        sorted_files = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:limit]
    
    def find_related_entities(self, entity_name: str, limit: int = 10) -> List[CodeEntity]:
        """Find entities related to the given entity name."""
        if entity_name not in self.entities:
            # Try partial match
            matches = [e for name, e in self.entities.items() if entity_name.lower() in name.lower()]
            return matches[:limit]
        
        entity = self.entities[entity_name]
        related = []
        
        # Add entities it references
        for ref in entity.references:
            if ref in self.entities:
                related.append(self.entities[ref])
        
        # Add entities that reference it
        for name, ent in self.entities.items():
            if entity_name in ent.references:
                related.append(ent)
        
        return related[:limit]
    
    def get_file_context(self, file_path: str) -> Dict:
        """Get rich context about a file."""
        if file_path not in self.files:
            return {}
        
        file_node = self.files[file_path]
        
        return {
            'path': file_path,
            'language': file_node.language,
            'imports': file_node.imports,
            'exports': file_node.exports,
            'dependencies': file_node.dependencies,
            'dependents': file_node.dependents,
            'entities': [
                {
                    'name': e.name,
                    'type': e.type,
                    'line': e.line_number,
                    'docstring': e.docstring
                }
                for e in file_node.entities
            ]
        }
    
    def suggest_context_files(self, query: str, max_files: int = 5) -> List[str]:
        """Suggest files that should be included as context for a query."""
        related = self.find_related_files(query, limit=max_files)
        return [file_path for file_path, score in related if score > 1.0]
    
    def detect_architecture_patterns(self) -> Dict[str, any]:
        """Detect common architecture patterns in the codebase."""
        patterns = {
            'framework': self._detect_framework(),
            'structure': self._detect_structure(),
            'testing': self._detect_testing_framework(),
            'has_tests': any('test' in f.lower() for f in self.files.keys()),
            'has_docs': any('doc' in f.lower() or 'readme' in f.lower() for f in self.files.keys()),
        }
        return patterns
    
    # Internal methods
    
    def _find_code_files(self, max_files: int) -> List[str]:
        """Find all code files in the repository."""
        code_files = []
        exclude_dirs = {
            'node_modules', 'venv', '.venv', 'dist', 'build', '__pycache__',
            '.git', '.next', '.nuxt', 'vendor', 'target'
        }
        
        for root, dirs, files in os.walk(self.root_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in self._language_parsers:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.root_path)
                    code_files.append(rel_path)
                    
                    if len(code_files) >= max_files:
                        return code_files
        
        return code_files
    
    def _parse_file(self, file_path: str) -> None:
        """Parse a single file and add to graph."""
        full_path = self.root_path / file_path
        ext = os.path.splitext(file_path)[1]
        
        if not os.path.exists(full_path):
            return
        
        parser = self._language_parsers.get(ext)
        if not parser:
            return
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_node = parser(file_path, content)
            if file_node:
                self.files[file_path] = file_node
                
                # Add entities to global index
                for entity in file_node.entities:
                    self.entities[f"{file_path}:{entity.name}"] = entity
        
        except Exception as e:
            # Silently skip files that can't be parsed
            pass
    
    def _parse_python_file(self, file_path: str, content: str) -> Optional[FileNode]:
        """Parse a Python file using AST."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None
        
        file_node = FileNode(path=file_path, language='python')
        
        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_node.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    file_node.imports.append(node.module)
            
            # Functions
            elif isinstance(node, ast.FunctionDef):
                entity = CodeEntity(
                    name=node.name,
                    type='function',
                    file_path=file_path,
                    line_number=node.lineno,
                    docstring=ast.get_docstring(node)
                )
                file_node.entities.append(entity)
                file_node.exports.append(node.name)
            
            # Classes
            elif isinstance(node, ast.ClassDef):
                entity = CodeEntity(
                    name=node.name,
                    type='class',
                    file_path=file_path,
                    line_number=node.lineno,
                    docstring=ast.get_docstring(node)
                )
                file_node.entities.append(entity)
                file_node.exports.append(node.name)
        
        return file_node
    
    def _parse_javascript_file(self, file_path: str, content: str) -> Optional[FileNode]:
        """Parse a JavaScript/TypeScript file (basic regex-based parsing)."""
        file_node = FileNode(path=file_path, language='javascript')
        
        # Extract imports (simplified)
        import_pattern = r'import\s+.*?from\s+[\'"](.+?)[\'"]'
        imports = re.findall(import_pattern, content)
        file_node.imports.extend(imports)
        
        # Extract function/class exports
        export_pattern = r'export\s+(?:function|class)\s+(\w+)'
        exports = re.findall(export_pattern, content)
        file_node.exports.extend(exports)
        
        # Extract function declarations
        func_pattern = r'(?:function|const|let|var)\s+(\w+)\s*=?\s*(?:async\s*)?\('
        functions = re.findall(func_pattern, content)
        for func_name in functions:
            entity = CodeEntity(
                name=func_name,
                type='function',
                file_path=file_path,
                line_number=0  # Would need more sophisticated parsing for line numbers
            )
            file_node.entities.append(entity)
        
        return file_node
    
    def _build_dependency_graph(self) -> None:
        """Build the dependency graph between files."""
        for file_path, file_node in self.files.items():
            for imp in file_node.imports:
                # Try to resolve import to actual file
                resolved = self._resolve_import(imp, file_path)
                if resolved and resolved in self.files:
                    file_node.dependencies.append(resolved)
                    self.files[resolved].dependents.append(file_path)
                    self.import_graph[file_path].add(resolved)
    
    def _resolve_import(self, import_name: str, current_file: str) -> Optional[str]:
        """Try to resolve an import to an actual file path."""
        # Simplified import resolution
        # In practice, this would need to handle node_modules, Python packages, etc.
        
        # Try relative imports
        current_dir = os.path.dirname(current_file)
        
        # Python-style imports
        potential_paths = [
            os.path.join(current_dir, f"{import_name}.py"),
            os.path.join(current_dir, import_name, "__init__.py"),
            f"{import_name.replace('.', '/')}.py",
        ]
        
        for path in potential_paths:
            if path in self.files:
                return path
        
        return None
    
    def _detect_framework(self) -> Optional[str]:
        """Detect the framework being used."""
        # Check for common framework indicators
        if any('django' in imp for file in self.files.values() for imp in file.imports):
            return 'django'
        if any('flask' in imp for file in self.files.values() for imp in file.imports):
            return 'flask'
        if any('react' in imp for file in self.files.values() for imp in file.imports):
            return 'react'
        if any('vue' in imp for file in self.files.values() for imp in file.imports):
            return 'vue'
        if any('next' in imp for file in self.files.values() for imp in file.imports):
            return 'nextjs'
        
        # Check for config files
        if 'package.json' in [os.path.basename(f) for f in self.files.keys()]:
            return 'nodejs'
        if 'setup.py' in [os.path.basename(f) for f in self.files.keys()]:
            return 'python'
        
        return None
    
    def _detect_structure(self) -> str:
        """Detect the project structure pattern."""
        files = list(self.files.keys())
        
        if any('src/' in f for f in files):
            return 'src-based'
        if any('lib/' in f for f in files):
            return 'lib-based'
        if any('app/' in f for f in files):
            return 'app-based'
        
        return 'flat'
    
    def _detect_testing_framework(self) -> Optional[str]:
        """Detect the testing framework."""
        for file in self.files.values():
            for imp in file.imports:
                if 'pytest' in imp:
                    return 'pytest'
                if 'unittest' in imp:
                    return 'unittest'
                if 'jest' in imp:
                    return 'jest'
                if 'mocha' in imp:
                    return 'mocha'
        
        return None


    def _compute_file_hash(self, file_path: str) -> str:
        """Compute hash of file contents for cache invalidation."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def _compute_tree_hash(self, file_paths: List[str]) -> str:
        """Compute combined hash of all files for cache validation."""
        hasher = hashlib.md5()
        
        # Sort for consistency
        for file_path in sorted(file_paths):
            hasher.update(file_path.encode())
            file_hash = self._compute_file_hash(file_path)
            hasher.update(file_hash.encode())
        
        return hasher.hexdigest()
    
    def _save_to_cache(self) -> None:
        """Save the codebase graph to cache."""
        try:
            # Create cache directory if it doesn't exist
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Compute file tree hash
            file_paths = list(self.files.keys())
            tree_hash = self._compute_tree_hash(file_paths)
            
            # Prepare data for serialization
            cache_data = {
                'version': self.CACHE_VERSION,
                'tree_hash': tree_hash,
                'root_path': str(self.root_path),
                'files': {},
                'entities': {}
            }
            
            # Serialize files (convert to dict)
            for path, file_node in self.files.items():
                cache_data['files'][path] = {
                    'path': file_node.path,
                    'language': file_node.language,
                    'imports': file_node.imports,
                    'exports': file_node.exports,
                    'dependencies': file_node.dependencies,
                    'dependents': file_node.dependents,
                    'last_modified': file_node.last_modified,
                    'entities': [
                        {
                            'name': e.name,
                            'type': e.type,
                            'file_path': e.file_path,
                            'line_number': e.line_number,
                            'defined_in': e.defined_in,
                            'docstring': e.docstring,
                            'references': e.references,
                            'dependencies': e.dependencies
                        }
                        for e in file_node.entities
                    ]
                }
            
            # Serialize entities
            for name, entity in self.entities.items():
                cache_data['entities'][name] = {
                    'name': entity.name,
                    'type': entity.type,
                    'file_path': entity.file_path,
                    'line_number': entity.line_number,
                    'defined_in': entity.defined_in,
                    'docstring': entity.docstring,
                    'references': entity.references,
                    'dependencies': entity.dependencies
                }
            
            # Write to cache file
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            import sys
            print(f"   💾 Cache saved to {self.cache_file}", file=sys.stderr)
        
        except Exception as e:
            import sys
            print(f"   ⚠️ Warning: Could not save cache: {e}", file=sys.stderr)
    
    def _load_from_cache(self) -> bool:
        """Load the codebase graph from cache if valid.
        
        Returns True if cache was loaded successfully, False otherwise.
        """
        try:
            # Check if cache file exists
            if not self.cache_file.exists():
                return False
            
            # Load cache data
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Verify cache version
            if cache_data.get('version') != self.CACHE_VERSION:
                import sys
                print("   ⚠️ Cache version mismatch, rebuilding...", file=sys.stderr)
                return False
            
            # Verify root path matches
            if cache_data.get('root_path') != str(self.root_path):
                return False
            
            # Find current code files
            current_files = self._find_code_files(1000)
            current_hash = self._compute_tree_hash(current_files)
            
            # Verify file tree hasn't changed
            if cache_data.get('tree_hash') != current_hash:
                import sys
                print("   ⚠️ Codebase changed, rebuilding graph...", file=sys.stderr)
                return False
            
            # Deserialize files
            for path, file_data in cache_data['files'].items():
                entities = [
                    CodeEntity(
                        name=e['name'],
                        type=e['type'],
                        file_path=e['file_path'],
                        line_number=e['line_number'],
                        defined_in=e.get('defined_in'),
                        docstring=e.get('docstring'),
                        references=e.get('references', []),
                        dependencies=e.get('dependencies', [])
                    )
                    for e in file_data.get('entities', [])
                ]
                
                self.files[path] = FileNode(
                    path=file_data['path'],
                    language=file_data['language'],
                    imports=file_data.get('imports', []),
                    exports=file_data.get('exports', []),
                    dependencies=file_data.get('dependencies', []),
                    dependents=file_data.get('dependents', []),
                    entities=entities,
                    last_modified=file_data.get('last_modified')
                )
            
            # Deserialize entities
            for name, entity_data in cache_data.get('entities', {}).items():
                self.entities[name] = CodeEntity(
                    name=entity_data['name'],
                    type=entity_data['type'],
                    file_path=entity_data['file_path'],
                    line_number=entity_data['line_number'],
                    defined_in=entity_data.get('defined_in'),
                    docstring=entity_data.get('docstring'),
                    references=entity_data.get('references', []),
                    dependencies=entity_data.get('dependencies', [])
                )
            
            # Rebuild import graph
            self._build_dependency_graph()
            
            return True
        
        except Exception as e:
            import sys
            print(f"   ⚠️ Could not load cache: {e}", file=sys.stderr)
            return False


def create_codebase_graph(root_path: Path, use_cache: bool = True) -> CodebaseGraph:
    """Create and build a codebase graph.
    
    Args:
        root_path: Root directory of the codebase
        use_cache: Whether to use cached graph if available
    """
    graph = CodebaseGraph(root_path)
    graph.build_graph(use_cache=use_cache)
    return graph
