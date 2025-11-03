"""Smart Auto-Initialization for Flux.

This module automatically enables features and watchers based on:
- Project type (Python, JavaScript, etc.)
- Project structure (tests, CI/CD, etc.)
- User behavior patterns
- Configuration preferences

Goal: Make Flux work out of the box without manual setup.
"""

from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class InitializationConfig:
    """Configuration for auto-initialization."""
    enable_auto_fix: bool = True
    enable_auto_fix_watch: bool = True
    enable_test_watch: bool = False  # More conservative - only if tests exist
    build_codebase_graph: bool = True
    show_startup_tips: bool = True


class SmartInitializer:
    """Intelligently initialize Flux features based on project context."""
    
    def __init__(self, cwd: Path):
        """Initialize with project directory.
        
        Args:
            cwd: Current working directory (project root)
        """
        self.cwd = cwd
        self.project_files = list(cwd.rglob('*'))[:1000]  # Limit for performance
    
    def detect_project_features(self) -> Dict[str, bool]:
        """Detect project features to guide initialization.
        
        Returns:
            Dict of detected features
        """
        features = {
            'has_tests': self._has_tests(),
            'has_git': self._has_git(),
            'has_ci': self._has_ci(),
            'has_linter': self._has_linter(),
            'is_python': self._is_python_project(),
            'is_javascript': self._is_javascript_project(),
            'is_typescript': self._is_typescript_project(),
            'has_package_json': (self.cwd / 'package.json').exists(),
            'has_pyproject': (self.cwd / 'pyproject.toml').exists(),
        }
        return features
    
    def create_initialization_plan(self) -> InitializationConfig:
        """Create smart initialization plan based on project.
        
        Returns:
            InitializationConfig with recommended settings
        """
        features = self.detect_project_features()
        config = InitializationConfig()
        
        # Always enable auto-fix and codebase graph
        config.enable_auto_fix = True
        config.build_codebase_graph = True
        
        # Enable auto-fix watch if it's a code project
        if features['is_python'] or features['is_javascript'] or features['is_typescript']:
            config.enable_auto_fix_watch = True
        
        # Enable test watch if project has tests
        if features['has_tests']:
            config.enable_test_watch = True
        
        # Show tips for first 5 sessions
        config.show_startup_tips = self._should_show_tips()
        
        return config
    
    def get_startup_message(self, config: InitializationConfig, features: Dict[str, bool]) -> List[str]:
        """Generate friendly startup message.
        
        Args:
            config: Initialization config used
            features: Detected project features
            
        Returns:
            List of message lines
        """
        messages = []
        
        # Project type
        if features['is_python']:
            messages.append("🐍 Python project detected")
        elif features['is_typescript']:
            messages.append("📘 TypeScript project detected")
        elif features['is_javascript']:
            messages.append("📗 JavaScript project detected")
        
        # Auto-enabled features
        enabled_features = []
        if config.enable_auto_fix_watch:
            enabled_features.append("Auto-fix on save")
        if config.enable_test_watch:
            enabled_features.append("Test watching")
        if config.build_codebase_graph:
            enabled_features.append("Code intelligence")
        
        if enabled_features:
            messages.append(f"✨ Enabled: {', '.join(enabled_features)}")
        
        # Tips
        if config.show_startup_tips:
            messages.append("")
            messages.append("💡 Just talk naturally - no commands needed")
            messages.append("   Try: 'run the tests' or 'fix the formatting'")
        
        return messages
    
    # Detection helpers
    
    def _has_tests(self) -> bool:
        """Check if project has tests."""
        test_indicators = [
            'test', 'tests', '__tests__', 'spec', 'specs',
            'test_*.py', '*_test.py', '*.test.js', '*.spec.ts'
        ]
        
        for file in self.project_files[:500]:  # Check first 500 files
            name_lower = file.name.lower()
            for indicator in test_indicators:
                if indicator in name_lower or file.parent.name in ['tests', 'test', '__tests__']:
                    return True
        return False
    
    def _has_git(self) -> bool:
        """Check if project uses git."""
        return (self.cwd / '.git').exists()
    
    def _has_ci(self) -> bool:
        """Check if project has CI/CD setup."""
        ci_files = [
            '.github/workflows',
            '.gitlab-ci.yml',
            '.travis.yml',
            'Jenkinsfile',
            '.circleci'
        ]
        return any((self.cwd / ci_file).exists() for ci_file in ci_files)
    
    def _has_linter(self) -> bool:
        """Check if project has linter config."""
        linter_files = [
            '.eslintrc', '.eslintrc.js', '.eslintrc.json',
            'pylint.rc', '.pylintrc',
            'pyproject.toml',  # Often contains ruff/black config
            '.flake8'
        ]
        return any((self.cwd / linter_file).exists() for linter_file in linter_files)
    
    def _is_python_project(self) -> bool:
        """Check if this is a Python project."""
        python_indicators = [
            'setup.py', 'pyproject.toml', 'requirements.txt',
            'Pipfile', 'poetry.lock', 'setup.cfg'
        ]
        if any((self.cwd / indicator).exists() for indicator in python_indicators):
            return True
        
        # Check for .py files
        py_files = list(self.cwd.glob('*.py'))
        return len(py_files) > 0
    
    def _is_javascript_project(self) -> bool:
        """Check if this is a JavaScript project."""
        return (self.cwd / 'package.json').exists() and not self._is_typescript_project()
    
    def _is_typescript_project(self) -> bool:
        """Check if this is a TypeScript project."""
        return (self.cwd / 'tsconfig.json').exists() or (self.cwd / 'package.json').exists()
    
    def _should_show_tips(self) -> bool:
        """Check if we should show startup tips.
        
        Returns:
            True if tips should be shown (first 5 sessions)
        """
        # Check for session count file
        flux_dir = self.cwd / '.flux'
        if not flux_dir.exists():
            return True
        
        session_file = flux_dir / 'session_count'
        if not session_file.exists():
            # First session
            flux_dir.mkdir(exist_ok=True)
            session_file.write_text('1')
            return True
        
        try:
            count = int(session_file.read_text().strip())
            # Update count
            session_file.write_text(str(count + 1))
            # Show tips for first 5 sessions
            return count <= 5
        except:
            return True


