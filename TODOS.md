# Flux Todo Manager

Warp-style intelligent todo tracking for Flux CLI. Automatically creates and tracks todos for complex tasks.

## Features

- **Automatic Todo Creation**: When Flux detects a complex task, it automatically breaks it down into todos
- **Progress Tracking**: See real-time progress as todos are completed
- **Session Persistence**: Todos are saved and restored across CLI sessions
- **Manual Management**: Add, complete, and manage todos manually
- **Visual Feedback**: Clean, emoji-based display with status indicators

## How It Works

### Automatic Todos

When you give Flux a complex query, the Task Planner automatically:
1. Analyzes the complexity
2. Breaks it into steps
3. Creates a todo list
4. Tracks progress as each step completes

**Example:**
```bash
flux> Build a login component with validation and tests

🧠 Analyzing and planning execution...

📋 Created 5 todos for tracking

📋 Build a login component with validation and tests
Progress: 0/5 (0%)

○ 1. 🟠 Read existing authentication patterns
   Understand current auth implementation before creating new component

○ 2. Create LoginForm component with email/password fields
   Implement component structure with React hooks

○ 3. Add form validation for email and password
   Use validation library to enforce rules

○ 4. Implement authentication logic and API integration
   Connect to backend auth endpoint

○ 5. Write unit tests for LoginForm component
   Test validation and authentication flows
```

### Manual Todo Commands

#### View Todos
```bash
/todos
```
Shows the current todo list with progress.

#### Add Todo
```bash
/todo add <title> [description]
```
Manually add a todo item.

**Example:**
```bash
/todo add "Review PR #123" This is high priority
```

#### Mark Todo as Done
```bash
/todo done <number>
```
Mark a todo as completed by its number.

**Example:**
```bash
/todo done 3
```

#### Clear All Todos
```bash
/todo clear
```
Removes all todos from the current list.

## Todo States

- **○ Pending** (white): Not yet started
- **○ In Progress** (yellow): Currently being worked on
- **✓ Completed** (green): Successfully completed
- **✗ Failed** (red): Failed with error

## Priority Indicators

- **🔴 Critical**: Highest priority
- **🟠 High**: High priority
- (no indicator): Medium/Low priority

## Progress Display

After each completed todo:
```
✓ Step 3 completed
Progress: 3/5 (60%)
```

When all todos are complete:
```
🎉 All todos completed!
```

## Architecture

### Core Components

1. **TodoManager** (`flux/core/todo_manager.py`)
   - Manages todo state and persistence
   - Provides todo CRUD operations
   - Formats display output

2. **Integration** (`flux/core/workflow_coordinator.py`)
   - Connects TodoManager to TaskPlanner
   - Automatically creates todos from task plans
   - Updates todo status during execution

3. **CLI Commands** (`flux/commands/todos.py`)
   - Provides user-facing todo commands
   - Handles manual todo management

### Data Model

```python
TodoItem:
  - id: str
  - title: str
  - description: str
  - status: TodoStatus (pending, in_progress, completed, failed)
  - priority: TodoPriority (low, medium, high, critical)
  - created_at: datetime
  - completed_at: Optional[datetime]
  - related_files: List[str]
  - notes: List[str]

TodoList:
  - id: str
  - goal: str
  - todos: List[TodoItem]
  - created_at: datetime
  - completed_at: Optional[datetime]
```

### Persistence

Todos are automatically saved to `~/.flux/todos.json` and restored when you restart Flux.

## Comparison to Warp

Like Warp's todo system, Flux TodoManager:
- ✅ Automatically creates todos from complex queries
- ✅ Shows progress with visual indicators
- ✅ Persists across sessions
- ✅ Provides manual management commands
- ✅ Integrates seamlessly into workflow

Flux-specific enhancements:
- 🎯 Integrates with AI task planning
- 🔄 Auto-updates status based on tool execution
- 📊 Priority-based todo ordering
- 🗂️ File relationship tracking
- 📝 Notes and failure reasons

## Future Enhancements

- [ ] Desktop UI panel in Electron app
- [ ] Todo dependencies (blocking tasks)
- [ ] Time estimates and tracking
- [ ] Sub-todos (nested tasks)
- [ ] Todo templates for common workflows
- [ ] Export/import todo lists
- [ ] Integration with GitHub Issues
- [ ] Smart todo suggestions based on context

## Examples

### Complex Feature Development
```bash
flux> Add a user profile page with avatar upload and bio editing

📋 Add a user profile page with avatar upload and bio editing
Progress: 0/7 (0%)

○ 1. 🟠 Read existing user model and profile schemas
○ 2. Create ProfilePage component structure
○ 3. Implement avatar upload with preview
○ 4. Add bio editing with character limit
○ 5. Create API endpoints for profile updates
○ 6. Write integration tests
○ 7. Update navigation to include profile link
```

### Bug Fix with Tests
```bash
flux> Fix the validation bug in SignupForm and add tests

📋 Fix the validation bug in SignupForm and add tests
Progress: 0/4 (0%)

○ 1. 🟠 Read SignupForm component code
○ 2. Identify and fix validation logic bug
○ 3. Write unit tests for validation
○ 4. Run tests to verify fix
```

### Manual Todo Management
```bash
/todo add "Refactor database queries" Need to optimize N+1 queries

/todos
📋 Current session
Progress: 0/1 (0%)

○ 1. Refactor database queries
   Need to optimize N+1 queries

/todo done 1
✓ Marked as done: Refactor database queries

🎉 All todos completed!
```

## Tips

1. **Let Flux Create Todos**: For complex tasks, let the Task Planner create todos automatically
2. **Check Progress Often**: Use `/todos` to see your progress
3. **Manual for Ad-Hoc Tasks**: Use `/todo add` for quick reminders
4. **Clear When Done**: Use `/todo clear` to start fresh on a new task
5. **Todos Persist**: Your todos will be there when you restart Flux

## Getting Help

```bash
/help        # General help
/todos       # Show current todos
/todo        # Show todo management help
```
