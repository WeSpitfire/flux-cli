# Smart Background Processing Design

## Concept

While Flux streams its response to the user, use that time to intelligently prepare for what's likely to happen next. The user is reading/watching the animation anyway, so we can use that time productively.

## Architecture

### 1. Response Analyzer (Real-time)

```python
class ResponseAnalyzer:
    """Analyzes streaming response to predict next actions."""
    
    def __init__(self):
        self.patterns = {
            'file_edit': ['edit', 'modify', 'change', 'update', 'fix'],
            'file_read': ['check', 'look at', 'examine', 'review'],
            'test_run': ['test', 'verify', 'validate'],
            'search': ['find', 'search', 'locate', 'grep'],
        }
        self.mentioned_files = set()
        self.predicted_actions = []
    
    def analyze_chunk(self, text_chunk: str):
        """Analyze a chunk of streamed text."""
        # Extract file mentions
        files = self._extract_file_mentions(text_chunk)
        self.mentioned_files.update(files)
        
        # Predict likely next actions
        for action, keywords in self.patterns.items():
            if any(kw in text_chunk.lower() for kw in keywords):
                self.predicted_actions.append(action)
        
        return self._generate_background_tasks()
```

### 2. Background Task Manager

```python
class BackgroundTaskManager:
    """Manages background tasks during response streaming."""
    
    def __init__(self):
        self.task_queue = asyncio.Queue()
        self.cache = {}
        self.running_tasks = []
    
    async def schedule_task(self, task_type: str, **kwargs):
        """Schedule a background task."""
        task = {
            'type': task_type,
            'priority': self._calculate_priority(task_type),
            'kwargs': kwargs
        }
        await self.task_queue.put(task)
    
    async def process_tasks(self):
        """Process background tasks concurrently."""
        while not self.task_queue.empty():
            task = await self.task_queue.get()
            
            # Don't block - run in background
            asyncio.create_task(self._execute_task(task))
    
    async def _execute_task(self, task):
        """Execute a specific background task."""
        if task['type'] == 'preload_file':
            await self._preload_file(task['kwargs']['path'])
        elif task['type'] == 'find_related':
            await self._find_related_files(task['kwargs']['file'])
        # ... more task types
```

### 3. Integration with CLI

```python
# In flux/ui/cli.py
async def process_query(self, query: str):
    """Process query with smart background processing."""
    
    # Initialize analyzers
    analyzer = ResponseAnalyzer()
    bg_tasks = BackgroundTaskManager()
    
    response_text = ""
    
    # Stream LLM response
    async for event in self.llm.send_message(...):
        if event["type"] == "text":
            chunk = event["content"]
            response_text += chunk
            self.console.print(chunk, end="")
            
            # SMART PART: Analyze while streaming
            tasks = analyzer.analyze_chunk(chunk)
            for task in tasks:
                await bg_tasks.schedule_task(**task)
    
    # Background tasks are now ready/running
    # When tool execution starts, cache is warm!
```

## Specific Use Cases

### Use Case 1: File Editing

**User:** "Fix the bug in auth.py"

**While Flux streams response:**
```
Flux: "I'll fix the authentication bug in auth.py. 
       First, let me read the file to understand the issue..."
       
Background (parallel):
✓ Read auth.py (cache it)
✓ Find related files (session.py, user.py)
✓ Load git blame for auth.py
✓ Check if tests exist for auth
✓ Load test output if available
```

**When Flux calls read_file:**
- ✅ Already cached! Instant response
- ✅ Related files ready
- ✅ Context is warm

### Use Case 2: Testing

**User:** "Run the tests for the API module"

**While Flux streams:**
```
Flux: "I'll run the tests for the API module. Let me first
       check which test framework you're using..."
       
Background:
✓ Scan for pytest.ini, jest.config.js, etc.
✓ Find test files in tests/ directory
✓ Check if dependencies are installed
✓ Load previous test output from .flux/
✓ Identify likely test command
```

**When Flux executes:**
- ✅ Test framework already detected
- ✅ Test files pre-scanned
- ✅ Faster execution

### Use Case 3: Refactoring

**User:** "Refactor the database layer to use async/await"

**While Flux streams:**
```
Flux: "I'll refactor the database layer. This is a significant
       change that will affect multiple files..."
       
Background:
✓ Find all files importing database code
✓ Build dependency graph
✓ Identify test files that need updating
✓ Check for migration files
✓ Scan for blocking I/O patterns
✓ Pre-compute impact analysis
```

**Result:**
- ✅ Flux has full context immediately
- ✅ Impact analysis ready
- ✅ Comprehensive refactoring plan

## Implementation Priorities

### Phase 1: Low-Hanging Fruit (2-3 hours)

1. **File Mention Detection**
   - Regex patterns for file paths in text
   - Pre-read mentioned files
   - Cache in memory

2. **Action Keyword Detection**
   - Simple keyword matching
   - Schedule obvious next tasks
   - Non-blocking execution

### Phase 2: Smart Predictions (4-6 hours)

1. **Pattern Learning**
   - Track what actions typically follow certain queries
   - Build a simple decision tree
   - Improve predictions over time

2. **Codebase Graph Integration**
   - Use existing CodebaseGraph
   - Find related files proactively
   - Load likely dependencies

### Phase 3: Advanced Intelligence (6-8 hours)

1. **LLM-Assisted Prediction**
   - Use fast model (Haiku) to predict next steps
   - While main model streams response
   - Dual-LLM architecture

