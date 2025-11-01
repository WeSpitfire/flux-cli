# Flux CLI

An AI-powered development assistant CLI tool with advanced code understanding, editing capabilities, and built-in safety features.

## 🛡️ Safety First

Flux is designed with multiple layers of protection:
- **Workflow Enforcement** - Must understand code before modifying it
- **Auto-Rollback** - Automatically reverts syntax-breaking changes
- **Interactive Approval** - You approve every file modification
- **Undo Support** - All operations can be reversed

## Vision

Flux aims to be an open-source alternative to AI-powered development tools, with improvements:
- AST-aware code editing using tree-sitter
- Intelligent context management with code graphs
- Semantic search with vector embeddings
- Multi-file refactoring capabilities
- Local and cloud LLM support

## Current Status: MVP Development

### Phase 1 Features (✅ COMPLETE!)
- [x] Project structure
- [x] LLM integration (Claude API)
- [x] File operations (read/write/edit)
- [x] **AST-aware code editing** 🌟
- [x] **Persistent memory system** 🧠
- [x] **Diff previews** 📋
- [x] **Project detection** 🎯
- [x] Command execution
- [x] Fast code search (grep)
- [x] File finding and listing
- [x] Interactive TUI
- [x] Conversation management
- [x] Token usage tracking
- [x] **Workflow enforcement** 🛡️ NEW!
- [x] **Auto-rollback on syntax errors** 🔄 NEW!
- [x] **Interactive approval system** ✅ NEW!

## Architecture

```
flux-cli/
├── flux/                  # Core package
│   ├── llm/              # LLM client & prompts
│   ├── tools/            # Tool system & implementations
│   ├── search/           # Codebase indexing & search
│   ├── ui/               # CLI/TUI interface
│   └── core/             # Context & state management
├── tests/                # Test suite
└── main.py               # Entry point
```

## Quick Start

```bash
# Setup
git clone <repo>
cd flux-cli
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Run
python flux/main.py
```

## Usage

```bash
# Interactive mode
python flux/main.py

# Single command
python flux/main.py "Add error handling to api.py"

# Auto-approve mode (skip approval prompts)
python flux/main.py --yes "Refactor the auth module"

# Get help
python flux/main.py
/help
```

## Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python main.py
```

## Tech Stack

- **Python 3.11+**: Core language
- **Anthropic Claude**: LLM backend
- **ChromaDB**: Vector database for semantic search
- **tree-sitter**: AST parsing
- **Rich**: Terminal UI
- **sentence-transformers**: Code embeddings

## Roadmap

### Phase 1: MVP (Weeks 1-6)
- Basic LLM integration
- File CRUD operations
- Command execution
- Simple semantic search
- Interactive CLI

### Phase 2: Advanced Features (Weeks 7-12)
- AST-aware editing
- Code graph understanding
- Multi-file refactoring
- Git integration
- Test generation mode

### Phase 3: Polish (Weeks 13-16)
- Performance optimization
- Local model support
- Plugin system
- VS Code extension
- Documentation

## 📚 Documentation

### User Guides
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user guide with examples ⭐
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Daily use reference card
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide

### Technical Documentation  
- **[WORKFLOW_ENFORCEMENT.md](WORKFLOW_ENFORCEMENT.md)** - Safety system details
- **[AST_EDITING.md](AST_EDITING.md)** - AST editing complete guide
- **[MEMORY_SYSTEM.md](MEMORY_SYSTEM.md)** - Memory system guide

### Development
- **[IMPROVEMENTS_PROGRESS.md](IMPROVEMENTS_PROGRESS.md)** - Current improvement status
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - Feature enhancements log
- **[FINAL_SUMMARY.md](FINAL_SUMMARY.md)** - Complete feature summary
- **[COMPLETE.md](COMPLETE.md)** - Ultimate project summary

## License

MIT
