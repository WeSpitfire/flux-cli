# Flux Documentation Structure

**Last Updated:** 2025-11-03

This document describes the organization of Flux documentation after the major reorganization from 82+ scattered files into a clean, maintainable structure.

---

## 📁 Directory Structure

```
docs/
├── README.md                          # Main project documentation
├── QUICKSTART.md                      # Quick start guide  
├── USER_GUIDE.md                      # Comprehensive user manual
├── TROUBLESHOOTING.md                 # Common issues and solutions
├── QUICK_REFERENCE.md                 # Command quick reference
├── DOC_AUDIT.md                       # Documentation audit plan (historical)
│
├── guides/                            # 🎓 User Guides (11 files)
│   ├── AUTO_FIX_MODE.md              # Auto-fix feature guide
│   ├── TEST_DRIVEN_WORKFLOW.md       # Test workflow guide
│   ├── multi-provider-guide.md       # LLM provider setup
│   ├── editing-strategy-guidelines.md
│   ├── automatic-validation.md
│   ├── dogfooding-insights.md
│   ├── MAX_HISTORY_FEATURE.md
│   ├── SMART_BACKGROUND_PROCESSING.md
│   ├── SMART_RELIABILITY.md
│   ├── UNDO_SUMMARY.md
│   └── WORKFLOW_ENFORCEMENT.md
│
├── architecture/                      # 🏗️ System Design (8 files)
│   ├── TOP_3_FEATURES.md             # Session persistence, monitoring, workflows
│   ├── ORCHESTRATION_COMPLETE.md     # AI orchestration system
│   ├── DESKTOP_APP.md                # Electron desktop app
│   ├── FLUX_REIMAGINED.md            # Product vision
│   ├── MEMORY_SYSTEM.md              # Context management
│   ├── AST_EDITING.md                # Code editing approach
│   ├── SMART_CONTEXT_SPEC.md         # Smart context system
│   └── VALIDATION_FRAMEWORK.md       # Validation architecture
│
├── development/                       # 🔧 Developer Docs (4 files)
│   ├── DEBUGGING_FLUX.md             # Debug guide
│   ├── DEBUG_QUICK_REFERENCE.md      # Debug commands
│   ├── DEBUG_SYSTEM_SUMMARY.md       # Debug system overview
│   └── AI-SAFETY-GUIDELINES.md       # AI safety guidelines
│
├── features/                          # 🎨 Feature Docs
│   └── typing-indicator.md           # Typing indicator feature
│
└── archive/                           # 📦 Historical Docs (49 files)
    ├── sessions/                      # Work logs & session summaries (10)
    ├── implementations/               # Completed implementations (28)
    ├── testing/                       # Old test results (6)
    └── bugfixes/                      # Specific bug fixes (5)
```

---

## 📖 Core Documentation (Root)

### For Users
- **README.md** - Main project documentation, features, installation
- **QUICKSTART.md** - Get started in 5 minutes
- **USER_GUIDE.md** - Comprehensive guide to all features
- **TROUBLESHOOTING.md** - Common issues and how to fix them
- **QUICK_REFERENCE.md** - Command reference cheat sheet

---

## 🎓 User Guides (`/guides`)

### Feature Guides
- **AUTO_FIX_MODE.md** - Using auto-fix to format code automatically
- **TEST_DRIVEN_WORKFLOW.md** - Test-driven development with Flux
- **SMART_BACKGROUND_PROCESSING.md** - Background processing features
- **SMART_RELIABILITY.md** - Reliability and error handling
- **UNDO_SUMMARY.md** - Undo/redo functionality
- **WORKFLOW_ENFORCEMENT.md** - Workflow system (NEW)
- **MAX_HISTORY_FEATURE.md** - Conversation history limits

### Setup & Configuration
- **multi-provider-guide.md** - Configure OpenAI, Anthropic, local LLMs
- **automatic-validation.md** - Validation system configuration

### Best Practices
- **editing-strategy-guidelines.md** - Code editing best practices
- **dogfooding-insights.md** - Insights from using Flux daily

---

## 🏗️ Architecture (`/architecture`)

### System Design
- **TOP_3_FEATURES.md** ⭐ - NEW: Session persistence, proactive monitoring, workflows
  - Complete implementation details
  - Usage examples
  - Integration guide

- **ORCHESTRATION_COMPLETE.md** - AI orchestration layer
  - Natural language command handling
  - Tool registry
  - Multi-step workflows

- **DESKTOP_APP.md** - Electron desktop application
  - Architecture
  - IPC communication
  - Desktop-specific features

- **FLUX_REIMAGINED.md** - Product vision and roadmap
  - Future direction
  - "Invisible Flux" concept
  - User experience goals

### Core Systems
- **MEMORY_SYSTEM.md** - Context management and memory
- **SMART_CONTEXT_SPEC.md** - Smart context selection
- **AST_EDITING.md** - Abstract syntax tree-based editing
- **VALIDATION_FRAMEWORK.md** - Validation and testing framework

