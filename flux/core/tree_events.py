"""Event system for Living Tree visualization.

This module provides a simple event emitter that tools can use to
broadcast file operations and codebase navigation events to the
Desktop UI for real-time visualization.
"""

import json
import sys
from typing import Any, Dict, Optional
from pathlib import Path


class TreeEventEmitter:
    """Emits events for the Living Tree visualization."""
    
    def __init__(self, enabled: bool = True):
        """Initialize the event emitter.
        
        Args:
            enabled: Whether to emit events (disabled in CLI mode)
        """
        self.enabled = enabled
        self._sequence = 0
    
    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to the Desktop UI.
        
        Events are written to stdout as JSON with a special prefix
        that the Desktop app can detect and route to the Living Tree.
        
        Args:
            event_type: Type of event (e.g., 'file-read', 'file-edit')
            data: Event data (must be JSON-serializable)
        """
        if not self.enabled:
            return
        
        try:
            self._sequence += 1
            event = {
                "type": "tree-event",
                "event": event_type,
                "data": data,
                "sequence": self._sequence
            }
            
            # Write to stdout with special prefix for Desktop to detect
            # Format: __FLUX_TREE_EVENT__<json>__END__
            event_json = json.dumps(event)
            sys.stdout.write(f"__FLUX_TREE_EVENT__{event_json}__END__\n")
            sys.stdout.flush()
            
        except Exception as e:
            # Silently fail - don't let visualization errors break functionality
            pass
    
    def file_read(self, path: str, parent: Optional[str] = None) -> None:
        """Emit event when a file is read.
        
        Args:
            path: Absolute path to the file being read
            parent: Optional parent file that triggered this read
        """
        data = {"path": str(path)}
        if parent:
            data["parent"] = str(parent)
        self.emit("file-read", data)
    
    def file_edit(self, path: str) -> None:
        """Emit event when a file is edited.
        
        Args:
            path: Absolute path to the file being edited
        """
        self.emit("file-edit", {"path": str(path)})
    
    def file_create(self, path: str, parent: Optional[str] = None) -> None:
        """Emit event when a file is created.
        
        Args:
            path: Absolute path to the file being created
            parent: Optional parent file/directory
        """
        data = {"path": str(path)}
        if parent:
            data["parent"] = str(parent)
        self.emit("file-create", data)
    
    def file_delete(self, path: str) -> None:
        """Emit event when a file is deleted.
        
        Args:
            path: Absolute path to the file being deleted
        """
        self.emit("file-delete", {"path": str(path)})
    
    def dependency_found(self, from_file: str, to_file: str, 
                        dep_type: str = "import") -> None:
        """Emit event when a dependency is discovered.
        
        Args:
            from_file: File that depends on another
            to_file: File being depended on
            dep_type: Type of dependency (import, require, etc.)
        """
        self.emit("dependency-found", {
            "from": str(from_file),
            "to": str(to_file),
            "type": dep_type
        })
    
    def analysis_start(self, path: str) -> None:
        """Emit event when analysis starts on a file.
        
        Args:
            path: Absolute path to the file being analyzed
        """
        self.emit("analysis-start", {"path": str(path)})
    
    def analysis_complete(self, path: str) -> None:
        """Emit event when analysis completes on a file.
        
        Args:
            path: Absolute path to the file that was analyzed
        """
        self.emit("analysis-complete", {"path": str(path)})
    
    def search_result(self, query: str, path: str, matches: int) -> None:
        """Emit event when a search finds results in a file.
        
        Args:
            query: The search query
            path: File where matches were found
            matches: Number of matches
        """
        self.emit("search-result", {
            "query": query,
            "path": str(path),
            "matches": matches
        })


# Global instance
_global_emitter: Optional[TreeEventEmitter] = None


def get_emitter() -> TreeEventEmitter:
    """Get the global tree event emitter.
    
    Returns:
        The global TreeEventEmitter instance
    """
    global _global_emitter
    if _global_emitter is None:
        # Auto-detect if we're in Desktop mode by checking environment
        import os
        is_desktop = os.environ.get('FLUX_DESKTOP_MODE') == '1'
        _global_emitter = TreeEventEmitter(enabled=is_desktop)
    return _global_emitter


def set_emitter(emitter: TreeEventEmitter) -> None:
    """Set the global tree event emitter.
    
    Args:
        emitter: TreeEventEmitter instance to use globally
    """
    global _global_emitter
    _global_emitter = emitter


# Convenience functions for direct use
def emit_file_read(path: str, parent: Optional[str] = None) -> None:
    """Emit file-read event."""
    get_emitter().file_read(path, parent)


def emit_file_edit(path: str) -> None:
    """Emit file-edit event."""
    get_emitter().file_edit(path)


def emit_file_create(path: str, parent: Optional[str] = None) -> None:
    """Emit file-create event."""
    get_emitter().file_create(path, parent)


def emit_file_delete(path: str) -> None:
    """Emit file-delete event."""
    get_emitter().file_delete(path)


def emit_dependency_found(from_file: str, to_file: str, 
                         dep_type: str = "import") -> None:
    """Emit dependency-found event."""
    get_emitter().dependency_found(from_file, to_file, dep_type)


def emit_analysis_start(path: str) -> None:
    """Emit analysis-start event."""
    get_emitter().analysis_start(path)


def emit_analysis_complete(path: str) -> None:
    """Emit analysis-complete event."""
    get_emitter().analysis_complete(path)


def emit_search_result(query: str, path: str, matches: int) -> None:
    """Emit search-result event."""
    get_emitter().search_result(query, path, matches)
