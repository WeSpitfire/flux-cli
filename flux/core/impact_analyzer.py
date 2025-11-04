"""Impact Analysis - Show what will be affected by code changes.

This module analyzes potential changes and shows:
- What files will be modified
- What functions/classes will be affected
- What dependencies might break
- Confidence levels for safety
"""

import ast
import difflib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


class ChangeType(Enum):
    """Type of change being made."""
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"
    REFACTOR = "refactor"


class ImpactLevel(Enum):
    """Severity of impact."""
    LOW = "low"          # Single file, single function
    MEDIUM = "medium"    # Multiple functions, limited scope
    HIGH = "high"        # Cross-file changes
    CRITICAL = "critical"  # Core infrastructure changes


@dataclass
class DependencyImpact:
    """Impact on a specific dependency."""
    file_path: str
    impact_type: str  # 'direct', 'indirect', 'test'
    functions_used: List[str] = field(default_factory=list)
    classes_used: List[str] = field(default_factory=list)
    confidence: float = 1.0
    break_risk: str = "low"  # low, medium, high


@dataclass
class ChangeImpact:
    """Impact analysis for a proposed change."""
    file_path: str
    change_type: ChangeType
    impact_level: ImpactLevel
    confidence_score: float  # 0.0 to 1.0

    # What will be affected
    functions_affected: List[str] = field(default_factory=list)
    classes_affected: List[str] = field(default_factory=list)
    dependencies_affected: List[str] = field(default_factory=list)
    tests_need_update: List[str] = field(default_factory=list)

    # Enhanced dependency impact
    dependency_tree: Dict[str, DependencyImpact] = field(default_factory=dict)
    propagation_depth: int = 0  # How many layers deep the impact goes

    # Risk assessment
    breaks_existing_code: bool = False
    requires_migration: bool = False
    affects_public_api: bool = False

    # Human-readable explanation
    summary: str = ""
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class DiffPreview:
    """Visual preview of changes."""
    file_path: str
    old_content: str
    new_content: str
    unified_diff: str
    line_changes: Dict[str, int] = field(default_factory=dict)  # {'added': n, 'removed': m}


