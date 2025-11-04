# Flux CLI

An intelligent AI-powered development assistant that works like a senior engineer pair-programming with you 24/7.

## ✨ What Makes Flux Special

Flux isn't just another AI coding tool—it's designed to **disappear into your workflow** while making you dramatically more productive:

- 🧠 **Persistent Memory** - Remembers your work across sessions, no re-explaining needed
- 🔔 **Proactive Monitoring** - Watches tests/builds in background, alerts you instantly when things break
- ⚡ **One-Command Workflows** - `deploy-staging` runs tests, builds, deploys, verifies—all automatically
- 🤖 **AI Orchestration** - Natural language commands without manual tool selection
- 🖥️ **Desktop App** - Beautiful Electron UI with real-time streaming
- 🛡️ **Safety First** - Auto-rollback, interactive approval, undo support

## 🚀 Core Features

### 🧠 Session Persistence & Context Memory
Never lose your place. Flux remembers:
- What you were working on
- Which files you've edited
- Test status and recent errors
- Full conversation history

**Example:**
```
$ flux
📂 Resuming session from 2 hours ago

🎯 Last task: Debugging login authentication  
📝 Working on: auth.py, login_tests.py, utils.py
❌ Tests: 3 failing

⚠️  Recent errors:
  • ImportError: Cannot import 'validate_token'
  • AssertionError: Expected 200, got 401
```

### 🔔 Proactive Monitoring
Stop asking "did tests pass?"—Flux tells you automatically:
- **Test Monitor** - Alerts when tests break (with AI analysis)
- **Build Monitor** - Detects build failures instantly  
- **Lint Monitor** - Notifies about new code issues
- **File Monitor** - Tracks code changes in real-time
- **Git Monitor** - Shows uncommitted changes

**Example:**
```
(You edit auth.py)

============================================================
❌ Tests are now failing!
============================================================

🤖 AI Analysis:
Tests failed due to missing import. The validate_token
function was moved to utils.py but the import wasn't updated.

Failed tests:
  • FAILED tests/test_auth.py::test_login - ImportError
============================================================
```

### ⚡ One-Command Workflows
Define complex workflows once, run them forever:

```yaml
# .flux/workflows.yaml
deploy-staging:
  steps:
    - run_tests
    - build  
    - deploy
    - verify
    - notify
```

Then just: `flux workflow deploy-staging` → Done!

**Built-in workflows:**
- `deploy-staging` - Tests → Build → Deploy → Verify
- `pr-ready` - Format → Lint → Tests → Commit
- `quick-check` - Format → Tests

### 🤖 AI Orchestration
Natural language commands without manual tool selection:

```
You: "run the tests"
Flux: ✓ Running tests...
      ✓ 15 passed

You: "fix the formatting"
Flux: ✓ Auto-fixing code...
      ✓ Fixed 7 issues in 3 files

You: "deploy to staging"  
Flux: ✓ Running tests... passed
      ✓ Building... done
      ✓ Deploying... success
      ✓ Verified health check
```

### 🖥️ Desktop App
Electron-based desktop application with:
- Beautiful dark/light themes
- Real-time streaming responses
- Code syntax highlighting
- Markdown rendering
- System tray integration

### 🛡️ Safety & Reliability
- **AST-aware editing** - Understands code structure
- **Auto-rollback** - Reverts syntax-breaking changes
- **Interactive approval** - Review before applying
- **Undo support** - Reverse any operation
- **Workflow enforcement** - Must understand before modifying

## 💻 Architecture

```
flux-cli/
├── flux/
│   ├── core/              # Core systems
│   │   ├── orchestrator.py      # AI orchestration
│   │   ├── session_manager.py   # Session persistence
│   │   ├── proactive_monitor.py # Background monitoring
│   │   └── workflows.py         # Workflow system
│   ├── llm/               # LLM providers (Claude, OpenAI, local)
│   ├── tools/             # Tool implementations
│   ├── search/            # Codebase indexing & vector search
│   └── ui/                # CLI and desktop app
├── desktop-app/         # Electron desktop app
├── tests/               # Test suite
└── docs/                # Documentation
```

## ⚡ Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/flux-cli.git
cd flux-cli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

```bash
# Create config file
cp .env.example .env

# Add your API key(s) - supports multiple providers:
ANTHROPIC_API_KEY=your_key_here    # Claude (recommended)
OPENAI_API_KEY=your_key_here        # GPT-4 (optional)
```

