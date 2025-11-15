"""Todo Manager - Intelligent task tracking for Flux.

Provides Warp-style todo management that:
1. Automatically tracks tasks from complex queries
2. Breaks down tasks into actionable todos
3. Tracks progress and completion
4. Persists across sessions
5. Provides clear visual feedback
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class TodoStatus(Enum):
    """Status of a todo item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TodoPriority(Enum):
    """Priority level for todos."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TodoItem:
    """A single todo item."""
    id: str
    title: str
    description: str
    status: TodoStatus = TodoStatus.PENDING
    priority: TodoPriority = TodoPriority.MEDIUM
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    parent_id: Optional[str] = None  # For subtasks
    related_files: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    def mark_completed(self):
        """Mark todo as completed."""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
    
    def mark_in_progress(self):
        """Mark todo as in progress."""
        self.status = TodoStatus.IN_PROGRESS
    
    def mark_failed(self, reason: str):
        """Mark todo as failed."""
        self.status = TodoStatus.FAILED
        self.notes.append(f"Failed: {reason}")
    
    def add_note(self, note: str):
        """Add a note to the todo."""
        self.notes.append(f"{datetime.now().strftime('%H:%M')}: {note}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'parent_id': self.parent_id,
            'related_files': self.related_files,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            status=TodoStatus(data.get('status', 'pending')),
            priority=TodoPriority(data.get('priority', 2)),
            created_at=data.get('created_at', datetime.now().isoformat()),
            completed_at=data.get('completed_at'),
            parent_id=data.get('parent_id'),
            related_files=data.get('related_files', []),
            notes=data.get('notes', [])
        )


@dataclass
class TodoList:
    """A collection of related todos (e.g., for a specific goal/task)."""
    id: str
    goal: str
    todos: List[TodoItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def add_todo(self, todo: TodoItem):
        """Add a todo to the list."""
        self.todos.append(todo)
    
    def get_todo(self, todo_id: str) -> Optional[TodoItem]:
        """Get a specific todo by ID."""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None
    
    def get_pending_todos(self) -> List[TodoItem]:
        """Get all pending todos."""
        return [t for t in self.todos if t.status == TodoStatus.PENDING]
    
    def get_completed_todos(self) -> List[TodoItem]:
        """Get all completed todos."""
        return [t for t in self.todos if t.status == TodoStatus.COMPLETED]
    
    def get_progress(self) -> Dict[str, Any]:
        """Get progress statistics."""
        total = len(self.todos)
        if total == 0:
            return {'completed': 0, 'pending': 0, 'percentage': 0}
        
        completed = len([t for t in self.todos if t.status == TodoStatus.COMPLETED])
        pending = len([t for t in self.todos if t.status == TodoStatus.PENDING])
        in_progress = len([t for t in self.todos if t.status == TodoStatus.IN_PROGRESS])
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'in_progress': in_progress,
            'percentage': int((completed / total) * 100)
        }
    
    def is_complete(self) -> bool:
        """Check if all todos are completed."""
        return all(t.status == TodoStatus.COMPLETED for t in self.todos)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'goal': self.goal,
            'todos': [t.to_dict() for t in self.todos],
            'created_at': self.created_at,
            'completed_at': self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoList':
        """Create from dictionary."""
        todo_list = cls(
            id=data['id'],
            goal=data['goal'],
            created_at=data.get('created_at', datetime.now().isoformat()),
            completed_at=data.get('completed_at')
        )
        todo_list.todos = [TodoItem.from_dict(t) for t in data.get('todos', [])]
        return todo_list


class TodoManager:
    """
    Manages todos for Flux sessions.
    
    Key features:
    - Automatic todo creation from task plans
    - Hierarchical todos (tasks -> subtasks)
    - Progress tracking
    - Session persistence
    - Smart status updates based on tool execution
    """
    
    def __init__(self, state_path: Optional[Path] = None):
        """Initialize todo manager.
        
        Args:
            state_path: Path to store todo state (default: ~/.flux/todos.json)
        """
        self.state_path = state_path or Path.home() / ".flux" / "todos.json"
        self.current_list: Optional[TodoList] = None
        self.todo_lists: List[TodoList] = []
        self._load_state()
    
    def create_todo_list_from_query(self, query: str) -> TodoList:
        """Create a new todo list from a user query.
        
        Args:
            query: User's query/goal
            
        Returns:
            New TodoList
        """
        import uuid
        list_id = str(uuid.uuid4())[:8]
        
        todo_list = TodoList(
            id=list_id,
            goal=query
        )
        
        self.todo_lists.append(todo_list)
        self.current_list = todo_list
        self._save_state()
        
        return todo_list
    
    def create_todo_list_from_plan(self, plan: 'TaskPlan') -> TodoList:
        """Create a todo list from a TaskPlan.
        
        Args:
            plan: TaskPlan from TaskPlanner
            
        Returns:
            TodoList with todos for each step
        """
        import uuid
        list_id = str(uuid.uuid4())[:8]
        
        todo_list = TodoList(
            id=list_id,
            goal=plan.goal
        )
        
        # Create a todo for each step
        for i, step in enumerate(plan.steps):
            todo_id = f"{list_id}-{i+1}"
            
            # Determine priority based on step number and complexity
            if step.step_number == 1 or "read" in step.action.lower():
                priority = TodoPriority.HIGH
            elif "test" in step.action.lower() or "validate" in step.action.lower():
                priority = TodoPriority.MEDIUM
            else:
                priority = TodoPriority.MEDIUM
            
            todo = TodoItem(
                id=todo_id,
                title=step.description,
                description=f"{step.rationale}\n\nValidation: {step.validation}",
                priority=priority,
                related_files=step.requires_context
            )
            
            todo_list.add_todo(todo)
        
        self.todo_lists.append(todo_list)
        self.current_list = todo_list
        self._save_state()
        
        return todo_list
    
    def add_todo(self, title: str, description: str = "", 
                 priority: TodoPriority = TodoPriority.MEDIUM,
                 parent_id: Optional[str] = None) -> TodoItem:
        """Add a new todo item.
        
        Args:
            title: Todo title
            description: Detailed description
            priority: Priority level
            parent_id: Parent todo ID for subtasks
            
        Returns:
            Created TodoItem
        """
        if not self.current_list:
            self.current_list = self.create_todo_list_from_query("Current session")
        
        import uuid
        todo_id = str(uuid.uuid4())[:8]
        
        todo = TodoItem(
            id=todo_id,
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id
        )
        
        self.current_list.add_todo(todo)
        self._save_state()
        
        return todo
    
    def mark_completed(self, todo_id: str, note: Optional[str] = None) -> bool:
        """Mark a todo as completed.
        
        Args:
            todo_id: ID of todo to complete
            note: Optional completion note
            
        Returns:
            True if todo was found and marked completed
        """
        if not self.current_list:
            return False
        
        todo = self.current_list.get_todo(todo_id)
        if todo:
            todo.mark_completed()
            if note:
                todo.add_note(note)
            self._save_state()
            return True
        
        return False
    
    def mark_in_progress(self, todo_id: str) -> bool:
        """Mark a todo as in progress.
        
        Args:
            todo_id: ID of todo to update
            
        Returns:
            True if todo was found and updated
        """
        if not self.current_list:
            return False
        
        todo = self.current_list.get_todo(todo_id)
        if todo:
            todo.mark_in_progress()
            self._save_state()
            return True
        
        return False
    
    def mark_failed(self, todo_id: str, reason: str) -> bool:
        """Mark a todo as failed.
        
        Args:
            todo_id: ID of todo to fail
            reason: Failure reason
            
        Returns:
            True if todo was found and marked failed
        """
        if not self.current_list:
            return False
        
        todo = self.current_list.get_todo(todo_id)
        if todo:
            todo.mark_failed(reason)
            self._save_state()
            return True
        
        return False
    
    def get_current_todos(self) -> List[TodoItem]:
        """Get todos from current list.
        
        Returns:
            List of TodoItems in current list
        """
        if not self.current_list:
            return []
        return self.current_list.todos
    
    def get_pending_todos(self) -> List[TodoItem]:
        """Get pending todos from current list.
        
        Returns:
            List of pending TodoItems
        """
        if not self.current_list:
            return []
        return self.current_list.get_pending_todos()
    
    def get_next_todo(self) -> Optional[TodoItem]:
        """Get the next pending todo to work on.
        
        Returns:
            Next pending TodoItem or None
        """
        pending = self.get_pending_todos()
        if not pending:
            return None
        
        # Sort by priority (highest first)
        pending.sort(key=lambda t: t.priority.value, reverse=True)
        return pending[0]
    
    def get_progress(self) -> Dict[str, Any]:
        """Get progress for current todo list.
        
        Returns:
            Progress statistics
        """
        if not self.current_list:
            return {'completed': 0, 'pending': 0, 'percentage': 0}
        
        return self.current_list.get_progress()
    
    def clear_current_list(self):
        """Clear the current todo list."""
        self.current_list = None
        self._save_state()
    
    def _save_state(self):
        """Save todo state to disk."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            
            state = {
                'current_list_id': self.current_list.id if self.current_list else None,
                'todo_lists': [tl.to_dict() for tl in self.todo_lists[-10:]]  # Keep last 10
            }
            
            with open(self.state_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            # Silently fail - don't break the session
            pass
    
    def _load_state(self):
        """Load todo state from disk."""
        try:
            if not self.state_path.exists():
                return
            
            with open(self.state_path, 'r') as f:
                state = json.load(f)
            
            self.todo_lists = [TodoList.from_dict(tl) for tl in state.get('todo_lists', [])]
            
            current_list_id = state.get('current_list_id')
            if current_list_id:
                for tl in self.todo_lists:
                    if tl.id == current_list_id:
                        self.current_list = tl
                        break
        except Exception as e:
            # Silently fail - start fresh
            pass
    
    def format_todos_display(self) -> str:
        """Format todos for terminal display.
        
        Returns:
            Formatted string with todos
        """
        if not self.current_list or not self.current_list.todos:
            return "No active todos"
        
        progress = self.get_progress()
        output = []
        
        # Header
        output.append(f"\n📋 {self.current_list.goal}")
        output.append(f"Progress: {progress['completed']}/{progress['total']} ({progress['percentage']}%)")
        output.append("")
        
        # Todos
        for i, todo in enumerate(self.current_list.todos, 1):
            # Status icon
            if todo.status == TodoStatus.COMPLETED:
                icon = "✓"
                style = "[dim green]"
            elif todo.status == TodoStatus.IN_PROGRESS:
                icon = "○"
                style = "[yellow]"
            elif todo.status == TodoStatus.FAILED:
                icon = "✗"
                style = "[red]"
            else:
                icon = "○"
                style = "[white]"
            
            # Priority indicator
            priority_marker = ""
            if todo.priority == TodoPriority.CRITICAL:
                priority_marker = "🔴 "
            elif todo.priority == TodoPriority.HIGH:
                priority_marker = "🟠 "
            
            output.append(f"{style}{icon} {i}. {priority_marker}{todo.title}[/]")
            
            # Show description for pending/in-progress items
            if todo.status in [TodoStatus.PENDING, TodoStatus.IN_PROGRESS]:
                if todo.description:
                    desc_lines = todo.description.split('\n')[0]  # First line only
                    output.append(f"   [dim]{desc_lines}[/dim]")
        
        output.append("")
        return "\n".join(output)
