"""Flux Copilot - Proactive project monitoring and intelligent suggestions."""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class SuggestionPriority(Enum):
    """Priority levels for copilot suggestions."""
    CRITICAL = "critical"  # Requires immediate attention
    HIGH = "high"          # Important but not urgent
    MEDIUM = "medium"      # Helpful optimization
    LOW = "low"            # Nice to have


class SuggestionType(Enum):
    """Types of copilot suggestions."""
    TEST_FAILURE = "test_failure"
    GIT_SYNC = "git_sync"
    CODE_SMELL = "code_smell"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BEST_PRACTICE = "best_practice"
    DEPENDENCY = "dependency"
    ERROR_DETECTED = "error_detected"


@dataclass
class CopilotSuggestion:
    """A proactive suggestion from Flux Copilot."""
    type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    action_prompt: str  # What Flux can do
    auto_fixable: bool  # Can Flux fix this automatically?
    context: Dict  # Additional context data
    timestamp: float
    id: str = ""  # Unique identifier
    
    def __post_init__(self):
        """Generate ID after initialization."""
        if not self.id:
            import hashlib
            content = f"{self.type.value}:{self.title}:{self.timestamp}"
            self.id = hashlib.md5(content.encode()).hexdigest()
    
    def __str__(self):
        priority_emoji = {
            SuggestionPriority.CRITICAL: "🚨",
            SuggestionPriority.HIGH: "⚠️",
            SuggestionPriority.MEDIUM: "💡",
            SuggestionPriority.LOW: "ℹ️"
        }
        emoji = priority_emoji.get(self.priority, "•")
        return f"{emoji} {self.title}"


