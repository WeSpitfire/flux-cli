# 🧠 Conversation Memory Improvements

## Problem Analysis

**Current State**: Flux suffers from the classic "AI forgetting" problem described in the brief:
1. ✅ Has `conversation_history` list
2. ✅ Has basic context pruning
3. ❌ **No summarization** - just drops old messages
4. ❌ **No persistent state** - loses everything on restart
5. ❌ **No project brief** - architecture/constraints fall off
6. ❌ **No structured state** - relies only on chat history

**Result**: After 10-15 messages, Flux "forgets" the project, constraints, and earlier decisions.

---

## What Flux Already Has (Good)

### 1. Context Manager (`flux/core/context_manager.py`)
- Prunes conversation history intelligently
- Keeps relevant messages about current file
- Tracks tokens and estimates costs

### 2. Smart Context (`flux/core/smart_context.py`)
- Knowledge graph of codebase
- Learns from conversations
- Stores entities and relationships

### 3. State Tracker (`flux/core/state_tracker.py`)
- Tracks current task
- Records test results
- Remembers modified files

### 4. Session Manager (`flux/core/session_task_manager.py`)
- Records events
- Tracks session activity
- Provides context

---

## What's Missing (Critical Gaps)

### 1. **No Conversation Summarization**
When history gets too long, Flux just **drops old messages**.

**Problem**:
```
[System: You're a dev assistant]
[User: We're building a todo app with React/Express]
[User: Use MongoDB for storage]
[User: All API responses must have { success, data, error }]
... 20 more messages ...
[Old messages dropped] ❌
[Flux forgets it's a todo app]
[Flux forgets the API format]
```

**Solution Needed**: Summarize before dropping!

---

### 2. **No Persistent Project Brief**
No structured memory of:
- What we're building
- Tech stack
- Architecture decisions
- Coding conventions
- Constraints

**Example of what's lost**:
```
Initial conversation:
"We're building a GSM grading app.
Stack: Next.js 15 + Express + MongoDB.
NEVER change API contracts.
ALWAYS return full file contents when modifying."

After 15 messages:
❌ Flux tries to use a different API format
❌ Flux returns partial file changes
❌ Flux forgets it's a grading app
```

---

### 3. **No Persistent State File**
When you close terminal or restart:
- ❌ All conversation lost
- ❌ All context gone
- ❌ Have to re-explain everything

---

## Solutions to Implement

### Priority 1: Conversation Summarization (HIGH IMPACT)

#### Implementation
Create `flux/core/conversation_summarizer.py`:

```python
class ConversationSummarizer:
    """Summarizes old conversation chunks before dropping them."""
    
    async def summarize_chunk(self, messages: List[dict]) -> str:
        """
        Takes 10-15 old messages and asks LLM to summarize them.
        
        Returns compact summary like:
        "Project: Building todo app with React/Express/MongoDB.
         Decisions: Using JWT auth, RESTful API with {success, data} format.
         Completed: User authentication, task CRUD.
         Currently: Adding task filtering and search."
        """
        
    def should_summarize(self, history: List[dict]) -> bool:
        """Check if it's time to summarize (every 20 messages)."""
```

#### Integration Point
In `conversation_manager.py` line 52:
```python
# Before pruning, check if we should summarize
if len(self.conversation_history) > 20:
    if not hasattr(self, '_last_summary_at'):
        self._last_summary_at = 0
    
    if len(self.conversation_history) - self._last_summary_at >= 20:
        # Summarize messages 0-20
        chunk = self.conversation_history[:20]
        summary = await self.summarizer.summarize_chunk(chunk)
        
        # Replace chunk with summary
        summary_message = {
            "role": "user",
            "content": f"[CONVERSATION SUMMARY]\n{summary}"
        }
        self.conversation_history = [summary_message] + self.conversation_history[20:]
        self._last_summary_at = 1  # Summary is now at position 0
```

**Impact**: Never lose important context!

---

### Priority 2: Project Brief System (HIGH IMPACT)

#### Implementation
Create `flux/core/project_brief.py`:

