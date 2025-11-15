"""Conversation State Manager - Persist and restore conversations across sessions.

This module enables true conversation continuity by saving conversation history,
summaries, and project brief to disk and restoring them on startup.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json


@dataclass
class ConversationState:
    """Complete conversation state snapshot.
    
    Contains everything needed to restore a conversation:
    - Conversation history (messages)
    - Summaries
    - Project brief
    - Metadata
    """
    
    # Conversation data
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    summaries: List[Dict[str, Any]] = field(default_factory=list)
    project_brief: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    project_name: str = ""
    project_path: str = ""
    last_message_time: str = ""
    message_count: int = 0
    session_count: int = 0
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        """Set creation timestamp."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'conversation_history': self.conversation_history,
            'summaries': self.summaries,
            'project_brief': self.project_brief,
            'project_name': self.project_name,
            'project_path': self.project_path,
            'last_message_time': self.last_message_time,
            'message_count': self.message_count,
            'session_count': self.session_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """Create from dictionary."""
        return cls(**data)
    
    def get_age_minutes(self) -> float:
        """Get age of last message in minutes.
        
        Returns:
            Minutes since last message (0 if never messaged)
        """
        if not self.last_message_time:
            return 0
        
        try:
            last_time = datetime.fromisoformat(self.last_message_time)
            now = datetime.now()
            delta = now - last_time
            return delta.total_seconds() / 60
        except Exception:
            return 0
    
    def get_summary(self) -> str:
        """Get human-readable summary of state.
        
        Returns:
            Formatted summary string
        """
        age_minutes = self.get_age_minutes()
        
        if age_minutes < 60:
            age_str = f"{int(age_minutes)} minutes ago"
        elif age_minutes < 1440:  # 24 hours
            age_str = f"{int(age_minutes / 60)} hours ago"
        else:
            age_str = f"{int(age_minutes / 1440)} days ago"
        
        summary_count = len(self.summaries)
        
        return (
            f"Project: {self.project_name}\n"
            f"Messages: {self.message_count}\n"
            f"Summaries: {summary_count}\n"
            f"Sessions: {self.session_count}\n"
            f"Last active: {age_str}"
        )


