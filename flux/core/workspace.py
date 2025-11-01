"""Workspace Intelligence - Manage entire development workflow.

This module provides:
- Session management: Save/restore entire work contexts
- Task tracking: AI-powered prioritization and progress tracking
- Multi-project support: Switch between projects seamlessly
- Work summaries: Automatic summaries of accomplishments
- Time tracking: Understand where time is spent
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum


class TaskPriority(Enum):
    """Priority levels for tasks."""
    URGENT = "urgent"      # Blocking, needs immediate attention
    HIGH = "high"          # Important, should do soon
    MEDIUM = "medium"      # Normal priority
    LOW = "low"            # Nice to have
    BACKLOG = "backlog"    # Future consideration


class TaskStatus(Enum):
    """Status of a task."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A development task."""
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    notes: List[str] = field(default_factory=list)


@dataclass
class WorkSession:
    """A work session capturing complete context."""
    id: str
    name: str
    project_path: str
    created_at: float
    updated_at: float
    
    # Context
    current_task_id: Optional[str] = None
    open_files: List[str] = field(default_factory=list)
    recent_commands: List[str] = field(default_factory=list)
    active_branch: Optional[str] = None
    
    # State
    workflow_state: Dict = field(default_factory=dict)
    suggestions_context: Dict = field(default_factory=dict)
    memory_state: Dict = field(default_factory=dict)
    
    # Metrics
    time_spent_seconds: float = 0.0
    files_modified: List[str] = field(default_factory=list)
    commands_run: int = 0
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkSummary:
    """Summary of work done in a session."""
    session_id: str
    session_name: str
    start_time: float
    end_time: float
    duration_minutes: float
    
    # Accomplishments
    tasks_completed: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    commands_executed: int = 0
    
    # Activity breakdown
    time_by_activity: Dict[str, float] = field(default_factory=dict)  # activity -> minutes
    most_active_files: List[tuple] = field(default_factory=list)  # [(file, edit_count)]
    
    # AI-generated summary
    summary_text: str = ""
    key_achievements: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)


