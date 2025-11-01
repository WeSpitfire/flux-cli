"""Project detection and context management."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class ProjectInfo:
    """Information about detected project."""
    
    project_type: str  # 'nextjs', 'react', 'python', 'django', 'fastapi', etc.
    root_path: Path
    name: str
    description: Optional[str] = None
    
    # Configuration
    config_files: Dict[str, Path] = field(default_factory=dict)
    
    # Dependencies
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    
    # Project structure
    main_dirs: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    
    # Scripts/commands
    scripts: Dict[str, str] = field(default_factory=dict)
    
    # Tech stack
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    
    def to_context_string(self) -> str:
        """Generate context string for LLM."""
        lines = [
            f"# Project: {self.name}",
            f"Type: {self.project_type}",
        ]
        
        if self.description:
            lines.append(f"Description: {self.description}")
        
        if self.languages:
            lines.append(f"Languages: {', '.join(self.languages)}")
        
        if self.frameworks:
            lines.append(f"Frameworks: {', '.join(self.frameworks)}")
        
        if self.main_dirs:
            lines.append(f"Main directories: {', '.join(self.main_dirs)}")
        
        if self.entry_points:
            lines.append(f"Entry points: {', '.join(self.entry_points)}")
        
        if self.scripts:
            lines.append("\nAvailable scripts:")
            for name, cmd in list(self.scripts.items())[:10]:  # Limit to 10
                lines.append(f"  - {name}: {cmd}")
        
        if self.dependencies:
            dep_count = len(self.dependencies)
            lines.append(f"\nDependencies: {dep_count} packages")
            # List important ones
            important = ['react', 'next', 'express', 'fastapi', 'django', 'flask']
            found = [name for name in important if name in self.dependencies]
            if found:
                lines.append(f"  Key packages: {', '.join(found)}")
        
        return "\n".join(lines)


class ProjectDetector:
    """Detects project type and loads context."""
    
    # Project markers - files that indicate project type
    PROJECT_MARKERS = {
        'nextjs': ['next.config.js', 'next.config.mjs', 'next.config.ts'],
        'react': ['package.json'],  # Check contents for react
        'vue': ['vue.config.js', 'nuxt.config.js'],
        'python': ['pyproject.toml', 'setup.py', 'requirements.txt'],
        'django': ['manage.py'],
        'fastapi': ['main.py'],  # Check imports
        'flask': ['app.py'],  # Check imports
        'nodejs': ['package.json'],
        'go': ['go.mod'],
        'rust': ['Cargo.toml'],
        'ruby': ['Gemfile'],
    }
    
    def __init__(self, cwd: Path):
        """Initialize detector."""
        self.cwd = cwd
    
    def detect(self) -> Optional[ProjectInfo]:
        """Detect project type and gather context."""
        # Try to find project root (walk up to find markers)
        root = self._find_project_root()
        if not root:
            return None
        
        # Detect project type
        project_type = self._detect_type(root)
        if not project_type:
            return None
        
        # Build project info
        info = ProjectInfo(
            project_type=project_type,
            root_path=root,
            name=root.name
        )
        
        # Load type-specific context
        if project_type in ['nextjs', 'react', 'vue', 'nodejs']:
            self._load_nodejs_context(info, root)
        elif project_type in ['python', 'django', 'fastapi', 'flask']:
            self._load_python_context(info, root)
        elif project_type == 'go':
            self._load_go_context(info, root)
        elif project_type == 'rust':
            self._load_rust_context(info, root)
        
        # Detect languages and frameworks
        self._detect_tech_stack(info, root)
        
        # Find main directories
        self._find_main_dirs(info, root)
        
        return info
    
    def _find_project_root(self) -> Optional[Path]:
        """Find project root by walking up directory tree."""
        current = self.cwd
        
        # Walk up max 5 levels
        for _ in range(5):
            # Check for common project markers
            markers = [
                'package.json', 'pyproject.toml', 'go.mod', 'Cargo.toml',
                '.git', 'requirements.txt', 'setup.py', 'pom.xml'
            ]
            
            for marker in markers:
                if (current / marker).exists():
                    return current
            
            # Move up
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent
        
        # No project root found, use cwd
        return self.cwd if self._has_project_files(self.cwd) else None
    
    def _has_project_files(self, path: Path) -> bool:
        """Check if directory has project files."""
        project_files = [
            'package.json', 'pyproject.toml', 'go.mod', 'Cargo.toml',
            'requirements.txt', 'setup.py', 'manage.py'
        ]
        return any((path / f).exists() for f in project_files)
    
    def _detect_type(self, root: Path) -> Optional[str]:
        """Detect specific project type."""
        # Check in priority order
        
        # Next.js
        if any((root / marker).exists() for marker in self.PROJECT_MARKERS['nextjs']):
            return 'nextjs'
        
        # Django
        if (root / 'manage.py').exists():
            return 'django'
        
        # Go
        if (root / 'go.mod').exists():
            return 'go'
        
        # Rust
        if (root / 'Cargo.toml').exists():
            return 'rust'
        
        # Check package.json for React/Node
        package_json = root / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    
                    if 'react' in deps:
                        return 'react'
                    return 'nodejs'
            except:
                pass
        
        # Python
        if any((root / f).exists() for f in ['pyproject.toml', 'requirements.txt', 'setup.py']):
            # Check for FastAPI or Flask
            req_file = root / 'requirements.txt'
            if req_file.exists():
                try:
                    content = req_file.read_text()
                    if 'fastapi' in content.lower():
                        return 'fastapi'
                    if 'flask' in content.lower():
                        return 'flask'
                except:
                    pass
            return 'python'
        
        return None
    
    def _load_nodejs_context(self, info: ProjectInfo, root: Path):
        """Load Node.js/npm project context."""
        package_json = root / 'package.json'
        if not package_json.exists():
            return
        
        try:
            with open(package_json) as f:
                data = json.load(f)
            
            info.name = data.get('name', root.name)
            info.description = data.get('description')
            info.dependencies = data.get('dependencies', {})
            info.dev_dependencies = data.get('devDependencies', {})
            info.scripts = data.get('scripts', {})
            
            info.config_files['package.json'] = package_json
            
            # Check for tsconfig
            if (root / 'tsconfig.json').exists():
                info.config_files['tsconfig.json'] = root / 'tsconfig.json'
            
            # Entry points
            if (root / 'src/index.js').exists():
                info.entry_points.append('src/index.js')
            if (root / 'src/index.ts').exists():
                info.entry_points.append('src/index.ts')
            if (root / 'pages').exists():
                info.entry_points.append('pages/')
            if (root / 'app').exists():
                info.entry_points.append('app/')
                
        except Exception as e:
            pass
    
    def _load_python_context(self, info: ProjectInfo, root: Path):
        """Load Python project context."""
        # pyproject.toml
        pyproject = root / 'pyproject.toml'
        if pyproject.exists():
            info.config_files['pyproject.toml'] = pyproject
            try:
                # Basic parsing without external deps
                content = pyproject.read_text()
                if 'name = ' in content:
                    for line in content.split('\n'):
                        if line.strip().startswith('name = '):
                            info.name = line.split('=')[1].strip().strip('"\'')
                            break
            except:
                pass
        
        # requirements.txt
        req_file = root / 'requirements.txt'
        if req_file.exists():
            info.config_files['requirements.txt'] = req_file
            try:
                content = req_file.read_text()
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse requirement
                        pkg = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                        info.dependencies[pkg] = line
            except:
                pass
        
        # Entry points
        common_mains = ['main.py', 'app.py', 'manage.py', '__main__.py']
        for main in common_mains:
            if (root / main).exists():
                info.entry_points.append(main)
    
    def _load_go_context(self, info: ProjectInfo, root: Path):
        """Load Go project context."""
        go_mod = root / 'go.mod'
        if go_mod.exists():
            info.config_files['go.mod'] = go_mod
            try:
                content = go_mod.read_text()
                for line in content.split('\n'):
                    if line.startswith('module '):
                        info.name = line.split()[1]
                        break
            except:
                pass
    
    def _load_rust_context(self, info: ProjectInfo, root: Path):
        """Load Rust project context."""
        cargo_toml = root / 'Cargo.toml'
        if cargo_toml.exists():
            info.config_files['Cargo.toml'] = cargo_toml
            try:
                content = cargo_toml.read_text()
                for line in content.split('\n'):
                    if line.startswith('name = '):
                        info.name = line.split('=')[1].strip().strip('"')
                        break
            except:
                pass
    
    def _detect_tech_stack(self, info: ProjectInfo, root: Path):
        """Detect languages and frameworks used."""
        # Languages (by file extensions)
        lang_extensions = {
            'Python': ['.py'],
            'JavaScript': ['.js', '.jsx'],
            'TypeScript': ['.ts', '.tsx'],
            'Go': ['.go'],
            'Rust': ['.rs'],
            'HTML': ['.html'],
            'CSS': ['.css'],
        }
        
        found_langs = set()
        for lang, exts in lang_extensions.items():
            for ext in exts:
                # Quick check - look in common dirs
                for check_dir in [root, root / 'src', root / 'app']:
                    if check_dir.exists():
                        if any(check_dir.glob(f'*{ext}')):
                            found_langs.add(lang)
                            break
        
        info.languages = sorted(found_langs)
        
        # Frameworks (from dependencies)
        framework_markers = {
            'React': ['react'],
            'Next.js': ['next'],
            'Vue': ['vue'],
            'Express': ['express'],
            'Django': ['django'],
            'FastAPI': ['fastapi'],
            'Flask': ['flask'],
        }
        
        all_deps = {**info.dependencies, **info.dev_dependencies}
        for framework, markers in framework_markers.items():
            if any(marker in all_deps for marker in markers):
                info.frameworks.append(framework)
    
    def _find_main_dirs(self, info: ProjectInfo, root: Path):
        """Find main project directories."""
        common_dirs = ['src', 'app', 'lib', 'pages', 'components', 'utils', 'api', 'tests']
        
        for dir_name in common_dirs:
            dir_path = root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                info.main_dirs.append(dir_name)
