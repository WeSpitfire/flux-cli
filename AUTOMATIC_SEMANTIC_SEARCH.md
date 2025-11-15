# Automatic Semantic Search - "Just Works" Brain

## Problem

Users have to remember commands like `/semantic-search` and `/index-project`. This is friction.

**Warp's Magic**: AI just works - no commands needed.

**Our Goal**: Same magic for Flux.

## Solution: Intelligent Auto-Detection

### Phase 1: Auto-Index on Startup (Background)

When Flux starts in a project, **automatically index in background** if:
- Project not indexed yet, OR
- Index is stale (files changed)

**User sees**: Nothing! Just happens silently.

```python
# On startup
async def _auto_index_if_needed():
    if not index_exists() or index_is_stale():
        # Index in background thread
        asyncio.create_task(engine.index_project())
```

**Implementation**:
1. Check `.flux/embeddings/index_metadata.json` on startup
2. If missing or old, start background indexing
3. Show subtle indicator: "🔍 Indexing codebase..." in corner
4. When done: "✓ Ready for semantic search"

### Phase 2: Smart Tool Selection (AI Decides)

AI **automatically chooses** semantic search when appropriate.

**Current state**: Semantic search is already a registered tool!
```python
cli.tools.register(SemanticSearchTool(cwd, llm_client=cli.llm))
```

**The AI can already use it!** We just need to:
1. Make tool description better
2. Add examples to system prompt
3. Let AI decide when to use it

### Phase 3: Natural Language Understanding

User says natural things, AI knows what to do:

| User Query | AI Action | Why |
|------------|-----------|-----|
| "Where do we handle errors?" | Uses `semantic_search("error handling")` | Exploratory question |
| "Show me authentication code" | Uses `semantic_search("authentication")` | Finding concept |
| "Fix bug in login.py" | Uses `read_files("login.py")` | Specific file |
| "Search for 'validateEmail'" | Uses `grep_search("validateEmail")` | Exact symbol |

**AI learns patterns** from tool descriptions and past usage.

## Implementation Plan

### Step 1: Background Auto-Indexing

**File**: `flux/ui/cli.py`

Add to startup sequence:

```python
async def _auto_index_project(self):
    """Auto-index project in background if needed."""
    try:
        from flux.core.semantic_search import SemanticSearchEngine
        
        engine = SemanticSearchEngine(
            project_path=self.cwd,
            llm_client=self.llm
        )
        
        # Check if index exists and is recent
        metadata_path = engine.index_metadata_path
        needs_index = True
        
        if metadata_path.exists():
            import json
            from datetime import datetime, timedelta
            
            with open(metadata_path) as f:
                data = json.load(f)
                last_indexed = data.get('last_indexed')
                
                if last_indexed:
                    last_time = datetime.fromisoformat(last_indexed)
                    # Re-index if older than 7 days
                    if datetime.now() - last_time < timedelta(days=7):
                        needs_index = False
        
        if needs_index:
            # Show subtle indicator
            self.console.print("[dim]🔍 Indexing codebase for semantic search...[/dim]")
            
            # Index in background
            await engine.index_project(max_files=500)
            
            # Save timestamp
            import json
            from datetime import datetime
            with open(metadata_path, 'r+') as f:
                data = json.load(f)
                data['last_indexed'] = datetime.now().isoformat()
                f.seek(0)
                json.dump(data, f)
                f.truncate()
            
            self.console.print("[dim]✓ Semantic search ready[/dim]")
    
    except Exception as e:
        # Silent fail - don't bother user
        logger.debug(f"Auto-index failed: {e}")
```

Call on startup:
```python
def run(self):
    # ... existing startup code ...
    
    # Auto-index in background (non-blocking)
    asyncio.create_task(self._auto_index_project())
    
    # Continue to main loop
```

### Step 2: Enhanced Tool Description

**File**: `flux/tools/search.py`

Make the tool description more detailed so AI knows when to use it:

```python
@property
def description(self) -> str:
    return """Search code semantically using natural language.

Use this tool when:
- User asks "where do we...", "show me...", "find..."
- User wants to find code by concept/pattern (not exact name)
- User is exploring unfamiliar codebase
- User asks about implementation details

Examples:
- "where do we handle authentication?" → search "authentication logic"
- "show me error handling" → search "error handling patterns"
- "find database queries" → search "database queries"

DO NOT use for:
- Exact symbol names (use grep_search instead)
- Specific file paths (use read_files instead)
- Recent changes (use git commands instead)

Returns code chunks with relevance scores."""
```

