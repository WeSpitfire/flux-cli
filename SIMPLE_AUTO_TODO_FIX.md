# Simple Auto-Todo Fix - The Warp Way

## Problem

The current TaskPlanner is too complex and fails when:
1. LLM doesn't return perfect JSON
2. JSON parsing fails → falls back to single generic step
3. Single step just repeats the entire query

**Result**: System detects complexity but doesn't actually help.

## Root Cause

**TaskPlanner tries to be too smart:**
- Asks LLM for JSON plan
- Parses JSON
- If parsing fails → useless fallback

**Warp's approach is simpler:**
- AI just works naturally
- Progress is tracked automatically
- Todos emerge from work, not pre-planning

## Better Solution: Automatic Progress Tracking

Instead of **pre-planning**, track progress **as the AI works**:

```python
# Current (broken):
1. Detect complexity
2. Ask LLM for JSON plan ❌ Fails here
3. Fall back to generic step
4. Execute generic step
5. AI does actual work but no todos shown

# Better (Warp-style):
1. Detect complexity
2. AI starts working immediately
3. Track what AI is doing in real-time
4. Auto-create todos from AI's actions
5. Show progress as it happens
```

## Implementation

### Option A: Remove Pre-Planning (Recommended)

**Change**: Make detection trigger **enhanced mode** instead of pre-planning

**File**: `flux/core/conversation_manager.py` lines 42-48

```python
# SMART TASK DECOMPOSITION
if self.cli.task_planner:
    should_decompose, reason = await self.cli.task_planner.should_decompose(query)
    if should_decompose:
        # Don't try to pre-plan, just enable enhanced tracking
        self.cli.console.print(f"[dim]💡 Complex task detected - enabling progress tracking[/dim]\n")
        
        # Create simple todo list for tracking
        todo_list = self.cli.todo_manager.create_todo_list_from_query(query)
        
        # Add automatic milestone todos
        self.cli.todo_manager.add_todo("Understand requirements", "Analyze what needs to be done")
        self.cli.todo_manager.add_todo("Implement changes", "Make the necessary code changes")
        self.cli.todo_manager.add_todo("Verify & test", "Ensure everything works")
        
        # Show todos
        self.cli.console.print(self.cli.todo_manager.format_todos_display())
        
        # Process normally but with tracking enabled
        await self.process_query_normal(query)
        return
```

**Benefits:**
- ✅ No JSON parsing failures
- ✅ AI works naturally
- ✅ Simple, predictable todos
- ✅ Progress shows what AI actually does

### Option B: Fix JSON Extraction

**Problem**: LLM returns ```json{...}``` instead of pure JSON

**Solution**: Extract JSON from markdown code blocks

**File**: `flux/core/task_planner.py` line 174

```python
# Get plan from LLM
plan_json = await self._get_llm_response(planning_prompt)

# Extract JSON from code blocks if present
import re
json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', plan_json, re.DOTALL)
if json_match:
    plan_json = json_match.group(1)

# Step 4: Parse and create TaskPlan
try:
    plan_data = json.loads(plan_json)
    # ... rest of code
```

### Option C: Make Fallback Actually Useful

**Current fallback** (line 204): Just repeats the entire query

**Better fallback**: Break into logical phases

**File**: `flux/core/task_planner.py` lines 198-213

```python
except (json.JSONDecodeError, KeyError) as e:
    # Fallback: Create useful multi-step plan
    # Parse the goal to create sensible steps
    steps = [
        TaskStep(
            step_number=1,
            description="Read and understand existing code",
            rationale="Need to understand current implementation",
            requires_context=[],
            action="read",
            validation="Files read and understood"
        ),
        TaskStep(
            step_number=2,
            description=f"Implement: {goal}",
            rationale="Core implementation work",
            requires_context=[],
            action="edit",
            validation="Changes implemented"
        ),
        TaskStep(
            step_number=3,
            description="Test and verify changes",
            rationale="Ensure implementation works correctly",
            requires_context=[],
            action="test",
            validation="Tests pass"
        )
    ]
    
    return TaskPlan(
        goal=goal,
        complexity="medium",
        requires_context=[],
        steps=steps
    )
```

## Recommendation

**Do Option A** - it's the simplest and most Warp-like:

1. Detect complexity ✅ (already works)
2. Create simple generic todos ✅ (3 steps always)
3. Let AI work naturally ✅ (no JSON parsing)
4. Track progress automatically ✅ (show what AI does)

This gives users the **feeling** of progress without the brittleness of JSON parsing.

## Quick Fix (5 minutes)

Replace the task planner integration with this simple version:

```python
# In conversation_manager.py lines 42-48
if self.cli.task_planner:
    should_decompose, reason = await self.cli.task_planner.should_decompose(query)
    if should_decompose:
        # Create simple tracking todos
        self.cli.console.print(f"[dim]💡 {reason}[/dim]")
        self.cli.console.print(f"[dim]📋 Creating task tracker...[/dim]\n")
        
        todo_list = self.cli.todo_manager.create_todo_list_from_query(query)
        
        # Add generic milestones
        self.cli.todo_manager.add_todo(
            "🔍 Understand requirements",
            "Analyze codebase and requirements",
            priority=TodoPriority.HIGH
        )
        self.cli.todo_manager.add_todo(
            "⚡ Implement changes",
            "Make necessary code modifications",
            priority=TodoPriority.HIGH
        )
        self.cli.todo_manager.add_todo(
            "✅ Verify & test",
            "Ensure changes work correctly",
            priority=TodoPriority.MEDIUM
        )
        
        # Show todos
        self.cli.console.print(self.cli.todo_manager.format_todos_display())
        self.cli.console.print()
        
        # Let AI work normally
        await self.process_query_normal(query)
        return
```

This removes the TaskPlanner's brittle JSON parsing and just shows progress.

## Result

User sees:
```
💡 Query contains 'redesign' with multiple requirements
📋 Creating task tracker...

📋 Redesign the terminal to feel more modern
Progress: 0/3 (0%)

○ 1. 🟠 🔍 Understand requirements
   Analyze codebase and requirements
○ 2. 🟠 ⚡ Implement changes
   Make necessary code modifications
○ 3. ✅ Verify & test
   Ensure changes work correctly

[AI starts working immediately]
[Shows what it's actually doing in real-time]
```

Much better than a failed JSON parse!

## Summary

**Current**: Complex JSON planning that fails → useless fallback  
**Better**: Simple generic todos + let AI work → shows progress

**Just like Warp**: Progress tracking without brittleness.

Should I implement Option A?
