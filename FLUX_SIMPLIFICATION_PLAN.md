# Flux Simplification Plan

## The Problem
Flux has become an over-engineered monster that doesn't actually help developers. We spent weeks building features nobody uses while the core AI remains dumb.

## The Solution: Strip It Down to What Matters

### 1. Use a Better AI Model (CRITICAL)
**Current**: Claude 3 Haiku (weak, can't understand context)  
**Fix**: Default to Claude 3.5 Sonnet or GPT-4
```bash
# In config.py, change default:
model: str = "claude-3-5-sonnet-20241022"  # NOT haiku!
```

### 2. Remove Over-Engineered Features
Delete these completely - they add complexity with no value:
- ❌ Parallel executor (tools are fast enough sequentially)
- ❌ Streaming pipeline (adds complexity, no real benefit)
- ❌ Workflow automation (nobody records/replays workflows)
- ❌ Intelligent cache (premature optimization)
- ❌ Semantic search (the lightweight version barely works)
- ❌ 50+ manager classes that do nothing
- ❌ Session restoration (annoying, not helpful)

### 3. What Flux Should Actually Be

```python
class SimpleFlux:
    """A coding assistant that just works."""
    
    def __init__(self):
        self.ai = ClaudeSonnet()  # Use the BEST model
        self.tools = [
            ReadFile(),      # Read files
            WriteFile(),     # Write files  
            RunCommand(),    # Run commands
            Search()         # Search codebase
        ]
    
    def chat(self, message):
        # Send to AI with tools
        # Execute tools
        # Return response
        # That's it!
```

### 4. Fix the Desktop App

The current app has issues:
- Too many tabs spawn automatically
- Session restoration is annoying
- Takes too long to start
- Crashes frequently

**Simple fix**: 
1. Start with ONE tab
2. NO session restoration
3. NO auto-retry on crashes
4. Simple terminal + AI chat

### 5. The 80/20 Features That Matter

Keep ONLY these:
1. **Smart file editing** - AI can read/write files
2. **Command execution** - Run tests, build, etc.
3. **Codebase search** - Find things quickly
4. **Context awareness** - Remember what we're working on
5. **Good error messages** - When things fail, explain why

Remove EVERYTHING else.

### 6. Implementation Steps

#### Step 1: Switch to Better Model (5 minutes)
```python
# flux/core/config.py
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
# or
DEFAULT_MODEL = "gpt-4-turbo"
```

#### Step 2: Disable Complex Features (10 minutes)
```python
# flux/ui/cli_builder.py
# Comment out all the "smart" features:
# cli.performance = None  # Kill performance "improvements"
# cli.workflow = None     # Kill workflow automation
# cli.copilot = None      # Kill "intelligent" suggestions
```

#### Step 3: Simplify Desktop App (Done!)
- ✅ Disabled session restoration
- TODO: Remove multi-tab spawning
- TODO: Remove auto-retry logic

#### Step 4: Focus on Core Loop
```
User asks question → AI understands → Tools execute → Clear response
```

That's it. No caching, no parallelization, no "smart" features.

## Why This Will Work

1. **Better AI = Better Experience** - Claude Sonnet/GPT-4 actually understand context
2. **Less Code = Fewer Bugs** - Remove 70% of the codebase
3. **Faster Startup** - No complex initialization
4. **Actually Helpful** - Focuses on what developers need

## The Truth

We built a Ferrari engine (all the infrastructure) but put it in a car with square wheels (Haiku model). 

**The fix isn't more features - it's using a better AI and removing complexity.**

## Next Actions

1. **Immediate**: Switch to Claude Sonnet (config change)
2. **Today**: Disable all "smart" features
3. **This Week**: Rip out unnecessary code
4. **Result**: A simple, fast, ACTUALLY HELPFUL coding assistant

Remember: **Developers don't want features. They want their problems solved.**