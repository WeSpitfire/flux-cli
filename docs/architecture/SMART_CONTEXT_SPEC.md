# Smart Context Management - Feature Specification

## Problem
Currently, Flux reads entire files even when only small portions are relevant. This:
- Wastes tokens
- Hits context limits on large files
- Slows down responses
- Makes it hard to work with large codebases

## Solution
Implement smart context management that:
1. Reads only relevant portions of files
2. Auto-detects related files
3. Summarizes large contexts
4. Stays within token budgets

---

## Feature 1: Partial File Reading

### Goal
Read only the relevant sections of a file instead of the entire file.

### Implementation
Create `flux/core/smart_reader.py` with:

```python
class SmartReader:
    """Intelligently reads portions of files."""
    
    def read_function(self, file_path: Path, function_name: str) -> str:
        """Read only a specific function from a file."""
        # Use AST to extract just that function
        
    def read_class(self, file_path: Path, class_name: str) -> str:
        """Read only a specific class from a file."""
        
    def read_lines(self, file_path: Path, start: int, end: int) -> str:
        """Read specific line range."""
        
    def read_with_context(self, file_path: Path, target: str, context_lines: int = 5) -> str:
        """Read target (function/class) with surrounding context."""
```

### New Tool Parameters
Update `ReadFilesTool` to accept:
- `target` (optional) - specific function/class to read
- `lines` (optional) - line range like "10-50"
- `context_lines` (optional) - how many lines around target

---

## Feature 2: Dependency Detection

### Goal
Auto-detect files that are related to the current task.

### Implementation
Create `flux/core/dependency_detector.py`:

```python
class DependencyDetector:
    """Detects related files automatically."""
    
    def find_imports(self, file_path: Path) -> List[Path]:
        """Find all files imported by this file."""
        
    def find_importers(self, file_path: Path) -> List[Path]:
        """Find all files that import this file."""
        
    def find_related_tests(self, file_path: Path) -> List[Path]:
        """Find test files for this source file."""
        
    def suggest_relevant_files(self, file_path: Path, operation: str) -> List[Path]:
        """Suggest files to read based on operation type."""
```

### Usage
When user asks to modify `api.py`, automatically suggest:
- Files that `api.py` imports
- Test files for `api.py`
- Files that use `api.py`

---

## Feature 3: Context Summarization

### Goal
Summarize large files/contexts to fit within token limits.

### Implementation
Add to `flux/core/smart_reader.py`:

```python
def summarize_file(self, file_path: Path, max_tokens: int = 500) -> str:
    """Create a summary of file structure."""
    # Return:
    # - List of functions/classes with signatures
    # - Key imports
    # - Docstrings
    # - No implementation details
    
def summarize_function(self, code: str) -> str:
    """Create a summary of a function."""
    # Return signature + docstring, strip implementation
```

### Example Output
```
File: api.py (250 lines)
├── Imports: flask, sqlalchemy, typing
├── Classes:
│   └── UserAPI(BaseAPI)
│       ├── get_user(user_id: int) -> User
│       ├── create_user(data: dict) -> User
│       └── delete_user(user_id: int) -> bool
└── Functions:
    └── validate_email(email: str) -> bool
```

---

## Feature 4: Token Budget Management

### Goal
Stay within token limits by intelligently managing what to read.

### Implementation
Create `flux/core/token_budget.py`:

```python
class TokenBudget:
    """Manages token allocation for context."""
    
    def __init__(self, max_tokens: int = 150000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
        
    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens in text (roughly 4 chars = 1 token)."""
        
    def can_read(self, file_path: Path) -> bool:
        """Check if we have budget to read this file."""
        
    def prioritize_reads(self, files: List[Path]) -> List[Path]:
        """Sort files by relevance/size to fit in budget."""
```

---

## Integration Plan

### Phase 1: Core Infrastructure
1. Create `SmartReader` class
2. Create `DependencyDetector` class  
3. Add token estimation utilities

### Phase 2: Tool Integration
1. Update `ReadFilesTool` to use `SmartReader`
2. Add optional parameters for targeted reading
3. Maintain backward compatibility

### Phase 3: Auto-Detection
1. Integrate `DependencyDetector`
2. Auto-suggest related files
3. Add to system prompt

---

## Success Criteria

✅ Can read specific functions without loading entire file
✅ Auto-detects related files (imports, tests)
✅ Generates useful file summaries
✅ Stays within token budget on large projects
✅ Backward compatible (still can read full files)

---

## Example Usage

**Before:**
```
You: Fix the get_user function
Flux: [reads entire 500-line api.py file, uses 2000 tokens]
```

**After:**
```
You: Fix the get_user function
Flux: [reads only get_user function + imports, uses 200 tokens]
      [auto-detects test_api.py and shows it as suggestion]
```

---

## Files to Create/Modify

### New Files
- `flux/core/smart_reader.py`
- `flux/core/dependency_detector.py`
- `flux/core/token_budget.py`

### Modified Files
- `flux/tools/file_ops.py` - Update ReadFilesTool
- `flux/llm/prompts.py` - Update system prompt

---

## Notes for Implementation

- Use tree-sitter for Python/JS/TS parsing (already available)
- For other languages, fall back to simple line-based reading
- Cache file summaries to avoid re-parsing
- Make everything optional - don't break existing behavior