class Workspace:
    """Manages development workspace with sessions and tasks."""
    
    def __init__(self, workspace_dir: Path, project_path: Path):
        """Initialize workspace manager.
        
        Args:
            workspace_dir: Directory to store workspace data (.flux/workspace/)
            project_path: Current project root path
        """
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.project_path = project_path
        
        # Data storage
        self.sessions_file = workspace_dir / "sessions.json"
        self.tasks_file = workspace_dir / "tasks.json"
        self.active_session_file = workspace_dir / "active_session.json"
        
        # Load data
        self.sessions: Dict[str, WorkSession] = self._load_sessions()
        self.tasks: Dict[str, Task] = self._load_tasks()
        self.active_session: Optional[WorkSession] = self._load_active_session()
        
        # Tracking
        self.session_start_time: Optional[float] = None
        if self.active_session:
            self.session_start_time = time.time()
    
    # Session Management
    
    def create_session(self, name: str, description: str = "") -> WorkSession:
        """Create a new work session."""
        session_id = f"session_{int(time.time())}_{len(self.sessions)}"
        
        session = WorkSession(
            id=session_id,
            name=name,
            project_path=str(self.project_path),
            created_at=time.time(),
            updated_at=time.time(),
            description=description
        )
        
        self.sessions[session_id] = session
        self._save_sessions()
        
        return session
    
    def save_session(self, name: str, description: str = "") -> WorkSession:
        """Save current context as a session."""
        if self.active_session:
            # Update existing session
            self.active_session.name = name
            self.active_session.description = description
            self.active_session.updated_at = time.time()
            
            # Calculate time spent
            if self.session_start_time:
                self.active_session.time_spent_seconds += (time.time() - self.session_start_time)
                self.session_start_time = time.time()
            
            session = self.active_session
        else:
            # Create new session
            session = self.create_session(name, description)
            self.active_session = session
            self.session_start_time = time.time()
        
        self._save_active_session()
        self._save_sessions()
        
        return session
    
    def restore_session(self, session_id: str) -> Optional[WorkSession]:
        """Restore a saved session."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        self.active_session = session
        self.session_start_time = time.time()
        
        self._save_active_session()
        
        return session
    
    def end_session(self) -> Optional[WorkSummary]:
        """End the current session and generate summary."""
        if not self.active_session:
            return None
        
        # Calculate final time
        if self.session_start_time:
            self.active_session.time_spent_seconds += (time.time() - self.session_start_time)
        
        # Generate summary
        summary = self._generate_summary(self.active_session)
        
        # Save and clear
        self._save_sessions()
        self.active_session = None
        self.session_start_time = None
        
        if self.active_session_file.exists():
            self.active_session_file.unlink()
        
        return summary
    
    def list_sessions(self, limit: int = 10) -> List[WorkSession]:
        """List recent sessions."""
        sorted_sessions = sorted(
            self.sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
        return sorted_sessions[:limit]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            return True
        return False
    
    # Task Management
    
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        estimated_minutes: Optional[int] = None,
        tags: List[str] = None,
        related_files: List[str] = None
    ) -> Task:
        """Create a new task."""
        task_id = f"task_{int(time.time())}_{len(self.tasks)}"
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            status=TaskStatus.TODO,
            created_at=time.time(),
            updated_at=time.time(),
            estimated_minutes=estimated_minutes,
            tags=tags or [],
            related_files=related_files or []
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        return task
    
    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update a task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = time.time()
        
        # If completing task
        if kwargs.get('status') == TaskStatus.DONE and not task.completed_at:
            task.completed_at = time.time()
        
        self._save_tasks()
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Task]:
        """List tasks with optional filters."""
        tasks = list(self.tasks.values())
        
        # Apply filters
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]
        
        # Sort by priority and creation time
        priority_order = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
            TaskPriority.BACKLOG: 4
        }
        
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 5), -t.created_at))
        
        return tasks[:limit]
    
    def suggest_next_task(self) -> Optional[Task]:
        """AI-powered suggestion for next task to work on."""
        # Get incomplete tasks
        incomplete = [
            t for t in self.tasks.values()
            if t.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]
        ]
        
        if not incomplete:
            return None
        
        # Score tasks based on multiple factors
        def score_task(task: Task) -> float:
            score = 0.0
            
            # Priority weight
            priority_weight = {
                TaskPriority.URGENT: 10.0,
                TaskPriority.HIGH: 5.0,
                TaskPriority.MEDIUM: 2.0,
                TaskPriority.LOW: 1.0,
                TaskPriority.BACKLOG: 0.5
            }
            score += priority_weight.get(task.priority, 1.0)
            
            # Already in progress
            if task.status == TaskStatus.IN_PROGRESS:
                score += 3.0
            
            # Age factor (older tasks get slight boost)
            age_days = (time.time() - task.created_at) / 86400
            score += min(age_days * 0.1, 2.0)
            
            # Has no dependencies (can start immediately)
            if not task.dependencies:
                score += 1.0
            
            return score
        
        # Find highest scoring task
        best_task = max(incomplete, key=score_task)
        return best_task
    
    def set_current_task(self, task_id: str):
        """Set the current task for the active session."""
        if self.active_session and task_id in self.tasks:
            self.active_session.current_task_id = task_id
            
            # Mark task as in progress
            task = self.tasks[task_id]
            if task.status == TaskStatus.TODO:
                task.status = TaskStatus.IN_PROGRESS
                task.updated_at = time.time()
                self._save_tasks()
            
            self._save_active_session()
    
    def complete_task(self, task_id: str):
        """Mark a task as complete."""
        self.update_task(task_id, status=TaskStatus.DONE)
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False
    
    # Work Summary
    
    def _generate_summary(self, session: WorkSession) -> WorkSummary:
        """Generate a summary of work done in a session."""
        duration_minutes = session.time_spent_seconds / 60
        
        # Get completed tasks in this session
        completed_tasks = [
            t.title for t in self.tasks.values()
            if t.status == TaskStatus.DONE and
            t.completed_at and t.completed_at >= session.created_at
        ]
        
        summary = WorkSummary(
            session_id=session.id,
            session_name=session.name,
            start_time=session.created_at,
            end_time=time.time(),
            duration_minutes=duration_minutes,
            tasks_completed=completed_tasks,
            files_modified=session.files_modified,
            commands_executed=session.commands_run
        )
        
        # Generate AI summary text
        summary.summary_text = self._generate_summary_text(session, summary)
        
        # Generate key achievements
        if completed_tasks:
            summary.key_achievements = [f"✓ {task}" for task in completed_tasks[:5]]
        
        # Suggest next steps
        next_task = self.suggest_next_task()
        if next_task:
            summary.next_steps = [f"Continue with: {next_task.title}"]
        
        return summary
    
    def _generate_summary_text(self, session: WorkSession, summary: WorkSummary) -> str:
        """Generate human-readable summary text."""
        duration_str = f"{int(summary.duration_minutes)} minutes"
        if summary.duration_minutes >= 60:
            hours = summary.duration_minutes / 60
            duration_str = f"{hours:.1f} hours"
        
        parts = [
            f"Session: {session.name}",
            f"Duration: {duration_str}",
        ]
        
        if summary.tasks_completed:
            parts.append(f"Completed {len(summary.tasks_completed)} task(s)")
        
        if summary.files_modified:
            parts.append(f"Modified {len(summary.files_modified)} file(s)")
        
        if summary.commands_executed:
            parts.append(f"Ran {summary.commands_executed} command(s)")
        
        return " | ".join(parts)
    
    def get_daily_summary(self) -> Dict:
        """Get summary of today's work across all sessions."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        
        # Find today's sessions
        today_sessions = [
            s for s in self.sessions.values()
            if s.updated_at >= today_start
        ]
        
        # Aggregate stats
        total_time = sum(s.time_spent_seconds for s in today_sessions)
        all_files = set()
        for s in today_sessions:
            all_files.update(s.files_modified)
        
        completed_today = [
            t for t in self.tasks.values()
            if t.completed_at and t.completed_at >= today_start
        ]
        
        return {
            'sessions': len(today_sessions),
            'total_minutes': total_time / 60,
            'files_modified': len(all_files),
            'tasks_completed': len(completed_today),
            'completed_task_titles': [t.title for t in completed_today]
        }
    
    # Context Tracking
    
    def track_file_access(self, file_path: str):
        """Track that a file was accessed."""
        if self.active_session:
            if file_path not in self.active_session.open_files:
                self.active_session.open_files.append(file_path)
            
            if file_path not in self.active_session.files_modified:
                self.active_session.files_modified.append(file_path)
            
            self._save_active_session()
    
    def track_command(self, command: str):
        """Track that a command was run."""
        if self.active_session:
            self.active_session.recent_commands.append(command)
            self.active_session.recent_commands = self.active_session.recent_commands[-20:]  # Keep last 20
            self.active_session.commands_run += 1
            self._save_active_session()
    
    # Persistence
    
    def _load_sessions(self) -> Dict[str, WorkSession]:
        """Load sessions from disk."""
        if not self.sessions_file.exists():
            return {}
        
        try:
            with open(self.sessions_file, 'r') as f:
                data = json.load(f)
                return {
                    sid: WorkSession(**sdata)
                    for sid, sdata in data.items()
                }
        except Exception:
            return {}
    
    def _save_sessions(self):
        """Save sessions to disk."""
        data = {
            sid: asdict(session)
            for sid, session in self.sessions.items()
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_tasks(self) -> Dict[str, Task]:
        """Load tasks from disk."""
        if not self.tasks_file.exists():
            return {}
        
        try:
            with open(self.tasks_file, 'r') as f:
                data = json.load(f)
                return {
                    tid: Task(
                        **{**tdata, 
                           'priority': TaskPriority(tdata['priority']),
                           'status': TaskStatus(tdata['status'])}
                    )
                    for tid, tdata in data.items()
                }
        except Exception:
            return {}
    
    def _save_tasks(self):
        """Save tasks to disk."""
        data = {}
        for tid, task in self.tasks.items():
            task_dict = asdict(task)
            task_dict['priority'] = task.priority.value
            task_dict['status'] = task.status.value
            data[tid] = task_dict
        
        with open(self.tasks_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_active_session(self) -> Optional[WorkSession]:
        """Load the active session."""
        if not self.active_session_file.exists():
            return None
        
        try:
            with open(self.active_session_file, 'r') as f:
                data = json.load(f)
                return WorkSession(**data)
        except Exception:
            return None
    
    def _save_active_session(self):
        """Save the active session."""
        if not self.active_session:
            return
        
        with open(self.active_session_file, 'w') as f:
            json.dump(asdict(self.active_session), f, indent=2)


def create_workspace(workspace_dir: Path, project_path: Path) -> Workspace:
    """Create a workspace manager instance."""
    return Workspace(workspace_dir, project_path)
