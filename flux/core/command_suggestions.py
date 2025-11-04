"""Command Suggestions System - Context-aware command suggestions.

Analyzes current project state, user patterns, and recent activity to suggest
the most relevant next commands. Uses rule-based intelligence without ML.

This is different from suggestions.py which focuses on code quality suggestions.
This module suggests *workflow commands* like /test, /commit, /workflow, etc.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class CommandSuggestion:
    """A single command suggestion with context."""
    command: str
    reason: str
    confidence: float  # 0.0 to 1.0
    icon: str = "💡"
    category: str = "general"  # test, git, workflow, fix, monitor

    def format(self) -> str:
        """Format suggestion for display."""
        return f"{self.icon} [cyan]{self.command}[/cyan] - {self.reason}"


class CommandSuggestionEngine:
    """Generates context-aware command suggestions based on current state."""

    def __init__(
        self,
        session_manager,
        state_tracker,
        git,
        proactive_monitor,
        workflow_manager
    ):
        """Initialize command suggestion engine.

        Args:
            session_manager: SessionManager instance
            state_tracker: StateTracker instance
            git: GitIntegration instance
            proactive_monitor: ProactiveMonitor instance
            workflow_manager: WorkflowManager instance
        """
        self.session = session_manager
        self.state = state_tracker
        self.git = git
        self.monitor = proactive_monitor
        self.workflows = workflow_manager

    def get_suggestions(self, max_suggestions: int = 3) -> List[CommandSuggestion]:
        """Get top context-aware command suggestions.

        Args:
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of CommandSuggestion objects, sorted by confidence
        """
        suggestions = []

        # Analyze current context
        context = self._analyze_context()

        # Generate suggestions based on different signals
        suggestions.extend(self._suggest_test_actions(context))
        suggestions.extend(self._suggest_git_actions(context))
        suggestions.extend(self._suggest_workflow_actions(context))
        suggestions.extend(self._suggest_fix_actions(context))
        suggestions.extend(self._suggest_monitor_actions(context))
        suggestions.extend(self._suggest_validation_actions(context))

        # Sort by confidence and return top N
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        # Deduplicate by command
        seen_commands = set()
        unique_suggestions = []
        for s in suggestions:
            if s.command not in seen_commands:
                seen_commands.add(s.command)
                unique_suggestions.append(s)

        return unique_suggestions[:max_suggestions]

    def _analyze_context(self) -> Dict[str, Any]:
        """Analyze current project and user context.

        Returns:
            Dict with context information
        """
        context = {
            # Git state
            'has_changes': False,
            'has_staged_changes': False,
            'total_changes': 0,

            # Test state
            'last_test_failed': False,
            'last_test_passed': False,
            'has_test_failures': False,
            'recent_test_count': 0,

            # File state
            'recently_modified_files': [],
            'files_modified_count': 0,

            # Session patterns
            'recent_pattern': None,
            'last_workflow': None,
            'last_command': None,

            # Monitor state
            'monitors_running': False,
            'recent_monitor_failures': [],

            # Workflow availability
            'available_workflows': [],
        }

        # Analyze git state
        try:
            git_status = self.git.get_status()
            if git_status.is_repo:
                context['has_changes'] = git_status.has_changes
                context['has_staged_changes'] = len(git_status.staged_files) > 0
                context['total_changes'] = git_status.total_changes
        except:
            pass

        # Analyze state tracker
        try:
            state_summary = self.state.get_context_summary(max_age_minutes=30)

            # Test state
            if state_summary['tests']['recent_count'] > 0:
                context['last_test_passed'] = state_summary['tests'].get('last_passed', False)
                context['last_test_failed'] = not context['last_test_passed']
                context['has_test_failures'] = len(state_summary['tests'].get('recent_failures', [])) > 0
                context['recent_test_count'] = state_summary['tests']['recent_count']

            # File state
            context['recently_modified_files'] = state_summary['files'].get('recently_modified', [])
            context['files_modified_count'] = len(context['recently_modified_files'])
        except:
            pass

        # Analyze session patterns
        try:
            patterns = self.session.detect_patterns()
            context['recent_pattern'] = patterns[0] if patterns else None
            context['last_workflow'] = self.session.get_last_workflow()

            recent_events = self.session.get_recent_events(limit=1)
            if recent_events:
                context['last_command'] = recent_events[0].get('type')
        except:
            pass

        # Analyze monitor state
        try:
            monitor_status = self.monitor.get_status()
            context['monitors_running'] = monitor_status.get('running', False)
            context['recent_monitor_failures'] = [
                e for e in monitor_status.get('last_events', [])
                if 'failed' in str(e).lower()
            ]
        except:
            pass

        # Get available workflows
        try:
            context['available_workflows'] = self.workflows.list_workflows()
        except:
            pass

        return context

    def _suggest_test_actions(self, context: Dict) -> List[CommandSuggestion]:
        """Suggest test-related actions."""
        suggestions = []

        # Test just failed - suggest fix
        if context['last_test_failed']:
            suggestions.append(CommandSuggestion(
                command="/fix",
                reason="Last test run failed - auto-fix available",
                confidence=0.95,
                icon="🔧",
                category="fix"
            ))
            suggestions.append(CommandSuggestion(
                command="/test",
                reason="Re-run tests after fixes",
                confidence=0.85,
                icon="🧪",
                category="test"
            ))

        # Tests passing and changes made - suggest running tests
        elif context['files_modified_count'] > 0 and context['recent_test_count'] == 0:
            suggestions.append(CommandSuggestion(
                command="/test",
                reason=f"{context['files_modified_count']} files modified - run tests",
                confidence=0.80,
                icon="🧪",
                category="test"
            ))

        # No recent tests - suggest running
        elif context['recent_test_count'] == 0 and context['files_modified_count'] > 2:
            suggestions.append(CommandSuggestion(
                command="/test",
                reason="Haven't run tests recently",
                confidence=0.60,
                icon="🧪",
                category="test"
            ))

        return suggestions

    def _suggest_git_actions(self, context: Dict) -> List[CommandSuggestion]:
        """Suggest git-related actions."""
        suggestions = []

        # Tests passing and changes exist - suggest commit
        if context['last_test_passed'] and context['has_changes']:
            suggestions.append(CommandSuggestion(
                command="/commit",
                reason="Tests passing - ready to commit",
                confidence=0.90,
                icon="✅",
                category="git"
            ))

        # Changes exist but no tests - suggest showing diff
        elif context['has_changes'] and not context['has_staged_changes']:
            suggestions.append(CommandSuggestion(
                command="/diff",
                reason=f"{context['total_changes']} files changed - review changes",
                confidence=0.75,
                icon="📝",
                category="git"
            ))

        # Staged changes - remind about commit
        elif context['has_staged_changes']:
            suggestions.append(CommandSuggestion(
                command="/commit",
                reason="Changes staged - ready to commit",
                confidence=0.85,
                icon="📦",
                category="git"
            ))

        return suggestions

    def _suggest_workflow_actions(self, context: Dict) -> List[CommandSuggestion]:
        """Suggest workflow-related actions."""
        suggestions = []

        # Pattern: edit -> test -> commit -> deploy
        if context['recent_pattern'] == 'edit-test-commit':
            if 'deploy-staging' in context['available_workflows']:
                suggestions.append(CommandSuggestion(
                    command="/workflow deploy-staging",
                    reason="Following your typical workflow pattern",
                    confidence=0.70,
                    icon="🚀",
                    category="workflow"
                ))

        # Last workflow was pr-ready - suggest deploy next
        if context['last_workflow'] == 'pr-ready':
            if 'deploy-staging' in context['available_workflows']:
                suggestions.append(CommandSuggestion(
                    command="/workflow deploy-staging",
                    reason="PR ready - deploy to staging",
                    confidence=0.75,
                    icon="🚀",
                    category="workflow"
                ))

        # Many changes and tests passing - suggest pr-ready
        if context['files_modified_count'] > 3 and context['last_test_passed']:
            if 'pr-ready' in context['available_workflows']:
                suggestions.append(CommandSuggestion(
                    command="/workflow pr-ready",
                    reason="Multiple files changed - prepare PR",
                    confidence=0.70,
                    icon="📋",
                    category="workflow"
                ))

        # Quick check before commit
        if context['has_changes'] and not context['last_test_passed']:
            if 'quick-check' in context['available_workflows']:
                suggestions.append(CommandSuggestion(
                    command="/workflow quick-check",
                    reason="Run quick validation before commit",
                    confidence=0.65,
                    icon="⚡",
                    category="workflow"
                ))

        return suggestions

    def _suggest_fix_actions(self, context: Dict) -> List[CommandSuggestion]:
        """Suggest fix-related actions."""
        suggestions = []

        # Test failures exist - suggest validate
        if context['has_test_failures']:
            suggestions.append(CommandSuggestion(
                command="/validate",
                reason="Test failures detected - validate modified files",
                confidence=0.80,
                icon="🔍",
                category="fix"
            ))

        # Recent modifications - suggest autofix
        if context['files_modified_count'] > 0:
            suggestions.append(CommandSuggestion(
                command="/autofix",
                reason="Auto-fix formatting and simple issues",
                confidence=0.55,
                icon="✨",
                category="fix"
            ))

        return suggestions

    def _suggest_monitor_actions(self, context: Dict) -> List[CommandSuggestion]:
        """Suggest monitoring-related actions."""
        suggestions = []

        # Test failures and no monitors - suggest watching tests
        if context['has_test_failures'] and not context['monitors_running']:
            suggestions.append(CommandSuggestion(
                command="/watch tests",
                reason="Monitor test runs automatically",
                confidence=0.70,
                icon="👀",
                category="monitor"
            ))

        # Recent monitor failures - suggest checking status
        if len(context['recent_monitor_failures']) > 0:
            suggestions.append(CommandSuggestion(
                command="/status",
                reason="Check monitor status and recent events",
                confidence=0.75,
                icon="📊",
                category="monitor"
            ))

        return suggestions

    def _suggest_validation_actions(self, context: Dict) -> List[CommandSuggestion]:
        """Suggest validation-related actions."""
        suggestions = []

        # Modified files but no validation yet
        if context['files_modified_count'] > 2:
            suggestions.append(CommandSuggestion(
                command="/state",
                reason="Review project state and recent changes",
                confidence=0.50,
                icon="🧠",
                category="general"
            ))

        return suggestions
