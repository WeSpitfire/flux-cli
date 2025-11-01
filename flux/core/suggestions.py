"""Proactive AI Suggestions - Anticipate developer needs and suggest improvements.

This module analyzes the current context and proactively suggests:
- Next logical actions
- Code quality improvements
- Security enhancements
- Performance optimizations
- Test coverage gaps
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time


class SuggestionType(Enum):
    """Type of suggestion."""
    NEXT_ACTION = "next_action"
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"


class Priority(Enum):
    """Priority level for suggestions."""
    CRITICAL = "critical"  # Security issues, breaking bugs
    HIGH = "high"          # Important improvements
    MEDIUM = "medium"      # Nice to have
    LOW = "low"            # Minor enhancements


@dataclass
class Suggestion:
    """A proactive suggestion."""
    type: SuggestionType
    priority: Priority
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    action: Optional[str] = None  # What Flux can do automatically
    confidence: float = 0.8  # 0.0 to 1.0
    reasoning: str = ""


@dataclass
class WorkContext:
    """Current work context."""
    current_file: Optional[str] = None
    recent_files: List[str] = field(default_factory=list)
    recent_commands: List[str] = field(default_factory=list)
    active_functions: List[str] = field(default_factory=list)
    detected_task: Optional[str] = None  # e.g., "authentication", "database"
    time_in_file: float = 0.0  # seconds


class SuggestionsEngine:
    """Generates proactive suggestions based on context."""
    
    def __init__(self, cwd: Path, codebase_graph=None):
        self.cwd = cwd
        self.codebase_graph = codebase_graph
        self.work_context = WorkContext()
        self.suggestion_history: List[Suggestion] = []
        
        # Pattern detectors
        self.security_patterns = self._load_security_patterns()
        self.performance_patterns = self._load_performance_patterns()
        self.quality_patterns = self._load_quality_patterns()
    
    def update_context(
        self, 
        current_file: Optional[str] = None,
        recent_command: Optional[str] = None
    ):
        """Update the work context."""
        if current_file:
            self.work_context.current_file = current_file
            if current_file not in self.work_context.recent_files:
                self.work_context.recent_files.append(current_file)
                self.work_context.recent_files = self.work_context.recent_files[-10:]  # Keep last 10
        
        if recent_command:
            self.work_context.recent_commands.append(recent_command)
            self.work_context.recent_commands = self.work_context.recent_commands[-20:]  # Keep last 20
        
        # Detect current task
        self.work_context.detected_task = self._detect_current_task()
    
    def get_suggestions(
        self, 
        max_suggestions: int = 5,
        min_priority: Priority = Priority.LOW
    ) -> List[Suggestion]:
        """Get proactive suggestions based on current context."""
        suggestions = []
        
        # 1. Next action suggestions
        suggestions.extend(self._suggest_next_actions())
        
        # 2. Code quality suggestions
        if self.work_context.current_file:
            suggestions.extend(self._suggest_code_quality_improvements())
        
        # 3. Security suggestions
        suggestions.extend(self._suggest_security_improvements())
        
        # 4. Performance suggestions
        suggestions.extend(self._suggest_performance_improvements())
        
        # 5. Testing suggestions
        suggestions.extend(self._suggest_testing_improvements())
        
        # 6. Documentation suggestions
        suggestions.extend(self._suggest_documentation_improvements())
        
        # Filter by priority
        priority_order = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        min_priority_index = priority_order.index(min_priority)
        suggestions = [
            s for s in suggestions 
            if priority_order.index(s.priority) <= min_priority_index
        ]
        
        # Sort by priority and confidence
        suggestions.sort(
            key=lambda s: (priority_order.index(s.priority), -s.confidence)
        )
        
        # Deduplicate
        seen_titles = set()
        unique_suggestions = []
        for s in suggestions:
            if s.title not in seen_titles:
                seen_titles.add(s.title)
                unique_suggestions.append(s)
        
        return unique_suggestions[:max_suggestions]
    
    def _suggest_next_actions(self) -> List[Suggestion]:
        """Suggest logical next steps based on recent activity."""
        suggestions = []
        
        current_file = self.work_context.current_file
        if not current_file:
            return suggestions
        
        # Detect file type and context
        file_path = Path(self.cwd) / current_file
        if not file_path.exists():
            return suggestions
        
        try:
            content = file_path.read_text()
        except Exception:
            return suggestions
        
        # Pattern: Working on authentication
        if self._is_auth_related(current_file, content):
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_ACTION,
                priority=Priority.HIGH,
                title="Add rate limiting to authentication",
                description="Prevent brute force attacks by limiting login attempts",
                file_path=current_file,
                action="Add rate limiting with exponential backoff",
                confidence=0.85,
                reasoning="Detected authentication code without rate limiting"
            ))
            
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_ACTION,
                priority=Priority.HIGH,
                title="Add security logging for auth events",
                description="Log authentication attempts, failures, and successes",
                file_path=current_file,
                action="Add comprehensive auth logging",
                confidence=0.82,
                reasoning="Auth code should log security events"
            ))
        
        # Pattern: Working on API endpoints
        if self._is_api_related(current_file, content):
            if not self._has_error_handling(content):
                suggestions.append(Suggestion(
                    type=SuggestionType.NEXT_ACTION,
                    priority=Priority.HIGH,
                    title="Add error handling to API endpoints",
                    description="Handle network errors, timeouts, and invalid responses",
                    file_path=current_file,
                    action="Add try-catch blocks with proper error responses",
                    confidence=0.88,
                    reasoning="API endpoints missing error handling"
                ))
            
            if not self._has_input_validation(content):
                suggestions.append(Suggestion(
                    type=SuggestionType.NEXT_ACTION,
                    priority=Priority.CRITICAL,
                    title="Add input validation",
                    description="Validate and sanitize user inputs to prevent injection attacks",
                    file_path=current_file,
                    action="Add input validation with schema checking",
                    confidence=0.90,
                    reasoning="API endpoints should validate inputs"
                ))
        
        # Pattern: Working on database code
        if self._is_database_related(current_file, content):
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_ACTION,
                priority=Priority.HIGH,
                title="Add database transaction handling",
                description="Ensure atomic operations and proper rollback",
                file_path=current_file,
                action="Wrap operations in transactions",
                confidence=0.80,
                reasoning="Database operations should use transactions"
            ))
        
        # Pattern: Modified file without tests
        if self._needs_tests(current_file):
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_ACTION,
                priority=Priority.MEDIUM,
                title="Generate tests for recent changes",
                description=f"Create test coverage for {Path(current_file).name}",
                file_path=current_file,
                action="Generate comprehensive test suite",
                confidence=0.85,
                reasoning="Modified code should have test coverage"
            ))
        
        return suggestions
    
    def _suggest_code_quality_improvements(self) -> List[Suggestion]:
        """Suggest code quality improvements."""
        suggestions = []
        
        current_file = self.work_context.current_file
        if not current_file:
            return suggestions
        
        file_path = Path(self.cwd) / current_file
        if not file_path.exists() or not current_file.endswith('.py'):
            return suggestions
        
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
        except Exception:
            return suggestions
        
        # Check for code smells
        
        # 1. Long functions (>50 lines)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_length = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if func_length > 50:
                    suggestions.append(Suggestion(
                        type=SuggestionType.CODE_QUALITY,
                        priority=Priority.MEDIUM,
                        title=f"Refactor long function: {node.name}()",
                        description=f"Function has {func_length} lines, consider breaking it up",
                        file_path=current_file,
                        line_number=node.lineno,
                        action=f"Extract helper functions from {node.name}()",
                        confidence=0.75,
                        reasoning="Functions over 50 lines are harder to maintain"
                    ))
        
        # 2. Missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    suggestions.append(Suggestion(
                        type=SuggestionType.DOCUMENTATION,
                        priority=Priority.LOW,
                        title=f"Add docstring to {node.name}",
                        description="Improve code documentation",
                        file_path=current_file,
                        line_number=node.lineno,
                        action=f"Generate docstring for {node.name}",
                        confidence=0.70,
                        reasoning="All functions and classes should have docstrings"
                    ))
        
        # 3. Unused imports
        imports = self._find_unused_imports(tree, content)
        if imports:
            suggestions.append(Suggestion(
                type=SuggestionType.CODE_QUALITY,
                priority=Priority.LOW,
                title="Remove unused imports",
                description=f"Found {len(imports)} unused import(s): {', '.join(imports[:3])}",
                file_path=current_file,
                action="Remove unused imports",
                confidence=0.85,
                reasoning="Clean code removes unused imports"
            ))
        
        return suggestions
    
    def _suggest_security_improvements(self) -> List[Suggestion]:
        """Suggest security improvements."""
        suggestions = []
        
        current_file = self.work_context.current_file
        if not current_file:
            return suggestions
        
        file_path = Path(self.cwd) / current_file
        if not file_path.exists():
            return suggestions
        
        try:
            content = file_path.read_text()
        except Exception:
            return suggestions
        
        # Check for security issues
        
        # 1. SQL Injection risk
        if re.search(r'execute\s*\(["\'].*%s.*["\']', content):
            suggestions.append(Suggestion(
                type=SuggestionType.SECURITY,
                priority=Priority.CRITICAL,
                title="Potential SQL injection vulnerability",
                description="Using string formatting in SQL queries",
                file_path=current_file,
                action="Use parameterized queries instead",
                confidence=0.90,
                reasoning="String formatting in SQL is dangerous"
            ))
        
        # 2. Hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']'
        ]
        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                suggestions.append(Suggestion(
                    type=SuggestionType.SECURITY,
                    priority=Priority.CRITICAL,
                    title="Hardcoded secrets detected",
                    description="Secrets should be in environment variables",
                    file_path=current_file,
                    action="Move secrets to environment variables",
                    confidence=0.85,
                    reasoning="Hardcoded secrets are a security risk"
                ))
                break  # Only suggest once
        
        # 3. Unsafe eval/exec
        if re.search(r'\beval\s*\(|\bexec\s*\(', content):
            suggestions.append(Suggestion(
                type=SuggestionType.SECURITY,
                priority=Priority.CRITICAL,
                title="Unsafe use of eval() or exec()",
                description="These functions can execute arbitrary code",
                file_path=current_file,
                action="Use safer alternatives like ast.literal_eval()",
                confidence=0.95,
                reasoning="eval/exec are dangerous with untrusted input"
            ))
        
        return suggestions
    
    def _suggest_performance_improvements(self) -> List[Suggestion]:
        """Suggest performance improvements."""
        suggestions = []
        
        current_file = self.work_context.current_file
        if not current_file or not current_file.endswith('.py'):
            return suggestions
        
        file_path = Path(self.cwd) / current_file
        if not file_path.exists():
            return suggestions
        
        try:
            content = file_path.read_text()
        except Exception:
            return suggestions
        
        # Check for performance issues
        
        # 1. Nested loops (potential N^2 or worse)
        if re.search(r'for\s+\w+\s+in.*:\s*\n\s+for\s+\w+\s+in', content):
            suggestions.append(Suggestion(
                type=SuggestionType.PERFORMANCE,
                priority=Priority.MEDIUM,
                title="Nested loops detected",
                description="May have O(N^2) or worse complexity",
                file_path=current_file,
                action="Consider using sets or dictionaries for faster lookup",
                confidence=0.70,
                reasoning="Nested loops can be slow with large data"
            ))
        
        # 2. String concatenation in loops
        if re.search(r'for\s+.*:\s*\n\s+\w+\s*\+=\s*["\']', content):
            suggestions.append(Suggestion(
                type=SuggestionType.PERFORMANCE,
                priority=Priority.LOW,
                title="String concatenation in loop",
                description="Using += for strings in loops is inefficient",
                file_path=current_file,
                action="Use list and join() instead",
                confidence=0.75,
                reasoning="String concatenation creates many temporary objects"
            ))
        
        return suggestions
    
    def _suggest_testing_improvements(self) -> List[Suggestion]:
        """Suggest testing improvements."""
        suggestions = []
        
        # Check if project has tests
        test_dirs = ['tests', 'test', '__tests__']
        has_tests = any((self.cwd / test_dir).exists() for test_dir in test_dirs)
        
        if not has_tests:
            suggestions.append(Suggestion(
                type=SuggestionType.TESTING,
                priority=Priority.HIGH,
                title="No tests directory found",
                description="Project should have automated tests",
                action="Create tests/ directory and add first test",
                confidence=0.90,
                reasoning="All projects should have tests"
            ))
        
        # Check if current file has tests
        current_file = self.work_context.current_file
        if current_file and self._needs_tests(current_file):
            suggestions.append(Suggestion(
                type=SuggestionType.TESTING,
                priority=Priority.MEDIUM,
                title=f"Add tests for {Path(current_file).name}",
                description="No test file found for this module",
                file_path=current_file,
                action="Generate test file with coverage",
                confidence=0.85,
                reasoning="Each module should have tests"
            ))
        
        return suggestions
    
    def _suggest_documentation_improvements(self) -> List[Suggestion]:
        """Suggest documentation improvements."""
        suggestions = []
        
        # Check for README
        readme_files = ['README.md', 'README.rst', 'README.txt']
        has_readme = any((self.cwd / readme).exists() for readme in readme_files)
        
        if not has_readme:
            suggestions.append(Suggestion(
                type=SuggestionType.DOCUMENTATION,
                priority=Priority.MEDIUM,
                title="No README file found",
                description="Project should have a README",
                action="Generate README with project description",
                confidence=0.95,
                reasoning="Every project needs a README"
            ))
        
        return suggestions
    
    # Helper methods
    
    def _detect_current_task(self) -> Optional[str]:
        """Detect what the user is working on."""
        if not self.work_context.current_file:
            return None
        
        current_file = self.work_context.current_file.lower()
        
        if 'auth' in current_file or 'login' in current_file:
            return "authentication"
        elif 'api' in current_file or 'endpoint' in current_file:
            return "api_development"
        elif 'db' in current_file or 'database' in current_file or 'model' in current_file:
            return "database"
        elif 'test' in current_file:
            return "testing"
        
        return None
    
    def _is_auth_related(self, file_path: str, content: str) -> bool:
        """Check if file is auth-related."""
        auth_keywords = ['auth', 'login', 'password', 'credential', 'token', 'session']
        return any(kw in file_path.lower() or kw in content.lower() for kw in auth_keywords)
    
    def _is_api_related(self, file_path: str, content: str) -> bool:
        """Check if file is API-related."""
        api_keywords = ['@app.route', '@router', 'endpoint', 'api', 'request', 'response']
        return any(kw in content.lower() for kw in api_keywords)
    
    def _is_database_related(self, file_path: str, content: str) -> bool:
        """Check if file has database code."""
        db_keywords = ['execute', 'query', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'commit', 'rollback']
        return any(kw in content for kw in db_keywords)
    
    def _has_error_handling(self, content: str) -> bool:
        """Check if code has error handling."""
        return 'try:' in content or 'except' in content
    
    def _has_input_validation(self, content: str) -> bool:
        """Check if code validates inputs."""
        validation_keywords = ['validate', 'schema', 'check_', 'assert', 'raise ValueError']
        return any(kw in content for kw in validation_keywords)
    
    def _needs_tests(self, file_path: str) -> bool:
        """Check if file needs tests."""
        if 'test' in file_path.lower():
            return False
        
        # Look for corresponding test file
        test_patterns = [
            file_path.replace('.py', '_test.py'),
            f"tests/test_{Path(file_path).name}",
            f"test/{Path(file_path).name}"
        ]
        
        return not any((self.cwd / pattern).exists() for pattern in test_patterns)
    
    def _find_unused_imports(self, tree: ast.AST, content: str) -> List[str]:
        """Find unused imports."""
        unused = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    # Simple check: if import name doesn't appear elsewhere in code
                    if content.count(name) == 1:  # Only appears in import line
                        unused.append(name)
        
        return unused[:3]  # Limit to 3
    
    def _load_security_patterns(self) -> List[Dict]:
        """Load security vulnerability patterns."""
        return [
            {'pattern': r'eval\s*\(', 'severity': 'critical', 'message': 'Unsafe eval()'},
            {'pattern': r'exec\s*\(', 'severity': 'critical', 'message': 'Unsafe exec()'},
            {'pattern': r'password\s*=\s*["\']', 'severity': 'critical', 'message': 'Hardcoded password'},
        ]
    
    def _load_performance_patterns(self) -> List[Dict]:
        """Load performance anti-patterns."""
        return [
            {'pattern': r'for.*:\s*\n\s*for', 'severity': 'medium', 'message': 'Nested loops'},
        ]
    
    def _load_quality_patterns(self) -> List[Dict]:
        """Load code quality patterns."""
        return []


def create_suggestions_engine(cwd: Path, codebase_graph=None) -> SuggestionsEngine:
    """Create a suggestions engine instance."""
    return SuggestionsEngine(cwd, codebase_graph)
