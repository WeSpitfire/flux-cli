"""Persistent project memory for Flux.

Tracks current task, checkpoints, recent changes, and important findings per project.
"""


import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_ts() -> float:
    return time.time()


def _human_ts(ts: float) -> str:
    try:
        import datetime as _dt
        return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


@dataclass
class Checkpoint:
    ts: float
    message: str
    files: List[str] = field(default_factory=list)
    tools: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MemoryState:
    project_root: str
    current_task: Optional[str] = None
    checkpoints: List[Checkpoint] = field(default_factory=list)
    recent_files: List[str] = field(default_factory=list)  # most recent first, unique
    notes: List[str] = field(default_factory=list)
    project_files: List[Dict[str, str]] = field(default_factory=list)  # files created in session

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_root": self.project_root,
            "current_task": self.current_task,
            "checkpoints": [asdict(c) for c in self.checkpoints],
            "recent_files": self.recent_files,
            "notes": self.notes,
            "project_files": self.project_files,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MemoryState":
        cps = [Checkpoint(**c) for c in data.get("checkpoints", [])]
        return MemoryState(
            project_root=data.get("project_root", ""),
            current_task=data.get("current_task"),
            checkpoints=cps,
            recent_files=data.get("recent_files", []),
            notes=data.get("notes", []),
            project_files=data.get("project_files", []),
        )


class MemoryStore:
    """Project-scoped persistent memory store."""

    def __init__(self, flux_dir: Path, project_root: Path):
        self.flux_dir = flux_dir
        self.project_root = project_root
        self.memory_dir = self.flux_dir / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.key = self._project_key(project_root)
        self.path = self.memory_dir / f"{self.key}.json"
        self.state: MemoryState = MemoryState(project_root=str(project_root))
        self.load()

    def _project_key(self, root: Path) -> str:
        h = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()
        return h[:16]

    def load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self.state = MemoryState.from_dict(data)
            except Exception:
                # Corrupt file; keep defaults and overwrite next save
                pass

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state.to_dict(), indent=2))
        tmp.replace(self.path)

    # High-level operations

    def set_current_task(self, task: Optional[str]):
        self.state.current_task = task
        self.save()

    def add_checkpoint(self, message: str, files: Optional[List[str]] = None, tools: Optional[List[Dict[str, Any]]] = None):
        cp = Checkpoint(ts=_now_ts(), message=message, files=files or [], tools=tools or [])
        self.state.checkpoints.insert(0, cp)
        # keep only last 50 checkpoints
        self.state.checkpoints = self.state.checkpoints[:50]
        self.save()

    def add_recent_file(self, path: str):
        # de-duplicate and keep recent first, limit to 50
        rf = [p for p in self.state.recent_files if p != path]
        rf.insert(0, path)
        self.state.recent_files = rf[:50]
        self.save()

    def record_tool_use(self, name: str, input_data: Dict[str, Any], result: Dict[str, Any], intent: Optional[str] = None):
        files = []
        if isinstance(result, dict) and "path" in result:
            files.append(str(result["path"]))
            self.add_recent_file(str(result["path"]))
            # Track if this was a write/create operation
            if name in ["write_file", "ast_edit"] and result.get("success"):
                self.add_project_file(str(result["path"]), name)
        if intent:
            msg = f"{name} executed - {intent}"
        else:
            msg = f"{name} executed"
        self.add_checkpoint(msg, files=files, tools=[{"name": name, "input": input_data}])


    def to_context_string(self, max_items: int = 5) -> str:
        lines: List[str] = ["# Project Memory"]
        if self.state.current_task:
            lines.append(f"Current task: {self.state.current_task}")
        if self.state.checkpoints:
            lines.append("Recent checkpoints:")
            for cp in self.state.checkpoints[:max_items]:
                when = _human_ts(cp.ts)
                files_str = f" files={', '.join(Path(f).name for f in cp.files)}" if cp.files else ""
                lines.append(f"  - [{when}] {cp.message}{files_str}")
        if self.state.recent_files:
            names = [Path(p).name for p in self.state.recent_files[:max_items]]
            lines.append(f"Recent files: {', '.join(names)}")
        return "\n".join(lines)

    def add_project_file(self, path: str, operation: str):
        """Track a file created/modified in this session."""
        from pathlib import Path
        file_info = {
            "path": path,
            "name": Path(path).name,
            "operation": operation,
            "timestamp": _now_ts()
        }
        # Avoid duplicates
        existing = [f for f in self.state.project_files if f["path"] == path]
        if not existing:
            self.state.project_files.insert(0, file_info)
            self.state.project_files = self.state.project_files[:50]  # keep last 50
            self.save()

    def get_project_summary(self) -> str:
        """Get a summary of files created in this session."""
        if not self.state.project_files:
            return "No files created in this session yet."

        lines = ["Files created/modified in this session:"]
        for f in self.state.project_files[:10]:
            lines.append(f"  - {f['name']} ({f['operation']}) at {_human_ts(f['timestamp'])}")

        if len(self.state.project_files) > 10:
            lines.append(f"  ... and {len(self.state.project_files) - 10} more")

        return "\n".join(lines)

    # Convenience getters
    def last_checkpoint(self) -> Optional[Checkpoint]:
        return self.state.checkpoints[0] if self.state.checkpoints else None