---

## 🔧 Development (`/development`)

### Debugging
- **DEBUGGING_FLUX.md** - Complete debugging guide
  - Common issues
  - Debug techniques
  - Log analysis

- **DEBUG_QUICK_REFERENCE.md** - Quick debug command reference
- **DEBUG_SYSTEM_SUMMARY.md** - Debug system architecture

### Guidelines
- **AI-SAFETY-GUIDELINES.md** - AI safety and security guidelines

---

## 📦 Archive (`/archive`)

Historical documentation kept for reference but not actively maintained.

### `/archive/sessions` (10 files)
Work logs and session summaries:
- session-summary-2025-11-01.md
- SESSION_SUMMARY.md
- FINAL_SESSION_SUMMARY.md
- WEEK2_COMPLETE.md
- WEEK3_PROGRESS.md
- TODAYS_IMPROVEMENTS.md
- etc.

### `/archive/implementations` (28 files)
Completed implementation documentation:
- ORCHESTRATION_COMPLETE.md (superseded by TOP_3_FEATURES.md)
- multi-provider-implementation-complete.md
- PASTE_MODE_IMPLEMENTATION.md
- MULTILINE_INPUT_SOLUTION.md
- CHANGE_PREVIEW_COMPLETE.md
- IMPROVEMENTS.md
- PRODUCTION_READY.md
- etc.

### `/archive/testing` (6 files)
Old test results:
- TEST_RESULTS.md
- RELIABILITY_TEST_RESULTS.md
- WORKFLOW_TEST_RESULTS.md
- DEMO_RESULTS.md
- test-clear-results.md
- test-history-failure-analysis.md

### `/archive/bugfixes` (5 files)
Specific bug fix documentation:
- BUGFIX_PATH_HANDLING.md
- openai-400-fix.md
- sonnet-access-issue.md
- CRITICAL_ISSUES.md
- DEBUG_ANALYSIS_MULTILINE_FIX.md

---

## 🎯 Documentation Principles

### Active Documentation
Files in root, `/guides`, `/architecture`, and `/development` are:
- ✅ Currently accurate
- ✅ Actively maintained
- ✅ Referenced by users and developers
- ✅ Updated with new features

### Archived Documentation
Files in `/archive` are:
- 📦 Historical record
- 📦 Not updated with new features
- 📦 Kept for reference and learning
- 📦 May contain outdated information

---

## 🚀 Finding Documentation

### I want to...
- **Get started** → `QUICKSTART.md`
- **Learn all features** → `USER_GUIDE.md`
- **Fix a problem** → `TROUBLESHOOTING.md`
- **Look up a command** → `QUICK_REFERENCE.md`
- **Configure LLM providers** → `guides/multi-provider-guide.md`
- **Use auto-fix** → `guides/AUTO_FIX_MODE.md`
- **Understand architecture** → `architecture/TOP_3_FEATURES.md`
- **Debug Flux** → `development/DEBUGGING_FLUX.md`
- **Contribute** → `development/` (CONTRIBUTING.md - TODO)

---

## 📝 Maintenance

### Adding New Documentation
1. **User guides** → `/guides`
2. **Architecture/design** → `/architecture`
3. **Developer docs** → `/development`
4. **Core docs** → Root only if essential

### Updating Documentation
- Update core docs when adding features
- Keep architecture docs in sync with code
- Archive old implementation notes after completion

### Archiving Documentation
When a doc becomes historical:
```bash
git mv docs/OLD_DOC.md docs/archive/implementations/
```

---

## 📊 Documentation Stats

**Total files:** 82 → **Organized into:**
- Core (6 root files)
- Guides (11 files)
- Architecture (8 files)
- Development (4 files)
- Features (1 file)
- Archive (49 files)
- Support (3 files: DOC_AUDIT.md, this file, etc.)

**Deleted:** 5 obsolete task files

**Result:** Clean, navigable structure that scales as project grows

---

## 🔄 Recent Changes

### 2025-11-03 - Major Reorganization
- Created structured folders (guides, architecture, development, archive)
- Archived 49 historical documents
- Deleted 5 obsolete task files
- Organized 28 active docs by category
- Created this structure document

### Key Improvements
✅ Clear separation of user vs developer docs
✅ Historical docs archived but accessible
✅ Easy to find relevant documentation
✅ Scales well as project grows
✅ Reduced clutter in root directory

---

## 📌 TODO

Remaining documentation work:
- [ ] Update README.md with new structure
- [ ] Update core docs with latest features
- [ ] Create CONTRIBUTING.md
- [ ] Create testing.md guide
- [ ] Validate all internal links
- [ ] Create ROADMAP.md (consolidate improvement docs)

---

For questions about documentation structure, see `DOC_AUDIT.md` for the detailed audit and reorganization plan.