### Step 3: Smart System Prompt

**File**: `flux/llm/prompts.py`

Add guidance to system prompt:

```python
TOOL_USAGE_GUIDANCE = """
## Smart Tool Selection

When user asks exploratory questions about code:
1. Use semantic_search for concepts/patterns
2. Use grep_search for exact symbols
3. Use read_files for specific files

Examples:
- "where do we validate input?" → semantic_search("input validation")
- "find the User class" → grep_search("class User")
- "read auth.py" → read_files("auth.py")

Choose the right tool based on user intent.
"""
```

### Step 4: Intent Detection Patterns

Add pattern matching to help AI decide:

```python
SEMANTIC_SEARCH_PATTERNS = [
    r"where (do|does|is|are) (we|the|it)",
    r"(show|find|locate) (me )?(the )?(code|implementation|logic)",
    r"how (do|does) (we|the|it)",
    r"what('s| is) (the|our) (approach|pattern|strategy)",
]

EXACT_SEARCH_PATTERNS = [
    r"(function|class|method|variable) (called|named)",
    r"search for ['\"]",
    r"find the exact",
]
```

## User Experience

### Before (Manual)
```
User: "Where do we handle authentication?"
User: (thinks... should I use /semantic-search? /grep? Just ask?)
User: "/semantic-search authentication"
Flux: [results]
```

### After (Automatic)
```
User: "Where do we handle authentication?"
Flux: [automatically uses semantic_search tool]
      "I found authentication code in these locations:
      
      1. flux/auth/middleware.py (lines 45-120)
         - Main authentication middleware
      2. flux/auth/jwt.py (lines 23-78)
         - JWT token validation
      ..."
```

**Zero friction!** User just asks, AI figures it out.

## Implementation Checklist

### Phase 1: Auto-Index (Essential)
- [ ] Add `_auto_index_project()` to CLI startup
- [ ] Check if index exists/stale
- [ ] Index in background (non-blocking)
- [ ] Save last_indexed timestamp
- [ ] Show subtle status indicator

### Phase 2: Tool Enhancement (Quick Win)
- [ ] Enhance SemanticSearchTool description with examples
- [ ] Add "when to use" guidance
- [ ] Add "when NOT to use" guidance
- [ ] Test that AI understands descriptions

### Phase 3: System Prompt (Important)
- [ ] Add tool selection guidance to system prompt
- [ ] Add example patterns
- [ ] Add decision tree logic
- [ ] Test with various user queries

### Phase 4: Smart Defaults (Polish)
- [ ] Auto-detect user intent from query
- [ ] Suggest semantic search for exploratory queries
- [ ] Fall back gracefully if index not ready
- [ ] Show "indexing..." if tool called before ready

## Testing Scenarios

Test these user queries to ensure AI picks right tool:

| Query | Expected Tool | Why |
|-------|---------------|-----|
| "Where do we validate emails?" | semantic_search | Exploratory concept |
| "Show me the validateEmail function" | grep_search | Exact symbol |
| "Read config.py" | read_files | Specific file |
| "Find all TODO comments" | grep_search | Exact pattern |
| "How does authentication work?" | semantic_search | Concept exploration |
| "What's in the User class?" | grep_search + read_files | Specific symbol + read |

## Benefits

### For Users
✅ **Zero learning curve** - Just ask questions naturally  
✅ **No commands to remember** - AI figures it out  
✅ **Faster workflow** - No thinking about which tool to use  
✅ **Better results** - AI picks optimal tool for query  

### For Developers (Us)
✅ **Less support** - No explaining commands  
✅ **Better UX** - Feels magical like Warp  
✅ **More usage** - People use features they discover naturally  
✅ **Data** - Learn what users actually search for  

## Cost Impact

**Auto-indexing**: ~$0.005 per project (one-time, then every 7 days)  
**Semantic searches**: ~$0.000001 per search (negligible)  

**Total**: Essentially free (<$0.10/month per user)

## Timeline

- **Day 1**: Auto-index on startup (~2 hours)
- **Day 2**: Enhanced tool descriptions (~1 hour)
- **Day 3**: System prompt guidance (~2 hours)
- **Day 4**: Testing & refinement (~3 hours)

**Total**: ~1 week to complete

## Next Steps

1. **Start with auto-indexing** - This is the foundation
2. **Enhance tool descriptions** - Quick win
3. **Test with real queries** - See what AI does
4. **Refine system prompt** - Based on testing

Should I start implementing Phase 1 (auto-index on startup)?