async def auto_initialize(cli_instance) -> None:
    """Auto-initialize Flux features based on project.
    
    This is called on CLI startup to intelligently enable features
    without requiring user configuration.
    
    Args:
        cli_instance: CLI instance to initialize
    """
    initializer = SmartInitializer(cli_instance.cwd)
    
    # Detect project and create plan
    features = initializer.detect_project_features()
    config = initializer.create_initialization_plan()
    
    # Display startup message
    messages = initializer.get_startup_message(config, features)
    if messages:
        cli_instance.console.print()
        for msg in messages:
            if msg:  # Skip empty lines
                cli_instance.console.print(f"  {msg}")
        cli_instance.console.print()
    
    # Enable features based on config
    
    # 1. Auto-fix mode
    if config.enable_auto_fix:
        cli_instance.auto_fixer.enabled = True
    
    # 2. Auto-fix watch mode (fix on save)
    if config.enable_auto_fix_watch:
        try:
            await cli_instance.start_autofix_watch(silent=True)
        except Exception as e:
            # Silently fail - not critical
            pass
    
    # 3. Test watch mode (if tests exist)
    if config.enable_test_watch:
        try:
            # Only enable if we can detect test framework
            framework = cli_instance.test_runner.detect_framework()
            if framework != 'unknown':
                await cli_instance.start_test_watch()
        except Exception:
            # Silently fail - not critical
            pass
    
    # 4. Build codebase graph (in background)
    if config.build_codebase_graph:
        try:
            import asyncio
            # Start in background without blocking
            asyncio.create_task(cli_instance.build_codebase_graph())
        except Exception:
            # Silently fail - not critical
            pass


def get_quick_start_tips() -> List[str]:
    """Get quick start tips for new users.
    
    Returns:
        List of helpful tips
    """
    return [
        "💬 Talk naturally - Flux understands natural language",
        "   • 'run the tests' → Executes tests",
        "   • 'fix the formatting' → Auto-fixes code",
        "   • 'save my work' → Creates smart commit",
        "",
        "🎯 Flux works best with goals, not commands",
        "   • 'add login page with validation'",
        "   • 'fix the failing tests'",
        "   • 'refactor this function'",
        "",
        "⚡ Features enabled automatically:",
        "   • Auto-fix on save (formatting, imports)",
        "   • Code intelligence (suggestions)",
        "   • Error detection",
        "",
        "📚 Use /help to see all available commands",
    ]