### Running Flux

```bash
# CLI mode
flux

# Desktop app
cd desktop-app
npm install
npm start

# Single command
flux "add error handling to api.py"

# With workflow
flux workflow pr-ready
```

## 📚 Usage Examples

### Natural Language Commands
```bash
flux "run the tests"
flux "fix the formatting issues"
flux "add type hints to the user module"
flux "create a new API endpoint for users"
```

### Interactive Mode
```bash
$ flux
📂 Resuming session from 2 hours ago

> run the tests
✓ Running pytest...
✓ 15 tests passed

> fix any issues
✓ Auto-fixing 3 lint issues...
✓ All fixed

> /workflow pr-ready
✓ Format → Lint → Tests → Commit
✓ Ready for PR!
```

### Custom Workflows
```yaml
# .flux/workflows.yaml
my-deploy:
  description: Deploy with checks
  steps:
    - name: tests
      tool: run_tests
    - name: build  
      command: npm run build
      condition: tests
    - name: deploy
      command: ./deploy.sh production
      condition: build
```

## 🛠️ Tech Stack

### Core
- **Python 3.11+** - Core language
- **SQLite** - Session persistence
- **tree-sitter** - AST-aware code editing
- **Rich** - Beautiful terminal UI

### AI & Search
- **Anthropic Claude** - Primary LLM (Sonnet 4.5)
- **OpenAI GPT-4** - Alternative LLM
- **ChromaDB** - Vector database
- **sentence-transformers** - Code embeddings

### Desktop App
- **Electron** - Cross-platform desktop
- **React** - UI framework  
- **Marked** - Markdown rendering
- **Prism** - Syntax highlighting

### Development
- **pytest** - Testing framework
- **ruff** - Linting and formatting
- **mypy** - Type checking

## 🗺️ Roadmap

### ✅ Completed (v0.1)
- ✓ AI orchestration layer
- ✓ Session persistence system
- ✓ Proactive monitoring
- ✓ Workflow engine
- ✓ Desktop app
- ✓ Multi-provider LLM support
- ✓ AST-aware editing
- ✓ Auto-fix mode
- ✓ Safety systems

### 🔄 In Progress (v0.2)
- □ CLI integration of new features
- □ Notification integrations (Slack, Discord)
- □ Enhanced AI analysis for monitors
- □ Workflow templates library

### 🔮 Planned (v0.3+)
- □ VS Code extension
- □ Plugin system
- □ Local model support (Ollama)
- □ Team collaboration features
- □ Cloud sync for sessions

## 📚 Documentation

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in 5 minutes
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user manual
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command cheat sheet
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues & solutions

### User Guides (`/guides`)
- **[Auto-Fix Mode](guides/AUTO_FIX_MODE.md)** - Automatic code formatting
- **[Test-Driven Workflow](guides/TEST_DRIVEN_WORKFLOW.md)** - TDD with Flux
- **[Multi-Provider Setup](guides/multi-provider-guide.md)** - Configure LLMs
- **[Workflow System](guides/WORKFLOW_ENFORCEMENT.md)** - Custom workflows
- **[Smart Features](guides/)** - Background processing, reliability, undo

### Architecture (`/architecture`)
- **[Top 3 Features](architecture/TOP_3_FEATURES.md)** ⭐ - Session, Monitoring, Workflows
- **[AI Orchestration](architecture/ORCHESTRATION_COMPLETE.md)** - Orchestration layer
- **[Desktop App](architecture/DESKTOP_APP.md)** - Electron app architecture
- **[Product Vision](architecture/FLUX_REIMAGINED.md)** - Future direction
- **[Core Systems](architecture/)** - Memory, AST editing, validation

### Development (`/development`)
- **[Debugging Guide](development/DEBUGGING_FLUX.md)** - Debug Flux itself
- **[Debug Reference](development/DEBUG_QUICK_REFERENCE.md)** - Quick commands
- **[AI Safety](development/AI-SAFETY-GUIDELINES.md)** - Safety guidelines

### More
- **[DOCUMENTATION_STRUCTURE.md](DOCUMENTATION_STRUCTURE.md)** - Doc organization
- **[Archive](archive/)** - Historical documentation

## License

MIT