class ImpactAnalyzer:
    """Analyzes the impact of proposed code changes."""

    def __init__(self, cwd: Path, codebase_graph=None):
        self.cwd = cwd
        self.codebase_graph = codebase_graph

    def analyze_change(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        change_description: Optional[str] = None
    ) -> ChangeImpact:
        """Analyze the impact of a proposed change."""

        # Determine change type
        change_type = self._determine_change_type(old_content, new_content)

        # Calculate impact level
        impact_level = self._calculate_impact_level(file_path, old_content, new_content)

        # Calculate confidence score
        confidence = self._calculate_confidence(file_path, old_content, new_content)

        # Analyze what's affected
        functions_affected = self._find_affected_functions(old_content, new_content)
        classes_affected = self._find_affected_classes(old_content, new_content)
        dependencies_affected = self._find_affected_dependencies(file_path)
        tests_need_update = self._find_tests_to_update(file_path, functions_affected)

        # Build detailed dependency impact tree
        dependency_tree = self._build_dependency_tree(file_path, functions_affected, classes_affected)
        propagation_depth = self._calculate_propagation_depth(dependency_tree)

        # Risk assessment
        breaks_existing = self._check_breaking_changes(old_content, new_content)
        requires_migration = self._check_migration_needed(old_content, new_content)
        affects_api = self._check_public_api_impact(file_path, functions_affected)

        # Generate summary
        summary = self._generate_summary(
            file_path, change_type, functions_affected, classes_affected
        )

        # Generate warnings and suggestions
        warnings = self._generate_warnings(impact_level, breaks_existing, dependencies_affected)
        suggestions = self._generate_suggestions(change_type, tests_need_update)

        return ChangeImpact(
            file_path=file_path,
            change_type=change_type,
            impact_level=impact_level,
            confidence_score=confidence,
            functions_affected=functions_affected,
            classes_affected=classes_affected,
            dependencies_affected=dependencies_affected,
            tests_need_update=tests_need_update,
            dependency_tree=dependency_tree,
            propagation_depth=propagation_depth,
            breaks_existing_code=breaks_existing,
            requires_migration=requires_migration,
            affects_public_api=affects_api,
            summary=summary,
            warnings=warnings,
            suggestions=suggestions
        )

    def create_diff_preview(self, file_path: str, old_content: str, new_content: str) -> DiffPreview:
        """Create a visual diff preview."""
        # Generate unified diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{file_path} (before)",
            tofile=f"{file_path} (after)",
            lineterm=''
        )

        unified_diff = '\n'.join(diff)

        # Count line changes
        added = sum(1 for line in new_lines if line not in old_lines)
        removed = sum(1 for line in old_lines if line not in new_lines)

        return DiffPreview(
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
            unified_diff=unified_diff,
            line_changes={'added': added, 'removed': removed, 'modified': min(added, removed)}
        )

    # Internal methods

    def _determine_change_type(self, old_content: str, new_content: str) -> ChangeType:
        """Determine the type of change."""
        if not old_content:
            return ChangeType.ADD
        if not new_content:
            return ChangeType.DELETE

        # Simple heuristic: if >50% different, it's a refactor
        similarity = difflib.SequenceMatcher(None, old_content, new_content).ratio()
        if similarity < 0.5:
            return ChangeType.REFACTOR

        return ChangeType.MODIFY

    def _calculate_impact_level(self, file_path: str, old_content: str, new_content: str) -> ImpactLevel:
        """Calculate the impact level of changes."""
        # Count changes
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        lines_changed = abs(len(new_lines) - len(old_lines))

        # Check if it's a core file
        is_core = any(core in file_path for core in ['core/', 'main.py', '__init__.py'])

        # Determine impact
        if lines_changed > 100 or is_core:
            return ImpactLevel.CRITICAL
        elif lines_changed > 50:
            return ImpactLevel.HIGH
        elif lines_changed > 20:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW

    def _calculate_confidence(self, file_path: str, old_content: str, new_content: str) -> float:
        """Calculate confidence score for the change."""
        confidence = 1.0

        # Reduce confidence for large changes
        lines_changed = abs(len(new_content.splitlines()) - len(old_content.splitlines()))
        if lines_changed > 100:
            confidence *= 0.7
        elif lines_changed > 50:
            confidence *= 0.8
        elif lines_changed > 20:
            confidence *= 0.9

        # Reduce confidence if syntax might be invalid
        try:
            if file_path.endswith('.py'):
                ast.parse(new_content)
        except SyntaxError:
            confidence *= 0.5

        # Increase confidence if tests exist
        if self.codebase_graph:
            test_file = file_path.replace('.py', '_test.py').replace('src/', 'tests/')
            if any(test_file in f for f in self.codebase_graph.files.keys()):
                confidence = min(1.0, confidence * 1.1)

        return round(confidence, 2)

    def _find_affected_functions(self, old_content: str, new_content: str) -> List[str]:
        """Find functions that are affected by changes."""
        affected = []

        try:
            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)

            old_functions = {node.name for node in ast.walk(old_tree) if isinstance(node, ast.FunctionDef)}
            new_functions = {node.name for node in ast.walk(new_tree) if isinstance(node, ast.FunctionDef)}

            # Functions that were modified or removed
            affected = list(old_functions - new_functions) + list(new_functions - old_functions)

            # Functions that exist in both but might be modified
            common = old_functions & new_functions
            for func in common:
                # Simple check: if function body changed significantly
                # (More sophisticated analysis would compare ASTs)
                if func in old_content and func in new_content:
                    old_func_content = self._extract_function_content(old_content, func)
                    new_func_content = self._extract_function_content(new_content, func)
                    if old_func_content != new_func_content:
                        affected.append(func)

        except SyntaxError:
            pass

        return affected[:10]  # Limit to top 10

    def _find_affected_classes(self, old_content: str, new_content: str) -> List[str]:
        """Find classes that are affected by changes."""
        affected = []

        try:
            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)

            old_classes = {node.name for node in ast.walk(old_tree) if isinstance(node, ast.ClassDef)}
            new_classes = {node.name for node in ast.walk(new_tree) if isinstance(node, ast.ClassDef)}

            affected = list((old_classes | new_classes) - (old_classes & new_classes))

        except SyntaxError:
            pass

        return affected[:10]

    def _find_affected_dependencies(self, file_path: str) -> List[str]:
        """Find files that depend on this file."""
        if not self.codebase_graph:
            return []

        if file_path not in self.codebase_graph.files:
            return []

        file_node = self.codebase_graph.files[file_path]
        return file_node.dependents[:5]  # Top 5 dependents

    def _find_tests_to_update(self, file_path: str, functions_affected: List[str]) -> List[str]:
        """Find test files that might need updating."""
        tests = []

        # Look for corresponding test file
        test_patterns = [
            file_path.replace('.py', '_test.py'),
            file_path.replace('src/', 'tests/test_'),
            f"tests/test_{Path(file_path).name}",
        ]

        if self.codebase_graph:
            for pattern in test_patterns:
                if any(pattern in f for f in self.codebase_graph.files.keys()):
                    tests.append(pattern)

        return tests

    def _check_breaking_changes(self, old_content: str, new_content: str) -> bool:
        """Check if changes might break existing code."""
        # Simple heuristics
        # - Removing functions/classes
        # - Changing function signatures

        try:
            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)

            old_functions = {node.name for node in ast.walk(old_tree) if isinstance(node, ast.FunctionDef)}
            new_functions = {node.name for node in ast.walk(new_tree) if isinstance(node, ast.FunctionDef)}

            # Functions were removed
            if old_functions - new_functions:
                return True

        except SyntaxError:
            return True  # Syntax errors definitely break things

        return False

    def _check_migration_needed(self, old_content: str, new_content: str) -> bool:
        """Check if changes require data migration."""
        # Simple check: look for database/model changes
        migration_keywords = ['class.*Model', 'Table', 'Column', 'migration', 'schema']

        for keyword in migration_keywords:
            if keyword in new_content and keyword not in old_content:
                return True

        return False

    def _check_public_api_impact(self, file_path: str, functions_affected: List[str]) -> bool:
        """Check if changes affect public API."""
        # Heuristic: files in certain directories or with certain names are public
        public_indicators = ['api/', 'public/', 'interface/', '__init__.py']

        if any(indicator in file_path for indicator in public_indicators):
            return len(functions_affected) > 0

        return False

    def _extract_function_content(self, content: str, function_name: str) -> str:
        """Extract function content from source."""
        # Simple extraction (not perfect but good enough)
        lines = content.splitlines()
        in_function = False
        function_lines = []

        for line in lines:
            if f'def {function_name}(' in line:
                in_function = True
            if in_function:
                function_lines.append(line)
                if line.strip() and not line.startswith(' ') and len(function_lines) > 1:
                    break

        return '\n'.join(function_lines)

    def _generate_summary(
        self,
        file_path: str,
        change_type: ChangeType,
        functions: List[str],
        classes: List[str]
    ) -> str:
        """Generate human-readable summary."""
        summary = f"Will {change_type.value} {file_path}"

        if functions:
            summary += f"\nAffects {len(functions)} function(s): {', '.join(functions[:3])}"
            if len(functions) > 3:
                summary += f" and {len(functions) - 3} more"

        if classes:
            summary += f"\nAffects {len(classes)} class(es): {', '.join(classes[:3])}"

        return summary

    def _generate_warnings(
        self,
        impact_level: ImpactLevel,
        breaks_existing: bool,
        dependencies: List[str]
    ) -> List[str]:
        """Generate warnings about potential issues."""
        warnings = []

        if impact_level == ImpactLevel.CRITICAL:
            warnings.append("⚠️  This is a critical change affecting core functionality")

        if breaks_existing:
            warnings.append("⚠️  This change might break existing code")

        if dependencies:
            warnings.append(f"⚠️  {len(dependencies)} file(s) depend on this: {', '.join(dependencies[:2])}")

        return warnings

    def _generate_suggestions(self, change_type: ChangeType, tests: List[str]) -> List[str]:
        """Generate helpful suggestions."""
        suggestions = []

        if tests:
            suggestions.append(f"💡 Update tests: {', '.join(tests)}")
        else:
            suggestions.append("💡 Consider adding tests for this change")

        if change_type == ChangeType.REFACTOR:
            suggestions.append("💡 Review all call sites to ensure compatibility")

        return suggestions

    def _build_dependency_tree(self, file_path: str, functions_affected: List[str], classes_affected: List[str]) -> Dict[str, DependencyImpact]:
        """Build detailed dependency impact tree."""
        dependency_tree = {}

        if not self.codebase_graph or file_path not in self.codebase_graph.files:
            return dependency_tree

        file_node = self.codebase_graph.files[file_path]

        # Direct dependencies (files that depend on this file)
        for dependent_path in file_node.dependents[:10]:  # Limit to prevent overwhelming output
            if dependent_path in self.codebase_graph.files:
                dependent_node = self.codebase_graph.files[dependent_path]

                # Analyze what functions/classes are used
                functions_used = self._find_used_functions(dependent_path, functions_affected)
                classes_used = self._find_used_classes(dependent_path, classes_affected)

                # Determine break risk
                break_risk = self._assess_break_risk(functions_used, classes_used, dependent_path)

                # Determine impact type
                impact_type = "test" if "/test" in dependent_path or "_test.py" in dependent_path else "direct"

                dependency_tree[dependent_path] = DependencyImpact(
                    file_path=dependent_path,
                    impact_type=impact_type,
                    functions_used=functions_used,
                    classes_used=classes_used,
                    confidence=0.9,
                    break_risk=break_risk
                )

        # Indirect dependencies (files that depend on direct dependents)
        for dependent_path in list(dependency_tree.keys())[:5]:  # Only check first 5 direct deps
            if dependent_path in self.codebase_graph.files:
                dependent_node = self.codebase_graph.files[dependent_path]
                for indirect_path in dependent_node.dependents[:3]:  # Limit indirect
                    if indirect_path not in dependency_tree and indirect_path != file_path:
                        dependency_tree[indirect_path] = DependencyImpact(
                            file_path=indirect_path,
                            impact_type="indirect",
                            functions_used=[],
                            classes_used=[],
                            confidence=0.6,
                            break_risk="low"
                        )

        return dependency_tree

    def _calculate_propagation_depth(self, dependency_tree: Dict[str, DependencyImpact]) -> int:
        """Calculate how many layers deep the impact propagates."""
        if not dependency_tree:
            return 0

        has_indirect = any(dep.impact_type == "indirect" for dep in dependency_tree.values())
        has_direct = any(dep.impact_type == "direct" for dep in dependency_tree.values())

        if has_indirect:
            return 2
        elif has_direct:
            return 1
        else:
            return 0

    def _find_used_functions(self, dependent_path: str, functions_affected: List[str]) -> List[str]:
        """Find which affected functions are used by a dependent file."""
        try:
            dependent_file = Path(self.cwd) / dependent_path
            if not dependent_file.exists():
                return []

            content = dependent_file.read_text()
            used_functions = []

            for func in functions_affected:
                # Simple regex to find function usage
                if re.search(rf'\b{func}\s*\(', content):
                    used_functions.append(func)

            return used_functions
        except Exception:
            return []

    def _find_used_classes(self, dependent_path: str, classes_affected: List[str]) -> List[str]:
        """Find which affected classes are used by a dependent file."""
        try:
            dependent_file = Path(self.cwd) / dependent_path
            if not dependent_file.exists():
                return []

            content = dependent_file.read_text()
            used_classes = []

            for cls in classes_affected:
                # Look for class instantiation or inheritance
                if re.search(rf'\b{cls}\s*\(|\b{cls}\.|class.*{cls}', content):
                    used_classes.append(cls)

            return used_classes
        except Exception:
            return []

    def _assess_break_risk(self, functions_used: List[str], classes_used: List[str], dependent_path: str) -> str:
        """Assess the risk of breaking a dependent file."""
        total_usage = len(functions_used) + len(classes_used)

        # Test files are lower risk
        if "/test" in dependent_path or "_test.py" in dependent_path:
            return "low" if total_usage <= 2 else "medium"

        # Main application files
        if total_usage >= 5:
            return "high"
        elif total_usage >= 2:
            return "medium"
        else:
            return "low"


def create_impact_analyzer(cwd: Path, codebase_graph=None) -> ImpactAnalyzer:
    """Create an impact analyzer instance."""
    return ImpactAnalyzer(cwd, codebase_graph)
