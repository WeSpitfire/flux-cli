"""Intelligent project state tracking for contextual awareness."""

import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict

from flux.core.git_utils import GitIntegration


@dataclass
class FileModification:
    """Track a single file modification."""
    path: str
    timestamp: float
    operation: str  # 'write', 'edit', 'delete', 'move'
    lines_changed: Optional[int] = None

    def __post_init__(self):
        """Convert timestamp to float if needed."""
        if isinstance(self.timestamp, datetime):
            self.timestamp = self.timestamp.timestamp()


@dataclass
class TestResult:
    """Track test execution results."""
    timestamp: float
    command: str
    passed: bool
    failures: List[str] = field(default_factory=list)
    duration_ms: Optional[float] = None

    def __post_init__(self):
        """Convert timestamp to float if needed."""
        if isinstance(self.timestamp, datetime):
            self.timestamp = self.timestamp.timestamp()


@dataclass
class CommandExecution:
    """Track command execution."""
    timestamp: float
    command: str
    exit_code: int
    output: Optional[str] = None

    def __post_init__(self):
        """Convert timestamp to float if needed."""
        if isinstance(self.timestamp, datetime):
            self.timestamp = self.timestamp.timestamp()


@dataclass
class ConversationCheckpoint:
    """Track conversation state at a point in time."""
    timestamp: float
    query: str
    response_summary: str  # First 200 chars
    files_mentioned: List[str]
    tools_used: List[str]

    def __post_init__(self):
        """Convert timestamp to float if needed."""
        if isinstance(self.timestamp, datetime):
            self.timestamp = self.timestamp.timestamp()


