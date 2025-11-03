"""Proactive Monitor - Background watching with intelligent notifications.

Monitors tests, builds, linting, and code changes in the background.
When something breaks, immediately notifies the user with AI analysis.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class MonitorType(Enum):
    """Types of monitors."""
    TESTS = "tests"
    BUILD = "build"
    LINT = "lint"
    TYPECHECK = "typecheck"
    FILE_CHANGES = "file_changes"
    GIT = "git"


class EventSeverity(Enum):
    """Severity levels for events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MonitorEvent:
    """Event detected by monitor."""
    monitor_type: MonitorType
    severity: EventSeverity
    message: str
    details: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict:
        return {
            'monitor_type': self.monitor_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }


class BaseMonitor:
    """Base class for all monitors."""

    def __init__(self, project_path: Path, interval: int = 5):
        """Initialize monitor.

        Args:
            project_path: Root directory to monitor
            interval: Check interval in seconds
        """
        self.project_path = project_path
        self.interval = interval
        self.running = False
        self.last_state: Optional[Dict[str, Any]] = None
        self.callbacks: List[Callable[[MonitorEvent], None]] = []

    def add_callback(self, callback: Callable[[MonitorEvent], None]):
        """Add callback to be called when event occurs."""
        self.callbacks.append(callback)

    async def start(self):
        """Start monitoring."""
        self.running = True
        while self.running:
            try:
                await self._check()
            except Exception as e:
                print(f"Monitor error: {e}")

            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop monitoring."""
        self.running = False

    async def _check(self):
        """Check for changes (implemented by subclasses)."""
        raise NotImplementedError

    def _notify(self, event: MonitorEvent):
        """Notify all callbacks about an event."""
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Callback error: {e}")


class TestMonitor(BaseMonitor):
    """Monitors test status."""

    async def _check(self):
        """Check test status."""
        # Run tests silently
        import subprocess

        try:
            result = subprocess.run(
                ["pytest", "--tb=no", "-q"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            current_state = {
                'exit_code': result.returncode,
                'output': result.stdout + result.stderr
            }

            # Check if state changed
            if self.last_state and self.last_state['exit_code'] != current_state['exit_code']:
                if current_state['exit_code'] == 0 and self.last_state['exit_code'] != 0:
                    # Tests fixed!
                    self._notify(MonitorEvent(
                        monitor_type=MonitorType.TESTS,
                        severity=EventSeverity.INFO,
                        message="✅ Tests are now passing!",
                        details={'output': current_state['output']},
                        timestamp=datetime.now().isoformat()
                    ))
                elif current_state['exit_code'] != 0 and self.last_state['exit_code'] == 0:
                    # Tests broke!
                    self._notify(MonitorEvent(
                        monitor_type=MonitorType.TESTS,
                        severity=EventSeverity.ERROR,
                        message="❌ Tests are now failing!",
                        details={'output': current_state['output']},
                        timestamp=datetime.now().isoformat()
                    ))

            self.last_state = current_state

        except subprocess.TimeoutExpired:
            pass  # Tests taking too long, skip this check
        except FileNotFoundError:
            pass  # pytest not available


class BuildMonitor(BaseMonitor):
    """Monitors build status."""

    async def _check(self):
        """Check build status."""
        # This is project-specific - detect build system and run it
        build_files = {
            'package.json': ['npm', 'run', 'build'],
            'setup.py': ['python', 'setup.py', 'build'],
            'Makefile': ['make', 'build'],
            'go.mod': ['go', 'build', './...']
        }

        for file, cmd in build_files.items():
            if (self.project_path / file).exists():
                try:
                    import subprocess
                    result = subprocess.run(
                        cmd,
                        cwd=self.project_path,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    current_state = {
                        'exit_code': result.returncode,
                        'output': result.stderr
                    }

                    if self.last_state and self.last_state['exit_code'] != current_state['exit_code']:
                        if current_state['exit_code'] == 0:
                            self._notify(MonitorEvent(
                                monitor_type=MonitorType.BUILD,
                                severity=EventSeverity.INFO,
                                message="✅ Build is now succeeding!",
                                details={'output': current_state['output']},
                                timestamp=datetime.now().isoformat()
                            ))
                        else:
                            self._notify(MonitorEvent(
                                monitor_type=MonitorType.BUILD,
                                severity=EventSeverity.ERROR,
                                message="❌ Build is now failing!",
                                details={'output': current_state['output']},
                                timestamp=datetime.now().isoformat()
                            ))

                    self.last_state = current_state
                    break

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass


class LintMonitor(BaseMonitor):
    """Monitors linting status."""

    async def _check(self):
        """Check linting status."""
        linters = {
            'ruff': ['ruff', 'check', '.'],
            'pylint': ['pylint', '.'],
            'eslint': ['eslint', '.'],
            'flake8': ['flake8', '.']
        }

        for linter, cmd in linters.items():
            try:
                import subprocess
                result = subprocess.run(
                    cmd,
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Count issues
                output = result.stdout + result.stderr
                issue_count = output.count('\n')

                current_state = {
                    'exit_code': result.returncode,
                    'issue_count': issue_count,
                    'output': output
                }

                if self.last_state:
                    # Check if issues increased
                    if current_state['issue_count'] > self.last_state['issue_count']:
                        new_issues = current_state['issue_count'] - self.last_state['issue_count']
                        self._notify(MonitorEvent(
                            monitor_type=MonitorType.LINT,
                            severity=EventSeverity.WARNING,
                            message=f"⚠️  {new_issues} new lint issue{'s' if new_issues != 1 else ''}",
                            details={'output': current_state['output']},
                            timestamp=datetime.now().isoformat()
                        ))
                    # Check if issues decreased
                    elif current_state['issue_count'] < self.last_state['issue_count']:
                        fixed = self.last_state['issue_count'] - current_state['issue_count']
                        self._notify(MonitorEvent(
                            monitor_type=MonitorType.LINT,
                            severity=EventSeverity.INFO,
                            message=f"✨ Fixed {fixed} lint issue{'s' if fixed != 1 else ''}",
                            details={'output': current_state['output']},
                            timestamp=datetime.now().isoformat()
                        ))

                self.last_state = current_state
                break

            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue


class FileChangeMonitor(BaseMonitor):
    """Monitors file changes."""

    def __init__(self, project_path: Path, interval: int = 2):
        super().__init__(project_path, interval)
        self.watched_patterns = ['*.py', '*.js', '*.ts', '*.go', '*.rs']
        self.file_mtimes: Dict[str, float] = {}

    async def _check(self):
        """Check for file changes."""
        changed_files = []

        for pattern in self.watched_patterns:
            for file in self.project_path.rglob(pattern):
                if '.git' in file.parts or '__pycache__' in file.parts:
                    continue

                try:
                    mtime = file.stat().st_mtime
                    file_key = str(file.relative_to(self.project_path))

                    if file_key in self.file_mtimes:
                        if self.file_mtimes[file_key] != mtime:
                            changed_files.append(file_key)

                    self.file_mtimes[file_key] = mtime

                except (OSError, ValueError):
                    continue

        if changed_files and self.last_state is not None:
            self._notify(MonitorEvent(
                monitor_type=MonitorType.FILE_CHANGES,
                severity=EventSeverity.INFO,
                message=f"📝 {len(changed_files)} file{'s' if len(changed_files) != 1 else ''} changed",
                details={'files': changed_files},
                timestamp=datetime.now().isoformat()
            ))

        self.last_state = {'checked': True}


class GitMonitor(BaseMonitor):
    """Monitors git repository status."""

    async def _check(self):
        """Check git status."""
        try:
            import subprocess

            # Check for uncommitted changes
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            lines = [l for l in result.stdout.split('\n') if l.strip()]
            current_state = {
                'uncommitted_count': len(lines),
                'files': lines
            }

            if self.last_state:
                # Check if new uncommitted changes
                if current_state['uncommitted_count'] > self.last_state['uncommitted_count']:
                    new_changes = current_state['uncommitted_count'] - self.last_state['uncommitted_count']
                    self._notify(MonitorEvent(
                        monitor_type=MonitorType.GIT,
                        severity=EventSeverity.INFO,
                        message=f"📋 {new_changes} new uncommitted change{'s' if new_changes != 1 else ''}",
                        details={'files': current_state['files']},
                        timestamp=datetime.now().isoformat()
                    ))

            self.last_state = current_state

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass


class ProactiveMonitor:
    """Main proactive monitoring system.

    Coordinates multiple monitors and provides intelligent notifications
    with AI analysis.
    """

    def __init__(self, project_path: Path, llm_provider=None):
        """Initialize proactive monitor.

        Args:
            project_path: Root directory to monitor
            llm_provider: Optional LLM for AI analysis
        """
        self.project_path = project_path
        self.llm_provider = llm_provider
        self.monitors: Dict[MonitorType, BaseMonitor] = {}
        self.event_history: List[MonitorEvent] = []
        self.notification_callbacks: List[Callable[[str], None]] = []
        self.running = False

        # Debouncing to avoid notification spam
        self.last_notification_time: Dict[MonitorType, float] = {}
        self.notification_cooldown = 10  # seconds

    def add_notification_callback(self, callback: Callable[[str], None]):
        """Add callback for notifications.

        Args:
            callback: Function that receives notification messages
        """
        self.notification_callbacks.append(callback)

    def enable_monitor(self, monitor_type: MonitorType, interval: int = 5):
        """Enable a specific monitor.

        Args:
            monitor_type: Type of monitor to enable
            interval: Check interval in seconds
        """
        if monitor_type in self.monitors:
            return

        monitor_class = {
            MonitorType.TESTS: TestMonitor,
            MonitorType.BUILD: BuildMonitor,
            MonitorType.LINT: LintMonitor,
            MonitorType.FILE_CHANGES: FileChangeMonitor,
            MonitorType.GIT: GitMonitor
        }.get(monitor_type)

        if not monitor_class:
            return

        monitor = monitor_class(self.project_path, interval)
        monitor.add_callback(self._handle_event)
        self.monitors[monitor_type] = monitor

    def disable_monitor(self, monitor_type: MonitorType):
        """Disable a specific monitor."""
        if monitor_type in self.monitors:
            self.monitors[monitor_type].stop()
            del self.monitors[monitor_type]

    async def start(self):
        """Start all enabled monitors."""
        self.running = True
        tasks = [monitor.start() for monitor in self.monitors.values()]

        if tasks:
            await asyncio.gather(*tasks)

    def stop(self):
        """Stop all monitors."""
        self.running = False
        for monitor in self.monitors.values():
            monitor.stop()

    def _handle_event(self, event: MonitorEvent):
        """Handle event from a monitor."""
        self.event_history.append(event)

        # Check cooldown
        now = time.time()
        last_time = self.last_notification_time.get(event.monitor_type, 0)
        if now - last_time < self.notification_cooldown:
            return  # Too soon, skip notification

        self.last_notification_time[event.monitor_type] = now

        # Generate notification
        notification = self._generate_notification(event)

        # Send to callbacks
        for callback in self.notification_callbacks:
            try:
                callback(notification)
            except Exception as e:
                print(f"Notification callback error: {e}")

    def _generate_notification(self, event: MonitorEvent) -> str:
        """Generate notification message for event."""
        notification = f"\n{'='*60}\n"
        notification += f"{event.message}\n"
        notification += f"{'='*60}\n"

        # Add AI analysis if available
        if self.llm_provider and event.severity in [EventSeverity.ERROR, EventSeverity.CRITICAL]:
            analysis = self._get_ai_analysis(event)
            if analysis:
                notification += f"\n🤖 AI Analysis:\n{analysis}\n"

        # Add relevant details
        if event.monitor_type == MonitorType.TESTS:
            output = event.details.get('output', '')
            if output:
                # Extract failure info
                lines = output.split('\n')
                failures = [l for l in lines if 'FAILED' in l or 'ERROR' in l]
                if failures:
                    notification += "\nFailed tests:\n"
                    for failure in failures[:5]:  # Limit to 5
                        notification += f"  • {failure}\n"

        elif event.monitor_type == MonitorType.LINT:
            output = event.details.get('output', '')
            if output:
                lines = output.split('\n')
                issues = [l for l in lines if l.strip()][:5]
                if issues:
                    notification += "\nIssues:\n"
                    for issue in issues:
                        notification += f"  • {issue}\n"

        elif event.monitor_type == MonitorType.FILE_CHANGES:
            files = event.details.get('files', [])
            if files:
                notification += f"\nChanged files:\n"
                for file in files[:5]:
                    notification += f"  • {file}\n"

        notification += f"\n{'='*60}\n"
        return notification

    def _get_ai_analysis(self, event: MonitorEvent) -> Optional[str]:
        """Get AI analysis of the event.

        This would use the LLM to analyze what went wrong and suggest fixes.
        For now, returns a simple analysis.
        """
        # TODO: Implement actual AI analysis using LLM
        # For now, return basic analysis

        if event.monitor_type == MonitorType.TESTS:
            return ("Tests failed. Check the output above for specific failures. "
                   "Common causes: API changes, missing dependencies, data issues.")

        elif event.monitor_type == MonitorType.BUILD:
            return ("Build failed. Check for syntax errors, missing imports, "
                   "or dependency issues.")

        elif event.monitor_type == MonitorType.LINT:
            return ("New lint issues detected. Run 'flux /autofix' to automatically "
                   "fix formatting issues.")

        return None

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status.

        Returns:
            Dict with monitor statuses and recent events
        """
        return {
            'running': self.running,
            'monitors': [m.value for m in self.monitors.keys()],
            'recent_events': [e.to_dict() for e in self.event_history[-10:]],
            'total_events': len(self.event_history)
        }
