"""File watcher for automatic test execution on file changes."""

import asyncio
import time
from pathlib import Path
from typing import Optional, Callable, Set, Dict, List
from dataclasses import dataclass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from flux.core.test_runner import TestRunner, TestResult


@dataclass
class WatchConfig:
    """Configuration for test watcher."""
    watch_paths: List[Path]
    ignore_patterns: List[str]
    debounce_seconds: float = 0.5
    run_all_on_start: bool = False


class TestFileHandler(FileSystemEventHandler):
    """Handles file system events for test watching."""
    
    def __init__(self, test_runner: TestRunner, callback: Callable):
        """Initialize handler.
        
        Args:
            test_runner: TestRunner instance
            callback: Callback function to call on file change
        """
        self.test_runner = test_runner
        self.callback = callback
        self.last_modified: Dict[str, float] = {}
        self.debounce_time = 0.5  # seconds
    
    def _should_process(self, file_path: str) -> bool:
        """Check if file change should trigger tests."""
        # Ignore patterns
        ignore_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache',
            'node_modules',
            '.venv',
            'venv',
            '.egg-info',
            '.pyc',
        ]
        
        for pattern in ignore_patterns:
            if pattern in file_path:
                return False
        
        # Only process source and test files
        valid_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']
        return any(file_path.endswith(ext) for ext in valid_extensions)
    
    def _is_debounced(self, file_path: str) -> bool:
        """Check if file change is within debounce period."""
        now = time.time()
        if file_path in self.last_modified:
            if now - self.last_modified[file_path] < self.debounce_time:
                return True
        
        self.last_modified[file_path] = now
        return False
    
    def on_modified(self, event):
        """Handle file modification event."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if not self._should_process(file_path):
            return
        
        if self._is_debounced(file_path):
            return
        
        # Trigger callback
        self.callback(Path(file_path))
    
    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if not self._should_process(file_path):
            return
        
        # Trigger callback
        self.callback(Path(file_path))


class TestWatcher:
    """Watches files and automatically runs tests on changes."""
    
    def __init__(
        self,
        test_runner: TestRunner,
        watch_paths: Optional[List[Path]] = None,
        on_test_complete: Optional[Callable[[TestResult], None]] = None
    ):
        """Initialize test watcher.
        
        Args:
            test_runner: TestRunner instance
            watch_paths: Paths to watch (defaults to cwd)
            on_test_complete: Callback when tests complete
        """
        self.test_runner = test_runner
        self.watch_paths = watch_paths or [test_runner.cwd]
        self.on_test_complete = on_test_complete
        self.observer: Optional[Observer] = None
        self.is_running = False
        self.changed_files: Set[Path] = set()
        self.test_in_progress = False
        self.run_queue: asyncio.Queue = asyncio.Queue()
    
    async def start(self):
        """Start watching for file changes."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Create file system observer
        self.observer = Observer()
        handler = TestFileHandler(self.test_runner, self._on_file_changed)
        
        # Watch each path
        for watch_path in self.watch_paths:
            if watch_path.exists():
                self.observer.schedule(handler, str(watch_path), recursive=True)
        
        self.observer.start()
        
        # Start test runner loop
        asyncio.create_task(self._test_runner_loop())
    
    def stop(self):
        """Stop watching for file changes."""
        self.is_running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
    
    def _on_file_changed(self, file_path: Path):
        """Handle file change event."""
        if not self.is_running:
            return
        
        self.changed_files.add(file_path)
        
        # Queue a test run (non-blocking)
        try:
            self.run_queue.put_nowait(file_path)
        except asyncio.QueueFull:
            pass  # Already queued
    
    async def _test_runner_loop(self):
        """Background loop that runs tests when files change."""
        while self.is_running:
            try:
                # Wait for file change
                changed_file = await asyncio.wait_for(
                    self.run_queue.get(),
                    timeout=1.0
                )
                
                # Debounce - wait a bit to collect more changes
                await asyncio.sleep(0.3)
                
                # Drain the queue to get all recent changes
                recent_changes = {changed_file}
                while not self.run_queue.empty():
                    try:
                        recent_changes.add(self.run_queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break
                
                # Run tests
                if not self.test_in_progress:
                    await self._run_tests_for_files(recent_changes)
                
            except asyncio.TimeoutError:
                # No changes, continue waiting
                continue
            except Exception as e:
                print(f"Error in test runner loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _run_tests_for_files(self, changed_files: Set[Path]):
        """Run tests for changed files."""
        if self.test_in_progress:
            return
        
        self.test_in_progress = True
        
        try:
            # Determine which tests to run
            test_files = set()
            
            for file_path in changed_files:
                # If it's a test file, run it directly
                if self._is_test_file(file_path):
                    test_files.add(file_path)
                else:
                    # Find related test files
                    related_tests = self.test_runner.get_test_files_for_source(file_path)
                    test_files.update(related_tests)
            
            # Run tests
            if test_files:
                # Run specific test files
                test_filter = " ".join(str(f) for f in test_files)
                result = await asyncio.to_thread(
                    self.test_runner.run_tests,
                    file_filter=test_filter
                )
            else:
                # Run all tests if no specific test files found
                result = await asyncio.to_thread(self.test_runner.run_tests)
            
            # Notify callback
            if self.on_test_complete:
                self.on_test_complete(result)
            
        finally:
            self.test_in_progress = False
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        name = file_path.name
        
        # Python test patterns
        if name.startswith('test_') and name.endswith('.py'):
            return True
        if name.endswith('_test.py'):
            return True
        
        # JavaScript test patterns
        if name.endswith('.test.js') or name.endswith('.test.ts'):
            return True
        if name.endswith('.spec.js') or name.endswith('.spec.ts'):
            return True
        
        # Check if in test directory
        parts = file_path.parts
        if 'tests' in parts or 'test' in parts or '__tests__' in parts:
            return True
        
        return False
    
    def get_status(self) -> Dict:
        """Get current watcher status."""
        return {
            'running': self.is_running,
            'watching': [str(p) for p in self.watch_paths],
            'changed_files': len(self.changed_files),
            'test_in_progress': self.test_in_progress,
            'last_result': self.test_runner.last_result
        }
