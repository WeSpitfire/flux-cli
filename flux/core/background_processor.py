"""Smart background processing for Flux.

While streaming responses to the user, intelligently pre-load files and
prepare context to make subsequent operations feel instant.
"""

import asyncio
import re
from pathlib import Path
from typing import Set, List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time


@dataclass
class BackgroundMetrics:
    """Track effectiveness of background processing."""
    
    cache_hits: int = 0
    cache_misses: int = 0
    files_preloaded: int = 0
    time_saved_ms: int = 0
    predictions_made: int = 0
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def report(self) -> str:
        """Generate human-readable metrics report."""
        return (
            f"Background Processing Stats:\n"
            f"  Files preloaded: {self.files_preloaded}\n"
            f"  Cache hits: {self.cache_hits}\n"
            f"  Cache misses: {self.cache_misses}\n"
            f"  Hit rate: {self.hit_rate():.1%}\n"
            f"  Time saved: {self.time_saved_ms}ms\n"
            f"  Predictions: {self.predictions_made}"
        )


class SmartBackgroundProcessor:
    """Intelligently processes background tasks during streaming.
    
    This processor analyzes streaming text in real-time to predict what
    files and context will be needed next, then pre-loads them in the
    background while the user is reading the response.
    """
    
    # File patterns to detect in streaming text
    FILE_PATTERNS = [
        # Standard file paths
        r'`([a-zA-Z0-9_\-./]+\.(py|js|jsx|ts|tsx|go|java|rb|rs|cpp|c|h|hpp|php|md|json|yaml|yml|toml|ini|cfg|conf))`',
        # Without backticks but with extension
        r'\b([a-zA-Z0-9_\-./]+\.(py|js|jsx|ts|tsx|go|java|rb|rs|cpp|c|h|hpp|php))\b',
    ]
    
    # Keywords that suggest file reading will happen
    ACTION_KEYWORDS = {
        'read': ['read', 'check', 'look at', 'examine', 'review', 'inspect', 'see'],
        'edit': ['edit', 'modify', 'change', 'update', 'fix', 'refactor'],
        'test': ['test', 'pytest', 'jest', 'verify', 'validate'],
    }
    
    def __init__(self, cwd: Path, max_cache_size: int = 50):
        """Initialize background processor.
        
        Args:
            cwd: Current working directory
            max_cache_size: Maximum number of files to cache
        """
        self.cwd = cwd
        self.max_cache_size = max_cache_size
        
        # Cache: {Path: (content, timestamp)}
        self.cache: Dict[Path, tuple] = {}
        
        # Track what we've seen
        self.mentioned_files: Set[Path] = set()
        self.running_tasks: Set[asyncio.Task] = set()
        
        # Metrics
        self.metrics = BackgroundMetrics()
        
        # Prediction state
        self.likely_action: Optional[str] = None
    
    def analyze_chunk(self, text_chunk: str) -> List[Dict[str, Any]]:
        """Analyze a chunk of streaming text and generate background tasks.
        
        Args:
            text_chunk: Chunk of text from LLM response
            
        Returns:
            List of background tasks to execute
        """
        tasks = []
        
        # Extract file mentions
        files = self._extract_file_mentions(text_chunk)
        for file_path in files:
            if file_path not in self.mentioned_files:
                self.mentioned_files.add(file_path)
                tasks.append({
                    'action': 'preload_file',
                    'path': file_path,
                    'priority': 1
                })
                self.metrics.predictions_made += 1
        
        # Detect likely actions
        action = self._detect_action(text_chunk)
        if action and action != self.likely_action:
            self.likely_action = action
            tasks.append({
                'action': f'prepare_{action}',
                'priority': 2
            })
        
        return tasks
    
    def _extract_file_mentions(self, text: str) -> Set[Path]:
        """Extract file paths mentioned in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Set of Path objects for mentioned files
        """
        files = set()
        
        for pattern in self.FILE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                # Handle tuple from regex group
                file_str = match[0] if isinstance(match, tuple) else match
                
                try:
                    path = Path(file_str)
                    
                    # Skip if it looks like a URL or absolute system path
                    if file_str.startswith('http') or file_str.startswith('/usr'):
                        continue
                    
                    # Make relative to cwd
                    if not path.is_absolute():
                        full_path = self.cwd / path
                    else:
                        full_path = path
                    
                    # Only include if file likely exists
                    if full_path.exists():
                        files.add(full_path)
                except (ValueError, OSError):
                    # Invalid path, skip it
                    continue
        
        return files
    
    def _detect_action(self, text: str) -> Optional[str]:
        """Detect likely next action from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Action name or None
        """
        text_lower = text.lower()
        
        for action, keywords in self.ACTION_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return action
        
        return None
    
    async def execute_task(self, task: Dict[str, Any]):
        """Execute a background task.
        
        Args:
            task: Task dictionary with 'action' and other parameters
        """
        try:
            if task['action'] == 'preload_file':
                await self._preload_file(task['path'])
            elif task['action'].startswith('prepare_'):
                # Future: prepare context for specific actions
                pass
        except Exception:
            # Silent failure - this is speculative work
            # We don't want to crash if a prediction was wrong
            pass
    
    async def _preload_file(self, path: Path):
        """Pre-load a file into cache.
        
        Args:
            path: Path to file to pre-load
        """
        # Check if already cached
        if path in self.cache:
            return
        
        # Check cache size limit
        if len(self.cache) >= self.max_cache_size:
            # Evict oldest entry (simple LRU)
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]
        
        # Read file
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Cache it
                self.cache[path] = (content, time.time())
                self.metrics.files_preloaded += 1
        except Exception:
            # File couldn't be read, skip it
            pass
    
    def get_cached_file(self, path: Path) -> Optional[str]:
        """Get file from cache if available.
        
        Args:
            path: Path to file
            
        Returns:
            File content if cached, None otherwise
        """
        # Normalize path
        if not path.is_absolute():
            path = self.cwd / path
        
        if path in self.cache:
            self.metrics.cache_hits += 1
            return self.cache[path][0]  # Return content
        else:
            self.metrics.cache_misses += 1
            return None
    
    def record_time_saved(self, ms: int):
        """Record time saved by cache hit.
        
        Args:
            ms: Milliseconds saved
        """
        self.metrics.time_saved_ms += ms
    
    def clear_cache(self):
        """Clear the file cache."""
        self.cache.clear()
        self.mentioned_files.clear()
        self.likely_action = None
    
    def get_metrics(self) -> BackgroundMetrics:
        """Get current metrics.
        
        Returns:
            BackgroundMetrics object
        """
        return self.metrics
    
    async def schedule_and_run(self, tasks: List[Dict[str, Any]]):
        """Schedule and run background tasks without blocking.
        
        Args:
            tasks: List of task dictionaries
        """
        for task in tasks:
            # Create task and don't await it (fire and forget)
            bg_task = asyncio.create_task(self.execute_task(task))
            self.running_tasks.add(bg_task)
            
            # Clean up completed tasks
            bg_task.add_done_callback(self.running_tasks.discard)
