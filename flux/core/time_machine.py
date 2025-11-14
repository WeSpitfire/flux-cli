"""Time Machine - Complete project state snapshots and restore."""

import json
import time
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class StateSnapshot:
    """A complete snapshot of project state at a point in time."""
    snapshot_id: str
    timestamp: float
    description: str
    git_commit: Optional[str]
    git_branch: Optional[str]
    modified_files: List[str]
    conversation_state: Dict
    memory_state: Dict
    task_state: Dict
    metrics: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StateSnapshot':
        """Create from dictionary."""
        return cls(**data)
    
    def get_display_time(self) -> str:
        """Get human-readable timestamp."""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class TimeMachine:
    """Manages project state snapshots and time-travel restoration."""
    
    def __init__(self, flux_dir: Path, cwd: Path):
        """Initialize Time Machine.
        
        Args:
            flux_dir: Flux configuration directory
            cwd: Current working directory
        """
        self.flux_dir = flux_dir
        self.cwd = cwd
        self.snapshots_dir = flux_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-snapshot settings
        self.auto_snapshot_enabled = True
        self.auto_snapshot_interval = 300  # 5 minutes
        self.last_snapshot_time = 0
        
        # Snapshot limits
        self.max_snapshots = 100
        self.max_age_days = 30
        
    def create_snapshot(
        self,
        description: str,
        git,
        llm,
        memory,
        workspace,
        state_tracker
    ) -> StateSnapshot:
        """Create a complete state snapshot.
        
        Args:
            description: Human-readable description
            git: Git integration
            llm: LLM provider (for conversation state)
            memory: Memory store
            workspace: Workspace manager
            state_tracker: State tracker
            
        Returns:
            StateSnapshot object
        """
        # Generate unique snapshot ID
        snapshot_id = f"snap_{int(time.time())}_{hashlib.md5(description.encode()).hexdigest()[:8]}"
        
        # Get git state
        git_status = git.get_status()
        git_commit = None
        git_branch = None
        
        if git_status.is_repo:
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    capture_output=True,
                    text=True,
                    cwd=self.cwd,
                    timeout=5
                )
                if result.returncode == 0:
                    git_commit = result.stdout.strip()
                git_branch = git_status.branch
            except Exception:
                pass
        
        # Get modified files
        modified_files = git_status.modified_files + git_status.untracked_files if git_status.is_repo else []
        
        # Capture conversation state
        conversation_state = {
            'history_length': len(llm.conversation_history),
            'history': llm.conversation_history.copy(),
            'token_usage': llm.get_token_usage()
        }
        
        # Capture memory state
        memory_state = {
            'current_task': memory.state.current_task,
            'checkpoints': memory.state.checkpoints.copy(),
            'context': memory.state.context.copy()
        }
        
        # Capture task state
        tasks = workspace.list_tasks(limit=50)
        task_state = {
            'tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'status': t.status.value,
                    'priority': t.priority.value
                }
                for t in tasks
            ]
        }
        
        # Capture metrics
        summary = state_tracker.get_context_summary(max_age_minutes=60)
        metrics = {
            'files_modified': len(summary['files']['recently_modified']),
            'commands_run': summary['commands']['recent_count'],
            'tests_status': summary['tests']['last_passed']
        }
        
        # Create snapshot object
        snapshot = StateSnapshot(
            snapshot_id=snapshot_id,
            timestamp=time.time(),
            description=description,
            git_commit=git_commit,
            git_branch=git_branch,
            modified_files=modified_files,
            conversation_state=conversation_state,
            memory_state=memory_state,
            task_state=task_state,
            metrics=metrics
        )
        
        # Save snapshot
        self._save_snapshot(snapshot)
        
        # Backup modified files
        self._backup_files(snapshot_id, modified_files)
        
        # Update last snapshot time
        self.last_snapshot_time = time.time()
        
        # Clean old snapshots
        self._cleanup_old_snapshots()
        
        return snapshot
    
    def should_auto_snapshot(self) -> bool:
        """Check if it's time for an automatic snapshot."""
        if not self.auto_snapshot_enabled:
            return False
        return time.time() - self.last_snapshot_time >= self.auto_snapshot_interval
    
    def restore_snapshot(
        self,
        snapshot_id: str,
        llm,
        memory,
        restore_files: bool = False
    ) -> bool:
        """Restore project state from a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to restore
            llm: LLM provider
            memory: Memory store
            restore_files: Whether to restore backed-up files
            
        Returns:
            True if successful
        """
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            return False
        
        # Restore conversation state
        if snapshot.conversation_state:
            llm.conversation_history = snapshot.conversation_state['history'].copy()
        
        # Restore memory state
        if snapshot.memory_state:
            memory.state.current_task = snapshot.memory_state['current_task']
            memory.state.checkpoints = snapshot.memory_state['checkpoints'].copy()
            memory.state.context = snapshot.memory_state['context'].copy()
            memory.save()
        
        # Restore files if requested
        if restore_files:
            self._restore_files(snapshot_id, snapshot.modified_files)
        
        return True
    
    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Get a snapshot by ID."""
        snapshot_file = self.snapshots_dir / f"{snapshot_id}.json"
        if not snapshot_file.exists():
            return None
        
        try:
            with open(snapshot_file, 'r') as f:
                data = json.load(f)
            return StateSnapshot.from_dict(data)
        except Exception:
            return None
    
    def list_snapshots(self, limit: int = 20) -> List[StateSnapshot]:
        """List recent snapshots."""
        snapshots = []
        
        for snapshot_file in sorted(self.snapshots_dir.glob("snap_*.json"), reverse=True):
            try:
                with open(snapshot_file, 'r') as f:
                    data = json.load(f)
                snapshots.append(StateSnapshot.from_dict(data))
                
                if len(snapshots) >= limit:
                    break
            except Exception:
                continue
        
        return snapshots
    
    def compare_snapshots(self, snapshot_id1: str, snapshot_id2: str) -> Dict:
        """Compare two snapshots and show differences."""
        snap1 = self.get_snapshot(snapshot_id1)
        snap2 = self.get_snapshot(snapshot_id2)
        
        if not snap1 or not snap2:
            return {}
        
        comparison = {
            'time_diff': snap2.timestamp - snap1.timestamp,
            'conversation_messages_diff': snap2.conversation_state['history_length'] - snap1.conversation_state['history_length'],
            'files_changed': len(set(snap2.modified_files) - set(snap1.modified_files)),
            'task_diff': len(snap2.task_state['tasks']) - len(snap1.task_state['tasks']),
            'git_commits_diff': snap1.git_commit != snap2.git_commit
        }
        
        return comparison
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        snapshot_file = self.snapshots_dir / f"{snapshot_id}.json"
        backup_dir = self.snapshots_dir / f"{snapshot_id}_files"
        
        try:
            if snapshot_file.exists():
                snapshot_file.unlink()
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            return True
        except Exception:
            return False
    
    def _save_snapshot(self, snapshot: StateSnapshot):
        """Save snapshot to disk."""
        snapshot_file = self.snapshots_dir / f"{snapshot.snapshot_id}.json"
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)
    
    def _backup_files(self, snapshot_id: str, files: List[str]):
        """Backup modified files for a snapshot."""
        backup_dir = self.snapshots_dir / f"{snapshot_id}_files"
        backup_dir.mkdir(exist_ok=True)
        
        for file_path in files[:50]:  # Limit to 50 files
            source = self.cwd / file_path
            if not source.exists() or not source.is_file():
                continue
            
            try:
                # Create subdirectories
                dest = backup_dir / file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source, dest)
            except Exception:
                pass
    
    def _restore_files(self, snapshot_id: str, files: List[str]):
        """Restore backed-up files from a snapshot."""
        backup_dir = self.snapshots_dir / f"{snapshot_id}_files"
        if not backup_dir.exists():
            return
        
        for file_path in files:
            source = backup_dir / file_path
            if not source.exists():
                continue
            
            try:
                dest = self.cwd / file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
            except Exception:
                pass
    
    def _cleanup_old_snapshots(self):
        """Remove old snapshots beyond limits."""
        snapshots = self.list_snapshots(limit=self.max_snapshots + 50)
        
        # Remove beyond max count
        if len(snapshots) > self.max_snapshots:
            for snapshot in snapshots[self.max_snapshots:]:
                self.delete_snapshot(snapshot.snapshot_id)
        
        # Remove beyond max age
        cutoff_time = time.time() - (self.max_age_days * 24 * 3600)
        for snapshot in snapshots:
            if snapshot.timestamp < cutoff_time:
                self.delete_snapshot(snapshot.snapshot_id)
    
    def get_summary(self) -> Dict:
        """Get Time Machine summary statistics."""
        snapshots = self.list_snapshots(limit=100)
        
        return {
            'enabled': self.auto_snapshot_enabled,
            'total_snapshots': len(snapshots),
            'oldest_snapshot': snapshots[-1].get_display_time() if snapshots else None,
            'newest_snapshot': snapshots[0].get_display_time() if snapshots else None,
            'interval_minutes': self.auto_snapshot_interval // 60,
            'max_snapshots': self.max_snapshots,
            'max_age_days': self.max_age_days
        }
