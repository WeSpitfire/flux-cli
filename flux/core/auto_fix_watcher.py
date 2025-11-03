"""File watcher for automatic background auto-fixing.

Monitors files for changes and automatically applies safe fixes in the background.
This is a key component of making Flux "invisible" - fixes happen without user intervention.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, Callable, Set, Dict
from dataclasses import dataclass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from flux.core.auto_fixer import AutoFixer, AutoFix


@dataclass
class AutoFixEvent:
    """Represents an automatic fix event."""
    file_path: Path
    fixes_applied: int
    fix_types: Set[str]
    timestamp: float


class AutoFixFileHandler(FileSystemEventHandler):
    """Handles file system events for auto-fixing."""
    
    def __init__(
        self,
        auto_fixer: AutoFixer,
        callback: Optional[Callable[[AutoFixEvent], None]] = None
    ):
        """Initialize handler.
        
        Args:
            auto_fixer: AutoFixer instance
            callback: Optional callback to call when fixes are applied
        """
        self.auto_fixer = auto_fixer
        self.callback = callback
        self.last_modified: Dict[str, float] = {}
        self.debounce_time = 1.0  # Wait 1 second after last change
        self.processing: Set[str] = set()
    
    def _should_process(self, file_path: str) -> bool:
        """Check if file should be processed for auto-fixing.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if should process
        """
        # Ignore patterns
        ignore_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            '.venv',
            'venv',
            '.pytest_cache',
            '.egg-info',
            'dist',
            'build',
            '.pyc',
            '.swp',
            '.tmp',
        ]
        
        for pattern in ignore_patterns:
            if pattern in file_path:
                return False
        
        # Check if supported file type
        path = Path(file_path)
        return self.auto_fixer.can_auto_fix(path)
    
    def _is_debounced(self, file_path: str) -> bool:
        """Check if file is within debounce period.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if still in debounce period
        """
        now = time.time()
        if file_path in self.last_modified:
            if now - self.last_modified[file_path] < self.debounce_time:
                return True
        
        self.last_modified[file_path] = now
        return False
    
    def on_modified(self, event):
        """Handle file modification event.
        
        Args:
            event: File modification event
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if not self._should_process(file_path):
            return
        
        if self._is_debounced(file_path):
            return
        
        if file_path in self.processing:
            return
        
        # Process file async
        self._process_file(Path(file_path))
    
    def _process_file(self, file_path: Path):
        """Process file for auto-fixing.
        
        Args:
            file_path: Path to file to process
        """
        file_str = str(file_path)
        self.processing.add(file_str)
        
        try:
            # Analyze and fix
            fixes = self.auto_fixer.analyze_file(file_path)
            
            if fixes:
                success, count = self.auto_fixer.apply_fixes(file_path, fixes)
                
                if success and count > 0:
                    # Create event
                    fix_types = {f.fix_type.value for f in fixes}
                    event = AutoFixEvent(
                        file_path=file_path,
                        fixes_applied=count,
                        fix_types=fix_types,
                        timestamp=time.time()
                    )
                    
                    # Call callback if provided
                    if self.callback:
                        self.callback(event)
        
        finally:
            self.processing.discard(file_str)


class AutoFixWatcher:
    """Watches files and automatically applies fixes in the background."""
    
    def __init__(
        self,
        auto_fixer: AutoFixer,
        watch_paths: Optional[list[Path]] = None,
        on_fix_applied: Optional[Callable[[AutoFixEvent], None]] = None
    ):
        """Initialize auto-fix watcher.
        
        Args:
            auto_fixer: AutoFixer instance
            watch_paths: Paths to watch (defaults to auto_fixer.cwd)
            on_fix_applied: Callback when fixes are applied
        """
        self.auto_fixer = auto_fixer
        self.watch_paths = watch_paths or [auto_fixer.cwd]
        self.on_fix_applied = on_fix_applied
        self.observer: Optional[Observer] = None
        self.is_running = False
        self.fix_events: list[AutoFixEvent] = []
        self.total_fixes = 0
    
    async def start(self):
        """Start watching for file changes."""
        if self.is_running:
            return
        
        if not self.auto_fixer.enabled:
            return
        
        self.is_running = True
        
        # Create file system observer
        self.observer = Observer()
        handler = AutoFixFileHandler(self.auto_fixer, self._on_fix_applied)
        
        # Watch each path
        for watch_path in self.watch_paths:
            if watch_path.exists():
                self.observer.schedule(handler, str(watch_path), recursive=True)
        
        self.observer.start()
    
    def stop(self):
        """Stop watching for file changes."""
        self.is_running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
    
    def _on_fix_applied(self, event: AutoFixEvent):
        """Handle fix applied event.
        
        Args:
            event: Auto-fix event
        """
        self.fix_events.append(event)
        self.total_fixes += event.fixes_applied
        
        # Call user callback if provided
        if self.on_fix_applied:
            self.on_fix_applied(event)
    
    def get_stats(self) -> Dict:
        """Get statistics about auto-fixes applied.
        
        Returns:
            Dictionary of statistics
        """
        if not self.fix_events:
            return {
                'total_fixes': 0,
                'files_fixed': 0,
                'fix_types': set(),
                'running': self.is_running
            }
        
        all_fix_types = set()
        for event in self.fix_events:
            all_fix_types.update(event.fix_types)
        
        return {
            'total_fixes': self.total_fixes,
            'files_fixed': len(self.fix_events),
            'fix_types': all_fix_types,
            'running': self.is_running,
            'recent_events': self.fix_events[-10:]  # Last 10 events
        }
    
    def clear_stats(self):
        """Clear statistics."""
        self.fix_events.clear()
        self.total_fixes = 0
