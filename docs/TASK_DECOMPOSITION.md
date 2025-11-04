# Smart Task Decomposition

Flux now has **autonomous task decomposition** - it can break down complex tasks and execute them step-by-step, without user intervention.

## How It Works

### 1. **Automatic Detection**
When you give Flux a complex task, it automatically detects whether decomposition is needed:

```
✅ Detected: "Build a /search command..." → Complex task
❌ Detected: "What does this code do?" → Simple question
```

**Indicators of complex tasks:**
- "Build", "create", "implement", "add feature"
- Multiple requirements ("X and Y")
- Long descriptions (>10 words with action verbs)

### 2. **Context Gathering**
Before planning, Flux asks itself: *"What do I need to understand?"*

```
Goal: Build a /search command
Context needed:
  - How are other commands implemented? → Read cli.py
  - How does codebase graph work? → Read codebase_graph.py
  - What's the pattern for slash commands? → Search existing code
```

### 3. **Smart Planning**
Flux creates a validated, context-aware plan:

```
Plan created: 4 steps
Complexity: medium

Execution Plan:
  1. Read cli.py to understand command patterns
     Rationale: Need to follow existing implementation style
  2. Create flux/core/code_search.py with CodeSearcher class
     Rationale: Separate concerns - search logic in dedicated module
  3. Integrate /search command into cli.py
     Rationale: Wire up the command following existing patterns
  4. Test the /search command with sample queries
     Rationale: Verify functionality before completion
```

### 4. **Step-by-Step Execution**
Each step is executed through Flux's normal conversation mode:
- ✅ Full access to all tools
- ✅ Can read files, edit code, run tests
- ✅ Self-validates before moving to next step
- ✅ Can self-correct on failures

### 5. **Self-Correction**
If a step fails, Flux replans:

```
Step 3 failed: Search text not found in cli.py
Replanning...

Adjusted Plan:
  3a. Re-read cli.py to get current structure
  3b. Find correct insertion point for /search command
  3c. Add /search command with correct indentation
```

## Key Differences from Old Orchestrator

| Feature | Old Orchestrator | New Task Planner |
|---------|-----------------|------------------|
| **Context** | Blind planning | Gathers context first |
| **Execution** | All-at-once | Step-by-step with validation |
| **Code Quality** | Stub code | Working code only |
| **Adaptability** | Rigid plan | Replans on failures |
| **Intelligence** | Tool sequencing | Full LLM reasoning per step |

## Architecture

```
┌─────────────────────────────────────┐
│         User Query                  │
│  "Build a /search command..."       │
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│    should_decompose()                │
│  Detect complexity                  │
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│    analyze_and_plan()                │
│  1. Identify required context       │
│  2. Gather context (read files)     │
│  3. Create validated plan           │
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│    Execute each step                │
│  - Read required context            │
│  - Execute via conversation mode    │
│  - Validate result                  │
│  - Mark complete or replan          │
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│    Complete or Self-Correct         │
│  ✓ All steps done → Success!        │
│  ✗ Step failed → Replan & retry     │
└─────────────────────────────────────┘
```

## Usage Examples

### Example 1: Feature Development

```
You: Build a /search command that finds code patterns using semantic search

Flux: 💡 Complex task detected: Query contains 'Build' with multiple requirements
      🧠 Analyzing and planning execution...
      
      ✅ Plan created: 4 steps
      Complexity: medium
      
      Execution Plan:
        1. Read cli.py to understand slash command patterns
           Rationale: Need to follow existing implementation style
        2. Create code_search.py with semantic search logic
           Rationale: Separate concerns for maintainability
        3. Add /search command handler to cli.py
           Rationale: Wire up the new functionality
        4. Test with sample search queries
           Rationale: Validate end-to-end functionality
      
      Step 1: Read cli.py to understand slash command patterns
      [... executes and reads relevant sections ...]
      ✓ Step 1 completed
      
      Step 2: Create code_search.py with semantic search logic
      [... creates working implementation ...]
      ✓ Step 2 completed
      
      [... continues through all steps ...]
      
      🎉 Task completed successfully!
```

### Example 2: Simple Question (No Decomposition)

```
You: What does the CodebaseGraph class do?

Flux: [No decomposition - answered directly]
      The CodebaseGraph class builds a semantic representation of your codebase...
```

### Example 3: Self-Correction

```
You: Refactor the validator and add comprehensive tests

Flux: 💡 Complex task detected
      ✅ Plan created: 3 steps
      
      Step 1: Read current validator code
      ✓ Step 1 completed
      
      Step 2: Refactor validator with improved error handling
      ✗ Step 2 failed: Import error - missing dependency
      
      Replanning...
      
      Adjusted Plan:
        2a. Install missing dependency
        2b. Update imports in validator
        2c. Refactor with new dependency
      
      [... continues with adjusted plan ...]
```

## Configuration

The task planner is automatically enabled when:
- Codebase graph is built
- Task complexity warrants it
- User provides a complex goal

No manual configuration needed!

## Benefits

1. **Autonomous Execution**: No need to break down tasks manually
2. **Context-Aware**: Reads relevant code before planning
3. **Validated Steps**: Each step produces working code
4. **Self-Correcting**: Adjusts plan when steps fail
5. **Transparent**: Shows plan and progress
6. **Flexible**: Falls back to conversation mode if needed

## Future Enhancements

- [ ] Learning from past task executions
- [ ] Parallel step execution when possible
- [ ] Confidence scoring for plan quality
- [ ] Integration with project-specific patterns
- [ ] Memory of common task patterns

## Related Files

- `flux/core/task_planner.py` - Core planning logic
- `flux/ui/cli.py` - Integration and execution
- `flux/core/orchestrator.py` - Legacy workflow system (kept for simple workflows)
