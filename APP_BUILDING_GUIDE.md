# 🏗️ Flux: Your App-Building Assistant

## Primary Purpose

Flux is designed to **understand and help build entire applications**, not just edit individual files. It maintains a complete semantic understanding of your codebase.

---

## Core Capabilities

### 1. 🧠 Complete Codebase Understanding

Flux automatically builds a **knowledge graph** of your entire application:
- **File relationships**: Understands which files depend on each other
- **Import chains**: Tracks all imports and exports  
- **Entity mapping**: Knows every function, class, and variable
- **Architecture detection**: Identifies patterns (React, FastAPI, etc.)
- **Dependency graph**: Visualizes how everything connects

**Example queries**:
```
"Explain how this application works"
"Show me the architecture of this project"
"What does the user authentication flow look like?"
"How do these components connect?"
```

---

### 2. 🔍 Smart Context Discovery

When you ask about code, Flux **automatically finds all related files**:

**You ask**: "Fix the login bug"
**Flux automatically finds**:
- `auth/login.py` (main login logic)
- `models/user.py` (User model used by login)
- `routes/auth_routes.py` (API endpoint that calls login)
- `middleware/session.py` (session handling)
- `tests/test_auth.py` (relevant tests)

It knows what's related **without you telling it**.

---

### 3. 📊 Project Intelligence

Flux maintains awareness of:
- **Hot files**: Most frequently modified files
- **Critical paths**: Core functionality  
- **Test coverage**: What has tests, what doesn't
- **Import patterns**: How modules connect
- **Architecture layers**: Frontend, backend, database, etc.

---

## How to Use Flux for App Building

### Starting a New Feature

```
"I need to add user profile editing to this app"
```

**Flux will**:
1. Understand your current app architecture
2. Find all relevant user/profile code
3. Identify what files need changes
4. Suggest the implementation approach
5. Make coordinated changes across multiple files
6. Update tests

---

### Understanding Existing Code

```
"How does the payment processing work in this app?"
```

**Flux will**:
1. Find all payment-related files
2. Trace the flow from API → logic → database
3. Explain the architecture
4. Show you the key functions
5. Identify external dependencies (Stripe, etc.)

---

### Debugging Across Files

```
"The shopping cart total is wrong"
```

**Flux will**:
1. Find cart-related code
2. Trace calculation logic across files
3. Check database models
4. Look at related frontend code
5. Identify the bug
6. Fix it everywhere needed

---

### Refactoring

```
"This authentication code is messy, refactor it"
```

**Flux will**:
1. Understand current auth flow
2. Identify all places auth is used
3. Design cleaner architecture
4. Make coordinated changes
5. Ensure nothing breaks
6. Update imports everywhere

---

## Best Practices

### ✅ DO: Ask Big-Picture Questions

**Good**:
- "How should I architect user permissions?"
- "Add real-time notifications to this app"
- "What's the best way to handle file uploads?"
- "Refactor the API layer for better testability"

**Bad**:
- "Change line 42 in file.py"
- "Add a semicolon here"

Flux excels at **application-level thinking**, not tiny edits.

---

### ✅ DO: Let Flux Find Context

**Don't say**: "Edit files A, B, and C to fix X"
**Instead say**: "Fix X"

Flux will automatically find A, B, C, D, and E if they're all related.

---

### ✅ DO: Think in Features

**Good**:
- "Add user authentication"
- "Implement search functionality"
- "Add pagination to the blog"

**Bad**:
- "Write a function"
- "Create a file"

Flux understands **features**, not just individual code snippets.

---

### ✅ DO: Ask for Explanations

Before making changes, ask:
- "Explain how this works"
- "Show me the architecture"
- "What would break if I change X?"

Flux can map out the entire system for you.

---

## Powerful Commands

### Architecture Analysis
```
"Map out the architecture of this project"
"Show me how the frontend connects to the backend"
"What design patterns are used here?"
```

### Impact Analysis
```
"What files would be affected if I change the User model?"
"What breaks if I remove this function?"
"Show me everything that depends on this module"
```

### Feature Development
```
"Add [feature] to this app"
"Implement [functionality]"
"Build a [component/system]"
```

### Code Quality
```
"Find code that needs refactoring"
"Where should I add error handling?"
"What's missing test coverage?"
```

### Documentation
```
"Explain this codebase to a new developer"
"Document the API endpoints"
"Create a README for this project"
```

---