```python
@dataclass
class ProjectBrief:
    """Structured state that persists across all conversations."""
    
    # Core identity
    project_name: str
    project_type: str  # "web_app", "cli_tool", "api", etc.
    description: str
    
    # Tech stack
    languages: List[str]
    frameworks: List[str]
    database: Optional[str]
    
    # Constraints & Conventions
    constraints: List[str]  # ["Never change API contracts", ...]
    coding_style: List[str]  # ["Use TypeScript", "Always use async/await"]
    api_format: Optional[str]  # "{ success, data, error }"
    
    # Architecture
    key_directories: Dict[str, str]  # {"src/": "main code", "tests/": "tests"}
    architecture_notes: List[str]
    
    # Current state
    current_task: Optional[str]
    completed_tasks: List[str]
    pending_issues: List[str]
    
    def to_prompt(self) -> str:
        """Convert to structured prompt that's ALWAYS sent."""
        return f"""
PROJECT BRIEF (READ FIRST - ALWAYS FOLLOW):
---
Name: {self.project_name}
Type: {self.project_type}
Description: {self.description}

Stack: {", ".join(self.frameworks)}
Languages: {", ".join(self.languages)}
Database: {self.database or "None"}

CRITICAL CONSTRAINTS:
{chr(10).join(f"  - {c}" for c in self.constraints)}

Coding Style:
{chr(10).join(f"  - {s}" for s in self.coding_style)}

Current Task: {self.current_task or "None"}
---
"""
    
    def save(self, path: Path):
        """Save to ~/.flux/projects/{project_name}/brief.json"""
        
    @classmethod
    def load(cls, project_path: Path) -> "ProjectBrief":
        """Load from disk"""
```

#### Integration
In `conversation_manager.py` `_build_system_prompt()`:
```python
def _build_system_prompt(self, query: Optional[str] = None) -> str:
    prompt = get_system_prompt(self.cli.config.model)
    
    # ALWAYS include project brief (never drops off)
    if self.cli.project_brief:
        prompt += "\n\n" + self.cli.project_brief.to_prompt()
    
    # ... rest of prompt ...
    return prompt
```

**Impact**: Core constraints NEVER get lost!

---

### Priority 3: Persistent State File (MEDIUM IMPACT)

#### Implementation
Store conversation in `~/.flux/projects/{project_name}/conversation.json`:

```json
{
  "project_brief": { ... },
  "conversation_summaries": [
    "Summary of messages 1-20: ...",
    "Summary of messages 21-40: ..."
  ],
  "recent_messages": [
    /* Last 10 messages */
  ],
  "last_updated": "2025-11-14T09:00:00Z"
}
```

#### Integration
In `cli.py` startup:
```python
# Load conversation state on startup
conversation_file = self.flux_dir / "projects" / self.project_name / "conversation.json"
if conversation_file.exists():
    state = json.loads(conversation_file.read_text())
    self.project_brief = ProjectBrief.from_dict(state["project_brief"])
    self.conversation_summaries = state["conversation_summaries"]
    self.llm.conversation_history = state["recent_messages"]
    console.print("[dim]✓ Loaded previous conversation state[/dim]")
```

**Impact**: Context persists across sessions!

---

## Proposed File Structure

```
flux/core/
  conversation_summarizer.py     # NEW: Summarizes old messages
  project_brief.py                # NEW: Structured project state
  conversation_state.py           # NEW: Persistent state manager

~/.flux/
  projects/
    my-todo-app/
      brief.json                  # Project identity & constraints
      conversation.json           # Conversation state
      summaries.json              # Historical summaries
      knowledge_graph.pkl         # Existing smart context
```

---

## Implementation Plan

### Phase 1: Project Brief (2-3 hours)
1. Create `project_brief.py` with ProjectBrief dataclass
2. Add auto-detection from README/package.json
3. Integrate into system prompt (always sent)
4. Add `/brief` command to view/edit

### Phase 2: Summarization (3-4 hours)
1. Create `conversation_summarizer.py`
2. Implement chunk summarization
3. Integrate into context pruning
4. Test with long conversations

