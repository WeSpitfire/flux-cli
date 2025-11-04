"""Undo system for reversible file operations."""

import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


def _now_ts() -> float:
    """Get current timestamp."""
    return datetime.now().timestamp()


def _human_ts(ts: float) -> str:
    """Format timestamp for humans."""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


@dataclass
class UndoSnapshot:
    """Snapshot of a file operation for undo."""
    ts: float
    operation: str  # 'write', 'edit', 'ast_edit'
    file_path: str
    old_content: Optional[str]  # None if file didn't exist
    new_content: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "UndoSnapshot":
        return UndoSnapshot(**data)


@dataclass
class UndoState:
    """State of undo history for a project."""
    project_root: str
    snapshots: List[UndoSnapshot] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_root": self.project_root,
            "snapshots": [s.to_dict() for s in self.snapshots]
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "UndoState":
        snapshots = [UndoSnapshot.from_dict(s) for s in data.get("snapshots", [])]
        return UndoState(
            project_root=data.get("project_root", ""),
            snapshots=snapshots
        )


class UndoManager:
    """Manages undo history for file operations."""

    MAX_SNAPSHOTS = 20

    def __init__(self, flux_dir: Path, project_root: Path):
        """Initialize undo manager.

        Args:
            flux_dir: Flux configuration directory (~/.flux)
            project_root: Root directory of current project
        """
        self.flux_dir = flux_dir
        self.project_root = project_root
        self.undo_dir = self.flux_dir / "undo"
        self.undo_dir.mkdir(parents=True, exist_ok=True)

        # Generate project key from path hash
        self.key = self._project_key(project_root)
        self.state_path = self.undo_dir / f"{self.key}.json"

        # Load or initialize state
        self.state = UndoState(project_root=str(project_root))
        self.load()

    def _project_key(self, root: Path) -> str:
        """Generate unique key for project."""
        h = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()
        return h[:16]

    def load(self):
        """Load undo state from disk."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                self.state = UndoState.from_dict(data)
            except Exception:
                # Corrupt file; keep defaults and overwrite next save
                pass

    def save(self):
        """Save undo state to disk."""
        try:
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.state.to_dict(), indent=2))
            tmp.replace(self.state_path)
        except Exception as e:
            # Silently fail - undo is a nice-to-have feature
            pass

    def snapshot_operation(
        self,
        operation: str,
        file_path: Path,
        old_content: Optional[str],
        new_content: str,
        description: str
    ):
        """Take a snapshot of a file operation before it's executed.

        Args:
            operation: Type of operation ('write', 'edit', 'ast_edit')
            file_path: Path to file being modified
            old_content: Original file content (None if file didn't exist)
            new_content: New file content
            description: Human-readable description of the change
        """
        snapshot = UndoSnapshot(
            ts=_now_ts(),
            operation=operation,
            file_path=str(file_path),
            old_content=old_content,
            new_content=new_content,
            description=description
        )

        # Add to front of list (most recent first)
        self.state.snapshots.insert(0, snapshot)

        # Trim to max size
        self.state.snapshots = self.state.snapshots[:self.MAX_SNAPSHOTS]

        # Save to disk
        self.save()

    def undo_last(self) -> Dict[str, Any]:
        """Undo the last operation.

        Returns:
            Dict with success status and details
        """
        if not self.state.snapshots:
            return {"error": "No operations to undo"}

        # Get most recent snapshot
        snapshot = self.state.snapshots[0]

        # Restore file to old state
        file_path = Path(snapshot.file_path)

        try:
            if snapshot.old_content is None:
                # File didn't exist before - delete it
                if file_path.exists():
                    file_path.unlink()
                    action = "deleted"
                else:
                    action = "already gone"
            else:
                # Restore old content
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(snapshot.old_content)
                action = "restored"

            # Remove snapshot from history
            self.state.snapshots.pop(0)
            self.save()

            return {
                "success": True,
                "file": str(file_path),
                "action": action,
                "description": snapshot.description,
                "timestamp": _human_ts(snapshot.ts)
            }

        except Exception as e:
            return {"error": f"Failed to undo: {str(e)}"}

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get undo history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of snapshot summaries
        """
        history = []
        for i, snapshot in enumerate(self.state.snapshots[:limit]):
            history.append({
                "index": i,
                "timestamp": _human_ts(snapshot.ts),
                "operation": snapshot.operation,
                "file": Path(snapshot.file_path).name,
                "full_path": snapshot.file_path,
                "description": snapshot.description
            })
        return history

    def clear_history(self):
        """Clear all undo history."""
        self.state.snapshots = []
        self.save()
