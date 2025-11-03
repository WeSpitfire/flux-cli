"""Session Manager - Persistent context across Flux sessions.

Saves and restores complete session state so users can resume where they left off.
Tracks conversation history, file changes, test results, errors, and active tasks.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(Enum):
    """Types of events to track in session."""
    MESSAGE = "message"
    FILE_EDIT = "file_edit"
    TEST_RUN = "test_run"
    ERROR = "error"
    COMMAND = "command"
    WORKFLOW = "workflow"
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"


@dataclass
class SessionEvent:
    """Single event in a session."""
    timestamp: str
    event_type: EventType
    data: Dict[str, Any]

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type.value,
            'data': self.data
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionEvent':
        return cls(
            timestamp=data['timestamp'],
            event_type=EventType(data['event_type']),
            data=data['data']
        )


@dataclass
class Session:
    """Complete session state."""
    session_id: str
    project_path: str
    start_time: str
    last_active: str
    events: List[SessionEvent]
    active_files: List[str]
    current_task: Optional[str]
    test_status: Dict[str, Any]
    error_history: List[Dict[str, Any]]

    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'project_path': self.project_path,
            'start_time': self.start_time,
            'last_active': self.last_active,
            'events': [e.to_dict() for e in self.events],
            'active_files': self.active_files,
            'current_task': self.current_task,
            'test_status': self.test_status,
            'error_history': self.error_history
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        return cls(
            session_id=data['session_id'],
            project_path=data['project_path'],
            start_time=data['start_time'],
            last_active=data['last_active'],
            events=[SessionEvent.from_dict(e) for e in data['events']],
            active_files=data['active_files'],
            current_task=data.get('current_task'),
            test_status=data.get('test_status', {}),
            error_history=data.get('error_history', [])
        )


class SessionManager:
    """Manages session persistence and restoration.

    Features:
    - Saves session state continuously
    - Restores last session on startup
    - Tracks conversation history
    - Remembers files being worked on
    - Stores test results and errors
    - Provides context for AI
    """

    def __init__(self, project_path: Path):
        """Initialize session manager.

        Args:
            project_path: Root directory of current project
        """
        self.project_path = project_path
        self.flux_dir = project_path / ".flux"
        self.flux_dir.mkdir(exist_ok=True)

        self.db_path = self.flux_dir / "sessions.db"
        self.current_session: Optional[Session] = None

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for sessions."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                project_path TEXT NOT NULL,
                start_time TEXT NOT NULL,
                last_active TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)

        # Events table for efficient querying
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_last_active
            ON sessions(last_active DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session
            ON events(session_id, timestamp DESC)
        """)

        conn.commit()
        conn.close()

    def start_new_session(self) -> Session:
        """Start a new session.

        Returns:
            New Session object
        """
        now = datetime.now().isoformat()
        session = Session(
            session_id=f"session_{int(datetime.now().timestamp())}",
            project_path=str(self.project_path),
            start_time=now,
            last_active=now,
            events=[],
            active_files=[],
            current_task=None,
            test_status={},
            error_history=[]
        )

        self.current_session = session
        self._save_session(session)

        return session

    def load_last_session(self) -> Optional[Session]:
        """Load the most recent session for this project.

        Returns:
            Last Session or None if no previous session exists
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, project_path, start_time, last_active, data
            FROM sessions
            WHERE project_path = ?
            ORDER BY last_active DESC
            LIMIT 1
        """, (str(self.project_path),))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        session_data = json.loads(row[4])
        session = Session.from_dict(session_data)

        self.current_session = session
        return session

    def get_session_summary(self, session: Session) -> str:
        """Generate human-readable session summary.

        Args:
            session: Session to summarize

        Returns:
            Formatted summary string
        """
        time_ago = self._time_ago(session.last_active)

        summary = f"📂 Resuming session from {time_ago}\n\n"

        # Current task
        if session.current_task:
            summary += f"🎯 Last task: {session.current_task}\n"

        # Active files
        if session.active_files:
            summary += f"📝 Working on: {', '.join(session.active_files[:3])}"
            if len(session.active_files) > 3:
                summary += f" (+{len(session.active_files) - 3} more)"
            summary += "\n"

        # Test status
        if session.test_status:
            if session.test_status.get('failed', 0) > 0:
                summary += f"❌ Tests: {session.test_status['failed']} failing\n"
            else:
                summary += f"✅ Tests: All passing\n"

        # Recent errors
        if session.error_history:
            recent_errors = session.error_history[-3:]
            summary += f"\n⚠️  Recent errors:\n"
            for error in recent_errors:
                summary += f"  • {error.get('message', 'Unknown error')}\n"

        # Recent activity
        recent_events = [e for e in session.events[-5:]
                        if e.event_type != EventType.MESSAGE]
        if recent_events:
            summary += f"\n📋 Recent activity:\n"
            for event in recent_events:
                summary += f"  • {event.event_type.value}: {self._format_event(event)}\n"

        return summary

    def _format_event(self, event: SessionEvent) -> str:
        """Format event for display."""
        if event.event_type == EventType.FILE_EDIT:
            return event.data.get('file', 'unknown file')
        elif event.event_type == EventType.TEST_RUN:
            total = event.data.get('total', 0)
            failed = event.data.get('failed', 0)
            return f"{total} tests, {failed} failed"
        elif event.event_type == EventType.COMMAND:
            return event.data.get('command', 'unknown')
        elif event.event_type == EventType.WORKFLOW:
            return event.data.get('name', 'unknown workflow')
        return str(event.data)

    def _time_ago(self, timestamp: str) -> str:
        """Convert timestamp to human-readable time ago."""
        then = datetime.fromisoformat(timestamp)
        now = datetime.now()
        delta = now - then

        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "just now"

    def record_event(self, event_type: EventType, data: Dict[str, Any]):
        """Record an event in current session.

        Args:
            event_type: Type of event
            data: Event data
        """
        if not self.current_session:
            return

        event = SessionEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            data=data
        )

        self.current_session.events.append(event)
        self.current_session.last_active = event.timestamp

        # Save to database
        self._save_event(event)
        self._save_session(self.current_session)

    def update_active_files(self, files: List[str]):
        """Update list of files being worked on.

        Args:
            files: List of file paths
        """
        if not self.current_session:
            return

        self.current_session.active_files = files
        self._save_session(self.current_session)

    def update_test_status(self, status: Dict[str, Any]):
        """Update test status.

        Args:
            status: Test results (total, passed, failed, etc.)
        """
        if not self.current_session:
            return

        self.current_session.test_status = status
        self.record_event(EventType.TEST_RUN, status)

    def record_error(self, error: Dict[str, Any]):
        """Record an error.

        Args:
            error: Error details (message, file, line, etc.)
        """
        if not self.current_session:
            return

        self.current_session.error_history.append({
            **error,
            'timestamp': datetime.now().isoformat()
        })
        self.record_event(EventType.ERROR, error)

    def set_current_task(self, task: Optional[str]):
        """Set the current task being worked on.

        Args:
            task: Task description or None to clear
        """
        if not self.current_session:
            return

        self.current_session.current_task = task

        if task:
            self.record_event(EventType.TASK_START, {'task': task})
        else:
            self.record_event(EventType.TASK_COMPLETE, {})

        self._save_session(self.current_session)

    def get_context_for_ai(self) -> Dict[str, Any]:
        """Get session context formatted for AI.

        Returns:
            Dict with relevant context for AI to understand current state
        """
        if not self.current_session:
            return {}

        # Get last 20 events for context
        recent_events = self.current_session.events[-20:]

        # Summarize conversation
        messages = [e for e in recent_events if e.event_type == EventType.MESSAGE]

        # Summarize file changes
        file_edits = [e for e in recent_events if e.event_type == EventType.FILE_EDIT]
        files_modified = list(set(e.data.get('file') for e in file_edits if e.data.get('file')))

        return {
            'session_id': self.current_session.session_id,
            'current_task': self.current_session.current_task,
            'active_files': self.current_session.active_files,
            'files_modified_recently': files_modified,
            'test_status': self.current_session.test_status,
            'recent_errors': self.current_session.error_history[-5:],
            'recent_activity': [
                {
                    'type': e.event_type.value,
                    'timestamp': e.timestamp,
                    'summary': self._format_event(e)
                }
                for e in recent_events[-10:]
            ]
        }

    def _save_session(self, session: Session):
        """Save session to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO sessions
            (session_id, project_path, start_time, last_active, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.project_path,
            session.start_time,
            session.last_active,
            json.dumps(session.to_dict())
        ))

        conn.commit()
        conn.close()

    def _save_event(self, event: SessionEvent):
        """Save individual event to database."""
        if not self.current_session:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO events (session_id, timestamp, event_type, data)
            VALUES (?, ?, ?, ?)
        """, (
            self.current_session.session_id,
            event.timestamp,
            event.event_type.value,
            json.dumps(event.data)
        ))

        conn.commit()
        conn.close()

    def clear_old_sessions(self, days: int = 30):
        """Delete sessions older than specified days.

        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now().timestamp() - (days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get session IDs to delete
        cursor.execute("""
            SELECT session_id FROM sessions WHERE last_active < ?
        """, (cutoff_iso,))

        session_ids = [row[0] for row in cursor.fetchall()]

        if session_ids:
            # Delete events
            placeholders = ','.join('?' * len(session_ids))
            cursor.execute(f"""
                DELETE FROM events WHERE session_id IN ({placeholders})
            """, session_ids)

            # Delete sessions
            cursor.execute(f"""
                DELETE FROM sessions WHERE session_id IN ({placeholders})
            """, session_ids)

        conn.commit()
        conn.close()

        return len(session_ids)