### Phase 3: Persistence (2 hours)
1. Create `conversation_state.py`
2. Save state after each message
3. Load state on startup
4. Add `/state` command to inspect

### Phase 4: UI/Commands (1 hour)
1. `/brief` - Show/edit project brief
2. `/brief set constraint "Never use var"`
3. `/state` - Show conversation state
4. `/summarize` - Force summarize now
5. `/clear-but-keep-brief` - Clear messages, keep brief

---

## Example: Before vs After

### Before (Current)
```
Session 1:
User: "Build a todo app with React"
Flux: [remembers]
... 15 messages ...
Flux: ✅ Working great

Session 2 (restart):
User: "Add task filtering"
Flux: "What app are you building?" ❌

Long session:
... 30 messages ...
Flux: Forgets initial constraints ❌
Flux: Uses different API format ❌
```

### After (With Improvements)
```
Session 1:
User: "Build a todo app with React"
Flux: [creates project brief]
Brief saved: Todo app, React/Express, MongoDB
... 15 messages ...
Flux: ✅ Working great
[Conversation saved to disk]

Session 2 (restart):
[Loads conversation + brief]
User: "Add task filtering"
Flux: "I'll add filtering to the todo app" ✅

Long session:
... 30 messages ...
[Messages 1-20 summarized]
Flux: Still remembers all constraints ✅
Flux: Uses correct API format ✅
Brief: ALWAYS in system prompt ✅
```

---

## Metrics to Track

After implementation, measure:
1. **Context retention**: Does Flux remember initial constraints after 50 messages?
2. **Restart recovery**: Can Flux continue after terminal restart?
3. **Token efficiency**: Are we using fewer tokens with summarization?
4. **User satisfaction**: Do users report "forgetting" issues?

---

## Quick Wins (Can Do Today)

### 1. Add Project Memo Command
```bash
flux set-memo "
Project: GSM Grading App
Stack: Next.js 15, Express, MongoDB
Constraints:
- Never change API contracts
- Always return full file contents
- Use TypeScript strict mode
"
```

Stores in `~/.flux/project-memo.txt`, always included in prompt.

### 2. Better Context Pruning
Modify existing pruning to keep:
- First 2 messages (project setup)
- Last 10 messages (recent context)
- Drop middle messages

### 3. Summarize Command
```bash
flux /summarize
```
Manually trigger summarization of conversation so far.

---

## Comparison to Brief's Advice

| Brief Recommendation | Flux Status | Action |
|---------------------|-------------|---------|
| Use summarization | ❌ Missing | **Implement** (Priority 1) |
| Persistent state file | ❌ Missing | **Implement** (Priority 3) |
| Structured state object | ⚠️ Partial | **Enhance** with ProjectBrief |
| Pin important context | ⚠️ Partial | **Fix** with brief system |
| Conversation manager | ✅ Has | ✓ Good foundation |

---

## Next Steps

**Immediate** (Today):
1. Create `project_brief.py`
2. Integrate into system prompt
3. Test with long conversation

**Short-term** (This Week):
1. Implement summarization
2. Add persistence
3. Create user commands

**Long-term** (Next Sprint):
1. Auto-detect project type
2. Smart constraint extraction
3. Multi-project management

---

## Code Skeleton to Start

I can implement this right now! Want me to:
1. ✅ Create `ProjectBrief` class
2. ✅ Integrate into system prompt
3. ✅ Add save/load persistence
4. ✅ Create `/brief` command

This will solve 70% of the "forgetting" problem immediately!

---

## Summary

**The Problem**: Flux drops old messages and forgets context.

**The Solution**:
1. **Summarize** old messages instead of dropping them
2. **Pin** critical info in a ProjectBrief
3. **Persist** state across sessions

**Impact**: Flux will remember:
- ✅ What you're building
- ✅ Initial constraints
- ✅ Architecture decisions
- ✅ Coding conventions

Even after 100 messages or restarting terminal!

**Ready to implement?** Say the word! 🚀