2. **Speculative Execution**
   - Pre-compute multiple likely scenarios
   - Cache multiple outcomes
   - Select correct one when needed

## Technical Challenges

### Challenge 1: Don't Slow Down Streaming

**Solution:**
- All background tasks are `asyncio.create_task()` (fire and forget)
- Never `await` during streaming
- Use separate thread pool if needed

### Challenge 2: Wasted Work

**Solution:**
- Cancel tasks if prediction was wrong
- Learn from cancellations to improve
- Low-cost operations first (reading < parsing < analysis)

### Challenge 3: Memory Usage

**Solution:**
- LRU cache with size limits
- Only cache high-value items
- Clear cache between queries

### Challenge 4: Race Conditions

**Solution:**
- Immutable data structures where possible
- Proper async locking for shared state
- Optimistic execution with validation

## Metrics to Track

```python
@dataclass
class BackgroundProcessingMetrics:
    """Track effectiveness of background processing."""
    
    # Hit rates
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Predictions
    correct_predictions: int = 0
    incorrect_predictions: int = 0
    
    # Performance
    time_saved_ms: int = 0  # Time saved by warm cache
    background_task_time_ms: int = 0  # Time spent on bg tasks
    
    # User experience
    perceived_latency_reduction: float = 0.0  # Subjective improvement
```

## Example Implementation

```python
# flux/core/background_processor.py

import asyncio
import re
from pathlib import Path
from typing import Set, List, Dict, Any

class SmartBackgroundProcessor:
    """Intelligently processes background tasks during streaming."""
    
    def __init__(self, cwd: Path, codebase_graph=None):
        self.cwd = cwd
        self.codebase = codebase_graph
        self.cache: Dict[str, Any] = {}
        self.mentioned_files: Set[Path] = set()
        
    def analyze_streaming_text(self, text_chunk: str) -> List[Dict]:
        """Analyze text chunk and return background tasks."""
        tasks = []
        
        # Extract file mentions
        file_pattern = r'`?([a-zA-Z0-9_\-./]+\.(py|js|ts|go|java|rb))`?'
        matches = re.findall(file_pattern, text_chunk)
        
        for match in matches:
            file_path = Path(match[0])
            if file_path not in self.mentioned_files:
                self.mentioned_files.add(file_path)
                tasks.append({
                    'action': 'preload_file',
                    'path': file_path,
                    'priority': 1
                })
        
        # Detect likely actions
        if any(kw in text_chunk.lower() for kw in ['edit', 'modify', 'change']):
            tasks.append({
                'action': 'prepare_edit_context',
                'priority': 2
            })
        
        if any(kw in text_chunk.lower() for kw in ['test', 'pytest', 'jest']):
            tasks.append({
                'action': 'detect_test_framework',
                'priority': 1
            })
        
        return tasks
    
    async def execute_background_task(self, task: Dict):
        """Execute a background task without blocking."""
        try:
            if task['action'] == 'preload_file':
                await self._preload_file(task['path'])
            elif task['action'] == 'prepare_edit_context':
                await self._prepare_edit_context()
            elif task['action'] == 'detect_test_framework':
                await self._detect_test_framework()
        except Exception as e:
            # Silent failure - this is speculative work
            pass
    
    async def _preload_file(self, path: Path):
        """Pre-read a file into cache."""
        full_path = self.cwd / path
        if full_path.exists() and full_path not in self.cache:
            with open(full_path, 'r') as f:
                self.cache[full_path] = f.read()
    
    async def _prepare_edit_context(self):
        """Prepare context for editing operations."""
        # Load git status
        # Find recently modified files
        # Warm up syntax checker
        pass
    
    async def _detect_test_framework(self):
        """Detect and cache test framework info."""
        # Check for pytest.ini, jest.config.js, etc.
        # Cache test command
        pass
    
    def get_cached_file(self, path: Path) -> Optional[str]:
        """Get file from cache if available."""
        return self.cache.get(self.cwd / path)
```

## Integration Points

### 1. In CLI Response Loop

```python
# flux/ui/cli.py
bg_processor = SmartBackgroundProcessor(self.cwd, self.codebase_graph)

async for event in self.llm.send_message(...):
    if event["type"] == "text":
        chunk = event["content"]
        
        # Analyze and schedule background tasks
        tasks = bg_processor.analyze_streaming_text(chunk)
        for task in tasks:
            asyncio.create_task(bg_processor.execute_background_task(task))
        
        # Continue streaming
        self.console.print(chunk, end="")
```

### 2. In Tool Execution

```python
# flux/tools/file_ops.py
async def execute(self, path: str):
    # Check cache first
    cached = bg_processor.get_cached_file(Path(path))
    if cached:
        return cached  # Instant!
    
    # Otherwise read from disk
    return self._read_from_disk(path)
```

## Expected Benefits

1. **Perceived Performance**: 30-50% faster (feels instant)
2. **Actual Performance**: 10-20% faster (cache hits)
3. **Better UX**: Smoother, more responsive experience
4. **Smarter System**: Learns from patterns over time

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Memory bloat | LRU cache with limits |
| CPU spike | Rate limit background tasks |
| Wrong predictions | Low-cost operations first |
| Complexity | Start simple, iterate |

## Next Steps

1. Implement Phase 1 (file mention detection)
2. Measure impact with metrics
3. Iterate based on real usage
4. Add Phase 2 when Phase 1 proves valuable