class ProjectStateTracker:
    """
    Intelligent project state tracker that maintains awareness of:
    - Recent file modifications and patterns
    - Git state (branch, uncommitted changes, recent commits)
    - Test results and failures
    - Command execution history
    - Conversation context and patterns
    """

    def __init__(self, cwd: Path, state_file: Optional[Path] = None):
        """Initialize state tracker.

        Args:
            cwd: Current working directory
            state_file: Optional path to persist state (default: .flux/state.json)
        """
        self.cwd = cwd
        self.state_file = state_file or (cwd / ".flux" / "state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Git integration
        self.git = GitIntegration(cwd)

        # State tracking
        self.file_modifications: List[FileModification] = []
        self.test_results: List[TestResult] = []
        self.command_history: List[CommandExecution] = []
        self.conversation_checkpoints: List[ConversationCheckpoint] = []

        # Quick lookups
        self.recently_modified_files: Set[str] = set()
        self.hot_files: Dict[str, int] = defaultdict(int)  # file -> access count
        self.last_test_failures: List[str] = []

        # Session metadata
        self.session_start = time.time()
        self.last_activity = time.time()

        # Load persisted state
        self._load_state()

    def track_file_modification(
        self,
        path: str,
        operation: str,
        lines_changed: Optional[int] = None
    ):
        """Track a file modification."""
        mod = FileModification(
            path=path,
            timestamp=time.time(),
            operation=operation,
            lines_changed=lines_changed
        )
        self.file_modifications.append(mod)
        self.recently_modified_files.add(path)
        self.hot_files[path] += 1
        self.last_activity = time.time()

        # Keep only last 100 modifications
        if len(self.file_modifications) > 100:
            self.file_modifications = self.file_modifications[-100:]

        self._persist_state()

    def track_test_result(
        self,
        command: str,
        passed: bool,
        failures: Optional[List[str]] = None,
        duration_ms: Optional[float] = None
    ):
        """Track test execution result."""
        result = TestResult(
            timestamp=time.time(),
            command=command,
            passed=passed,
            failures=failures or [],
            duration_ms=duration_ms
        )
        self.test_results.append(result)

        if not passed:
            self.last_test_failures = failures or []
        else:
            self.last_test_failures = []

        self.last_activity = time.time()

        # Keep only last 50 test results
        if len(self.test_results) > 50:
            self.test_results = self.test_results[-50:]

        self._persist_state()

    def track_command(self, command: str, exit_code: int, output: Optional[str] = None):
        """Track command execution."""
        cmd = CommandExecution(
            timestamp=time.time(),
            command=command,
            exit_code=exit_code,
            output=output[:500] if output else None  # Truncate output
        )
        self.command_history.append(cmd)
        self.last_activity = time.time()

        # Keep only last 50 commands
        if len(self.command_history) > 50:
            self.command_history = self.command_history[-50:]

        self._persist_state()

    def track_conversation(
        self,
        query: str,
        response: str,
        files_mentioned: List[str],
        tools_used: List[str]
    ):
        """Track conversation checkpoint."""
        checkpoint = ConversationCheckpoint(
            timestamp=time.time(),
            query=query[:200],  # Truncate
            response_summary=response[:200],  # Truncate
            files_mentioned=files_mentioned,
            tools_used=tools_used
        )
        self.conversation_checkpoints.append(checkpoint)
        self.last_activity = time.time()

        # Keep only last 20 checkpoints
        if len(self.conversation_checkpoints) > 20:
            self.conversation_checkpoints = self.conversation_checkpoints[-20:]

        self._persist_state()

    def get_context_summary(self, max_age_minutes: int = 30) -> Dict[str, Any]:
        """Get contextual summary of recent project state.

        Args:
            max_age_minutes: Only include activity within this time window

        Returns:
            Dict containing contextual information
        """
        cutoff = time.time() - (max_age_minutes * 60)

        # Recent file modifications
        recent_mods = [
            m for m in self.file_modifications
            if m.timestamp >= cutoff
        ]

        # Recent test results
        recent_tests = [
            t for t in self.test_results
            if t.timestamp >= cutoff
        ]

        # Recent commands
        recent_commands = [
            c for c in self.command_history
            if c.timestamp >= cutoff
        ]

        # Git state
        git_status = self.git.get_status()

        # Build summary
        summary = {
            "session_duration_minutes": (time.time() - self.session_start) / 60,
            "time_since_last_activity_seconds": time.time() - self.last_activity,

            "files": {
                "recently_modified": [m.path for m in recent_mods[-10:]],
                "most_active": sorted(
                    self.hot_files.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "total_modifications": len(recent_mods),
            },

            "git": {
                "is_repo": git_status.is_repo,
                "branch": git_status.branch,
                "has_changes": git_status.has_changes,
                "total_changes": git_status.total_changes,
                "staged_files": len(git_status.staged_files),
                "modified_files": len(git_status.modified_files),
                "untracked_files": len(git_status.untracked_files),
            },

            "tests": {
                "recent_count": len(recent_tests),
                "last_passed": recent_tests[-1].passed if recent_tests else None,
                "recent_failures": self.last_test_failures,
            },

            "commands": {
                "recent_count": len(recent_commands),
                "last_command": recent_commands[-1].command if recent_commands else None,
                "failed_commands": [
                    c.command for c in recent_commands
                    if c.exit_code != 0
                ],
            },

            "conversation": {
                "recent_checkpoints": len([
                    c for c in self.conversation_checkpoints
                    if c.timestamp >= cutoff
                ]),
                "files_discussed": list(set(
                    f for cp in self.conversation_checkpoints
                    if cp.timestamp >= cutoff
                    for f in cp.files_mentioned
                ))[:10],
            }
        }

        return summary

    def get_proactive_suggestions(self) -> List[str]:
        """Generate proactive suggestions based on current state.

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Check for uncommitted changes
        git_status = self.git.get_status()
        if git_status.has_changes and git_status.total_changes > 5:
            suggestions.append(
                f"📝 You have {git_status.total_changes} uncommitted changes. "
                "Consider committing or using /diff to review."
            )

        # Check for test failures
        if self.last_test_failures:
            suggestions.append(
                f"⚠️  {len(self.last_test_failures)} test(s) failed. "
                f"Focus on: {', '.join(self.last_test_failures[:3])}"
            )

        # Check for hot files that might need tests
        hot_files_without_tests = [
            path for path, count in self.hot_files.items()
            if count >= 3 and not any('test' in path.lower() for path in self.hot_files)
        ]
        if hot_files_without_tests:
            suggestions.append(
                f"🧪 Files modified frequently: {', '.join(hot_files_without_tests[:2])}. "
                "Consider adding/updating tests."
            )

        # Check for long-running session without commits
        session_hours = (time.time() - self.session_start) / 3600
        if session_hours > 2 and not self.git.get_status().has_changes:
            suggestions.append(
                "⏰ Long session with no uncommitted work. "
                "Great progress! Consider taking a break."
            )

        # Check for failed commands
        recent_failed = [
            c for c in self.command_history[-10:]
            if c.exit_code != 0
        ]
        if len(recent_failed) >= 3:
            suggestions.append(
                f"⚠️  Multiple failed commands detected. "
                f"Last: '{recent_failed[-1].command}'. Need help debugging?"
            )

        return suggestions

    def get_contextual_prompt_addon(self) -> str:
        """Generate contextual information to add to system prompt.

        Returns:
            String to append to system prompt with relevant context
        """
        summary = self.get_context_summary(max_age_minutes=15)

        addon_parts = []

        # Recent activity
        if summary["files"]["recently_modified"]:
            files = summary["files"]["recently_modified"][:3]
            addon_parts.append(f"Recent edits: {', '.join(files)}")

        # Git status
        if summary["git"]["has_changes"]:
            addon_parts.append(
                f"Uncommitted: {summary['git']['total_changes']} files on {summary['git']['branch']}"
            )

        # Test failures
        if summary["tests"]["recent_failures"]:
            failures = summary["tests"]["recent_failures"][:2]
            addon_parts.append(f"Failing tests: {', '.join(failures)}")

        # Failed commands
        if summary["commands"]["failed_commands"]:
            cmd = summary["commands"]["failed_commands"][-1]
            addon_parts.append(f"Last failed: {cmd}")

        if addon_parts:
            return "\n\n**Current Project State:**\n" + " | ".join(addon_parts)

        return ""

    def _load_state(self):
        """Load persisted state from disk."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            # Restore state
            self.file_modifications = [
                FileModification(**m) for m in data.get('file_modifications', [])
            ]
            self.test_results = [
                TestResult(**t) for t in data.get('test_results', [])
            ]
            self.command_history = [
                CommandExecution(**c) for c in data.get('command_history', [])
            ]
            self.conversation_checkpoints = [
                ConversationCheckpoint(**cp) for cp in data.get('conversation_checkpoints', [])
            ]

            # Rebuild lookups
            self.recently_modified_files = set(m.path for m in self.file_modifications[-20:])
            self.hot_files = defaultdict(int)
            for m in self.file_modifications:
                self.hot_files[m.path] += 1

            if self.test_results and not self.test_results[-1].passed:
                self.last_test_failures = self.test_results[-1].failures

        except Exception as e:
            print(f"Warning: Could not load state: {e}")

    def _persist_state(self):
        """Persist state to disk."""
        try:
            data = {
                'file_modifications': [asdict(m) for m in self.file_modifications],
                'test_results': [asdict(t) for t in self.test_results],
                'command_history': [asdict(c) for c in self.command_history],
                'conversation_checkpoints': [asdict(cp) for cp in self.conversation_checkpoints],
                'session_start': self.session_start,
                'last_activity': self.last_activity,
            }

            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not persist state: {e}")

    def clear_old_data(self, days: int = 7):
        """Clear data older than specified days."""
        cutoff = time.time() - (days * 24 * 60 * 60)

        self.file_modifications = [m for m in self.file_modifications if m.timestamp >= cutoff]
        self.test_results = [t for t in self.test_results if t.timestamp >= cutoff]
        self.command_history = [c for c in self.command_history if c.timestamp >= cutoff]
        self.conversation_checkpoints = [cp for cp in self.conversation_checkpoints if cp.timestamp >= cutoff]

        # Rebuild lookups
        self.recently_modified_files = set(m.path for m in self.file_modifications[-20:])
        self.hot_files = defaultdict(int)
        for m in self.file_modifications:
            self.hot_files[m.path] += 1

        self._persist_state()