class ConversationStateManager:
    """Manages persistent conversation state across terminal sessions.
    
    Responsibilities:
    - Save conversation state after each message
    - Load state on startup
    - Prompt user to continue or start fresh
    - Manage state lifecycle
    """
    
    def __init__(self, project_name: str, project_path: Path):
        """Initialize state manager.
        
        Args:
            project_name: Name of the project
            project_path: Path to project directory
        """
        self.project_name = project_name
        self.project_path = project_path
        
        # Storage path
        self.storage_dir = Path.home() / ".flux" / "projects" / project_name
        self.state_file = self.storage_dir / "conversation.json"
        
        # Current state
        self.state: Optional[ConversationState] = None
    
    def has_saved_state(self) -> bool:
        """Check if saved state exists.
        
        Returns:
            True if state file exists and is valid
        """
        if not self.state_file.exists():
            return False
        
        try:
            # Try to load to verify it's valid
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return len(data.get('conversation_history', [])) > 0
        except Exception:
            return False
    
    def load_state(self) -> Optional[ConversationState]:
        """Load saved conversation state.
        
        Returns:
            ConversationState if loaded, None if no state or error
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = ConversationState.from_dict(data)
            
            # Increment session count
            state.session_count += 1
            
            self.state = state
            return state
        except Exception as e:
            # If corrupt, return None
            print(f"[Warning] Failed to load conversation state: {e}")
            return None
    
    def save_state(self,
                   conversation_history: List[Dict[str, Any]],
                   summaries: List[Dict[str, Any]],
                   project_brief: Dict[str, Any]):
        """Save current conversation state.
        
        Args:
            conversation_history: Current conversation messages
            summaries: Current summaries
            project_brief: Current project brief
        """
        # Update or create state
        if self.state is None:
            self.state = ConversationState(
                project_name=self.project_name,
                project_path=str(self.project_path),
                session_count=1
            )
        
        # Update state
        self.state.conversation_history = conversation_history
        self.state.summaries = summaries
        self.state.project_brief = project_brief
        self.state.message_count = len(conversation_history)
        self.state.last_message_time = datetime.now().isoformat()
        self.state.updated_at = datetime.now().isoformat()
        
        # Save to disk
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)
    
    def clear_state(self):
        """Clear saved state (start fresh)."""
        if self.state_file.exists():
            self.state_file.unlink()
        self.state = None
    
    def should_prompt_restore(self) -> bool:
        """Check if we should prompt user to restore conversation.
        
        Returns:
            True if state exists and is recent enough to restore
        """
        if not self.has_saved_state():
            return False
        
        state = self.load_state()
        if state is None:
            return False
        
        # Only prompt if conversation was active recently (< 7 days)
        age_minutes = state.get_age_minutes()
        max_age_minutes = 7 * 24 * 60  # 7 days
        
        return age_minutes < max_age_minutes
    
    def get_restore_prompt_message(self) -> str:
        """Get message to show user when prompting to restore.
        
        Returns:
            Formatted prompt message
        """
        if self.state is None:
            return ""
        
        age_minutes = self.state.get_age_minutes()
        
        if age_minutes < 60:
            age_str = f"{int(age_minutes)} minutes ago"
        elif age_minutes < 1440:  # 24 hours
            age_str = f"{int(age_minutes / 60)} hours ago"
        else:
            age_str = f"{int(age_minutes / 1440)} days ago"
        
        return (
            f"Found previous conversation from {age_str}\n"
            f"  Messages: {self.state.message_count}\n"
            f"  Summaries: {len(self.state.summaries)}\n\n"
            f"Continue where you left off?"
        )
    
    def restore_to_managers(self,
                           llm_client,
                           summarizer,
                           project_brief_manager):
        """Restore state to various managers.
        
        Args:
            llm_client: LLM client to restore conversation history to
            summarizer: ConversationSummarizer to restore summaries to
            project_brief_manager: ProjectBrief manager (conversation_manager)
        """
        if self.state is None:
            return
        
        # Restore conversation history
        llm_client.conversation_history = self.state.conversation_history
        
        # Restore summaries
        from flux.core.conversation_summarizer import ConversationSummary
        summarizer.summaries = [
            ConversationSummary.from_dict(s)
            for s in self.state.summaries
        ]
        
        # Restore project brief (merge with existing)
        if self.state.project_brief:
            # Update existing brief with saved values
            project_brief_manager.project_brief.update_from_dict(
                self.state.project_brief
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about saved state.
        
        Returns:
            Dictionary with stats
        """
        if self.state is None:
            return {
                'has_state': False,
                'message_count': 0,
                'summaries_count': 0,
                'session_count': 0,
                'age_minutes': 0
            }
        
        return {
            'has_state': True,
            'message_count': self.state.message_count,
            'summaries_count': len(self.state.summaries),
            'session_count': self.state.session_count,
            'age_minutes': self.state.get_age_minutes(),
            'project_name': self.state.project_name,
            'last_active': self.state.last_message_time
        }


def should_auto_restore(state_manager: ConversationStateManager,
                       max_age_hours: int = 24,
                       min_messages: int = 3) -> bool:
    """Check if conversation should be auto-restored without prompting.
    
    Use this for very recent, substantial conversations that clearly
    should be continued.
    
    Args:
        state_manager: ConversationStateManager instance
        max_age_hours: Max age in hours for auto-restore (default 24)
        min_messages: Min messages for auto-restore (default 3)
    
    Returns:
        True if should auto-restore
    """
    if not state_manager.has_saved_state():
        return False
    
    state = state_manager.load_state()
    if state is None:
        return False
    
    # Check age
    age_minutes = state.get_age_minutes()
    if age_minutes > max_age_hours * 60:
        return False
    
    # Check message count
    if state.message_count < min_messages:
        return False
    
    return True