## How Flux Thinks

### 1. Understand First
When you ask something, Flux:
- Builds a mental model of your app
- Identifies relevant code
- Understands dependencies
- Considers impacts

### 2. Plan Holistically
- Thinks about the entire feature, not just one file
- Considers database, backend, frontend together
- Plans tests alongside implementation
- Thinks about edge cases

### 3. Execute Systematically
- Makes changes in logical order
- Updates all related files
- Keeps imports/types in sync
- Verifies nothing breaks

---

## Current Codebase Graph

Flux builds this automatically on first use:
```
✅ Loaded cached graph: 18 files, 54 entities
```

This means Flux knows about:
- **18 files** in your project
- **54 entities** (functions, classes, variables)
- All connections between them

---

## Commands for Codebase Intelligence

### Explore
```
flux graph --format=json    # See the complete graph
flux find [pattern]          # Find files by pattern  
flux grep [pattern]          # Search code content
```

### Understand
```
"Show me the architecture"
"List all API endpoints"
"What frameworks are used?"
```

### Navigate
```
"What files does X depend on?"
"What depends on file Y?"
"Trace the flow from A to B"
```

---

## Integration with Your Workflow

### During Development
- **Before coding**: "How should I implement X?"
- **While coding**: "Does this break anything?"
- **After coding**: "Review my changes"

### During Debugging
- **Start broad**: "The feature X is broken"
- **Let Flux narrow**: It will find the bug
- **Verify**: "Did that fix it?"

### During Refactoring
- **Explain goal**: "Make the auth code cleaner"
- **Let Flux plan**: It will design the refactor
- **Review changes**: Check the multi-file changes
- **Run tests**: Verify nothing broke

---

## Example Session

```bash
$ flux

→ Explain how this application works

[Flux reads multiple files, builds understanding]

This is a FastAPI application with:
- REST API backend (flux/api/)
- CLI interface (flux/ui/)
- Tool system for file operations
- LLM provider abstraction (Anthropic/OpenAI)

The architecture follows a clean separation:
- Core business logic in flux/core/
- Tools in flux/tools/
- UI layer in flux/ui/
- Provider interfaces in flux/llm/

[Shows dependency graph, key files, flow]

→ Add input validation to all API endpoints

[Flux identifies all endpoints, adds validation systematically]

→ Run the tests

[Verifies everything still works]
```

---

## Tips for Maximum Effectiveness

### 1. **Start with Understanding**
Always ask Flux to explain first before making changes.

### 2. **Be Feature-Oriented**
Think in terms of user-facing features, not implementation details.

### 3. **Trust the Context Discovery**
Don't micromanage which files to edit. Let Flux find them.

### 4. **Verify with Tests**
After changes, always run tests or ask Flux to verify.

### 5. **Iterate Conversationally**
Flux remembers the conversation context. Build on previous exchanges.

---

## What Flux Can Build

- ✅ Full-stack web applications
- ✅ REST APIs and GraphQL servers
- ✅ CLI tools and scripts
- ✅ Desktop applications (Electron, etc.)
- ✅ Mobile app backends
- ✅ Data processing pipelines
- ✅ Microservices
- ✅ Testing frameworks
- ✅ DevOps automation

---

## What Makes Flux Different

### Traditional Approach:
1. You: "Edit file.py line 42"
2. AI: Makes that one edit
3. You: "Now edit other_file.py line 15"
4. You: "Now update the tests"
5. (Repeat 20 times...)

### Flux Approach:
1. You: "Add user authentication"
2. Flux: 
   - Understands your app
   - Finds all relevant files
   - Makes coordinated changes
   - Updates tests
   - Done.

**Flux thinks like a senior developer who understands the whole system.**

---

## Current Limitations

With your current setup (GPT/OpenAI with 50 RPM limit):
- Rate limits may slow down large refactors
- Complex multi-file changes may need retries
- Consider upgrading OpenAI tier for production use

**Workaround**: Flux now auto-retries on rate limits with exponential backoff.

---

## Next Steps

1. **Try it**: Ask Flux to explain your current project
2. **Build something**: Add a new feature
3. **Refactor**: Clean up messy code
4. **Learn**: Ask Flux to teach you the codebase

Flux is designed to be your **pair programming partner** that understands the entire application.

---

## Philosophy

> "The best code assistant doesn't just edit files—it understands your entire application and helps you build it."

Flux is not a text editor. It's an **application-building partner**.