class CopilotEngine:
    """Proactive monitoring engine that watches project and suggests actions."""
    
    def __init__(self, cwd: Path, state_tracker, git, test_runner, llm):
        """Initialize Copilot Engine.
        
        Args:
            cwd: Current working directory
            state_tracker: Project state tracker
            git: Git integration
            test_runner: Test runner
            llm: LLM provider for intelligent analysis
        """
        self.cwd = cwd
        self.state_tracker = state_tracker
        self.git = git
        self.test_runner = test_runner
        self.llm = llm
        
        # Monitoring state
        self.enabled = True
        self.monitoring = False
        self.check_interval = 30  # Check every 30 seconds
        
        # Suggestion state
        self.suggestions: List[CopilotSuggestion] = []
        self.dismissed_suggestions: set = set()
        self.suggestion_callbacks: List[Callable] = []
        
        # Last check timestamps
        self.last_checks = {
            'git': 0,
            'tests': 0,
            'code_quality': 0,
            'dependencies': 0
        }
        
    def add_callback(self, callback: Callable):
        """Add callback to be notified of new suggestions."""
        self.suggestion_callbacks.append(callback)
    
    def add_notification_callback(self, callback: Callable):
        """Add notification callback (alias for add_callback)."""
        self.add_callback(callback)
        
    def get_suggestions(self, priority: Optional[SuggestionPriority] = None) -> List[CopilotSuggestion]:
        """Get current suggestions, optionally filtered by priority."""
        if priority:
            return [s for s in self.suggestions if s.priority == priority]
        return self.suggestions
    
    def dismiss_suggestion(self, suggestion_id: str) -> bool:
        """Dismiss a suggestion by ID.
        
        Args:
            suggestion_id: ID of suggestion to dismiss
            
        Returns:
            True if dismissed, False if not found
        """
        for suggestion in self.suggestions:
            if suggestion.id.startswith(suggestion_id):  # Allow partial ID match
                self.suggestions.remove(suggestion)
                self.dismissed_suggestions.add(f"{suggestion.type}:{suggestion.title}")
                return True
        return False
        
    async def start_monitoring(self):
        """Start background monitoring loop."""
        if self.monitoring:
            return
            
        self.monitoring = True
        
        # Run monitoring loop in background
        asyncio.create_task(self._monitoring_loop())
        
    async def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitoring = False
        
    async def _monitoring_loop(self):
        """Main monitoring loop - runs continuously in background."""
        while self.monitoring:
            try:
                await self._run_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                # Log but don't crash
                print(f"[Copilot] Monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _run_checks(self):
        """Run all monitoring checks."""
        current_time = time.time()
        
        # Check git status (every 30s)
        if current_time - self.last_checks['git'] > 30:
            await self._check_git_status()
            self.last_checks['git'] = current_time
            
        # Check test status (every 60s)
        if current_time - self.last_checks['tests'] > 60:
            await self._check_test_status()
            self.last_checks['tests'] = current_time
            
        # Check code quality (every 120s)
        if current_time - self.last_checks['code_quality'] > 120:
            await self._check_code_quality()
            self.last_checks['code_quality'] = current_time
            
    async def _check_git_status(self):
        """Check git status and suggest actions."""
        status = self.git.get_status()
        
        if not status.is_repo:
            return
            
        # Check if behind remote
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD..@{u}'],
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=5
            )
            if result.returncode == 0:
                behind_count = int(result.stdout.strip())
                if behind_count > 0:
                    suggestion = CopilotSuggestion(
                        type=SuggestionType.GIT_SYNC,
                        priority=SuggestionPriority.MEDIUM if behind_count < 10 else SuggestionPriority.HIGH,
                        title=f"Branch is {behind_count} commits behind remote",
                        description=f"Your {status.branch} branch is {behind_count} commits behind the remote. You might want to pull or rebase.",
                        action_prompt=f"Pull {behind_count} commits from remote",
                        auto_fixable=True,
                        context={'behind_count': behind_count, 'branch': status.branch},
                        timestamp=time.time()
                    )
                    self._add_suggestion(suggestion)
        except Exception:
            pass
            
        # Check for uncommitted changes
        if status.has_changes:
            total_changes = len(status.modified_files) + len(status.untracked_files)
            if total_changes > 10:
                suggestion = CopilotSuggestion(
                    type=SuggestionType.GIT_SYNC,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"{total_changes} uncommitted changes",
                    description=f"You have {total_changes} uncommitted files. Consider committing your work.",
                    action_prompt="Create a smart commit with all changes",
                    auto_fixable=True,
                    context={'change_count': total_changes},
                    timestamp=time.time()
                )
                self._add_suggestion(suggestion)
                
    async def _check_test_status(self):
        """Check test status and suggest actions."""
        # Check if there are recent test failures
        summary = self.state_tracker.get_context_summary(max_age_minutes=30)
        
        if summary['tests']['recent_count'] > 0:
            if summary['tests']['last_passed'] is False:
                failures = summary['tests']['recent_failures']
                if failures:
                    suggestion = CopilotSuggestion(
                        type=SuggestionType.TEST_FAILURE,
                        priority=SuggestionPriority.HIGH,
                        title=f"{len(failures)} failing tests detected",
                        description=f"Tests are failing: {', '.join(failures[:3])}{'...' if len(failures) > 3 else ''}",
                        action_prompt="Investigate and fix failing tests",
                        auto_fixable=True,
                        context={'failures': failures},
                        timestamp=time.time()
                    )
                    self._add_suggestion(suggestion)
                    
    async def _check_code_quality(self):
        """Check code quality and suggest improvements."""
        # Check for recently modified files
        summary = self.state_tracker.get_context_summary(max_age_minutes=60)
        
        for file_path in summary['files']['recently_modified'][:5]:
            full_path = self.cwd / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                # Check for large functions (simple heuristic)
                in_function = False
                function_start = 0
                function_name = ""
                
                for i, line in enumerate(lines):
                    # Simple Python function detection
                    if line.strip().startswith('def ') or line.strip().startswith('async def '):
                        if in_function and i - function_start > 50:
                            # Function is too long
                            suggestion = CopilotSuggestion(
                                type=SuggestionType.CODE_SMELL,
                                priority=SuggestionPriority.MEDIUM,
                                title=f"Large function detected: {function_name}",
                                description=f"Function '{function_name}' in {file_path} is {i - function_start} lines long. Consider refactoring.",
                                action_prompt=f"Refactor {function_name} into smaller functions",
                                auto_fixable=True,
                                context={'file': file_path, 'function': function_name, 'lines': i - function_start},
                                timestamp=time.time()
                            )
                            self._add_suggestion(suggestion)
                            
                        in_function = True
                        function_start = i
                        function_name = line.strip().split('(')[0].replace('def ', '').replace('async ', '').strip()
                        
            except Exception:
                pass
                
    def _add_suggestion(self, suggestion: CopilotSuggestion):
        """Add a new suggestion if not already present or dismissed."""
        key = f"{suggestion.type}:{suggestion.title}"
        
        # Don't add if dismissed
        if key in self.dismissed_suggestions:
            return
            
        # Don't add duplicates
        for existing in self.suggestions:
            if existing.type == suggestion.type and existing.title == suggestion.title:
                return
                
        # Add suggestion
        self.suggestions.append(suggestion)
        
        # Notify callbacks
        for callback in self.suggestion_callbacks:
            try:
                callback(suggestion)
            except Exception:
                pass
                
    def get_summary(self) -> Dict:
        """Get copilot summary statistics."""
        return {
            'enabled': self.enabled,
            'monitoring': self.monitoring,
            'total_suggestions': len(self.suggestions),
            'by_priority': {
                'critical': len([s for s in self.suggestions if s.priority == SuggestionPriority.CRITICAL]),
                'high': len([s for s in self.suggestions if s.priority == SuggestionPriority.HIGH]),
                'medium': len([s for s in self.suggestions if s.priority == SuggestionPriority.MEDIUM]),
                'low': len([s for s in self.suggestions if s.priority == SuggestionPriority.LOW])
            },
            'dismissed_count': len(self.dismissed_suggestions)
        }
    
    def get_stats(self) -> Dict:
        """Get detailed copilot statistics.
        
        Returns:
            Dictionary with monitoring status and check timestamps
        """
        from datetime import datetime
        
        def format_time(timestamp):
            if timestamp == 0:
                return None
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%H:%M:%S")
        
        return {
            'monitoring': self.monitoring,
            'suggestion_count': len(self.suggestions),
            'total_generated': len(self.suggestions) + len(self.dismissed_suggestions),
            'dismissed_count': len(self.dismissed_suggestions),
            'last_git_check': format_time(self.last_checks['git']),
            'last_test_check': format_time(self.last_checks['tests']),
            'last_quality_check': format_time(self.last_checks['code_quality'])
        }
