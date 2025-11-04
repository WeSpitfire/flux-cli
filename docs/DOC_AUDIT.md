# Documentation Audit & Cleanup Plan

**Total files:** 82 markdown/text files in `/docs`

## Categories

### 📘 Core User Documentation (Keep & Update)
Essential documentation for users:
- `README.md` - Main project documentation
- `QUICKSTART.md` - Getting started guide
- `USER_GUIDE.md` - Comprehensive user manual
- `TROUBLESHOOTING.md` - Common issues and solutions
- `QUICK_REFERENCE.md` - Command quick reference
- `multi-provider-guide.md` - LLM provider setup

**Action:** Update with current features (orchestration, sessions, monitoring, workflows, desktop app)

### 🏗️ Architecture & Design (Keep & Update)
Current system design documentation:
- `TOP_3_FEATURES.md` - NEW - Session, Monitoring, Workflows (KEEP)
- `ORCHESTRATION_COMPLETE.md` - AI orchestration implementation (KEEP)
- `DESKTOP_APP.md` - Electron desktop app (KEEP)
- `FLUX_REIMAGINED.md` - Vision document (KEEP)
- `STRATEGIC_VISION.md` - Product direction (REVIEW & MERGE?)
- `MEMORY_SYSTEM.md` - Context system design (UPDATE)
- `AST_EDITING.md` - Code editing approach (KEEP)
- `SMART_CONTEXT_SPEC.md` - Context management (KEEP)

**Action:** Review for overlap, consolidate where appropriate

### 🔧 Implementation Notes (Archive)
Completed implementation documentation:
- `ORCHESTRATION_COMPLETE.md` - Done, archived
- `multi-provider-implementation-complete.md` - Done
- `IMPROVEMENTS_COMPLETED.md` - Historical
- `PASTE_MODE_IMPLEMENTATION.md` - Done
- `MULTILINE_INPUT_SOLUTION.md` - Done
- `CHANGE_PREVIEW_COMPLETE.md` - Done
- `PHASE_1_COMPLETE.md` - Done
- `OPTION_A_COMPLETE.md` - Done
- `phase1-complete.md` - Done (duplicate?)

**Action:** Move to `docs/archive/implementations/`

### 📝 Session Summaries (Archive)
Historical work logs:
- `session-summary-2025-11-01.md`
- `SESSION_SUMMARY.md`
- `SESSION_COMPLETE.md`
- `FINAL_SESSION_SUMMARY.md`
- `FINAL_SUMMARY.md`
- `WEEK2_COMPLETE.md`
- `WEEK3_PROGRESS.md`
- `WEEK3_TEST_WORKFLOW_COMPLETE.md`
- `TODAYS_IMPROVEMENTS.md`
- `TODAYS_WORK.md`

**Action:** Move to `docs/archive/sessions/`

### 🧪 Test Results (Archive)
Historical test documentation:
- `TEST_RESULTS.md`
- `RELIABILITY_TEST_RESULTS.md`
- `WORKFLOW_TEST_RESULTS.md`
- `DEMO_RESULTS.md`
- `test-clear-results.md`
- `test-history-failure-analysis.md`

**Action:** Move to `docs/archive/testing/`

### 📋 Task Files (Delete)
Temporary task tracking files:
- `ELECTRON_TASK.txt`
- `REAL_WORKFLOW_TASK.txt`
- `SIMPLE_TASK.txt`
- `STREAMING_DIFF_TASK.txt`

**Action:** Delete - no longer needed

### 🔄 Improvement Plans (Review & Consolidate)
Various improvement documentation:
- `IMPROVEMENTS.md`
- `IMPROVEMENTS_PROGRESS.md`
- `IMPROVEMENT_ROADMAP.md`
- `FLUX_IMPROVEMENTS.md`
- `improvement-summary.md`
- `flux-editing-improvements-plan.md`
- `PRODUCTION_READINESS_PLAN.md`
- `PRODUCTION_READY.md`

**Action:** Consolidate into single `ROADMAP.md` or delete if obsolete

### 🐛 Debug Documentation (Keep & Update)
Debugging and development guides:
- `DEBUGGING_FLUX.md` - Debug guide (KEEP & UPDATE)
- `DEBUG_QUICK_REFERENCE.md` - Debug commands (KEEP)
- `DEBUG_SYSTEM_SUMMARY.md` - Debug system overview (KEEP)
- `DEBUG_ANALYSIS_MULTILINE_FIX.md` - Specific fix (ARCHIVE)

**Action:** Keep main guides, archive specific fix documentation

### 🔧 Bug Fixes & Issues (Archive)
Documentation for specific fixes:
- `BUGFIX_PATH_HANDLING.md`
- `openai-400-fix.md`
- `sonnet-access-issue.md`
- `CRITICAL_ISSUES.md`

**Action:** Move to `docs/archive/bugfixes/`

### 📚 Feature Documentation (Review)
Specific feature docs:
- `AUTO_FIX_MODE.md` - Autofix feature (KEEP & UPDATE)
- `TEST_DRIVEN_WORKFLOW.md` - Test workflow (KEEP)
- `SMART_BACKGROUND_PROCESSING.md` - Background processing (KEEP)
- `SMART_RELIABILITY.md` - Reliability features (KEEP)
- `VALIDATION_FRAMEWORK.md` - Validation system (KEEP)
- `WORKFLOW_ENFORCEMENT.md` - Workflow system (MERGE into TOP_3?)
- `MAX_HISTORY_FEATURE.md` - History feature (KEEP)
- `UNDO_SUMMARY.md` - Undo feature (KEEP)
- `UNDO_REVIEW.md` - Undo review (ARCHIVE)
- `MULTI_LINE_INPUT.md` - Multiline input (MERGE into USER_GUIDE?)
- `features/typing-indicator.md` - Typing indicator (KEEP)

**Action:** Keep current features, merge overlapping docs

### 📖 Guides & References (Keep)
Useful guides:
- `editing-strategy-guidelines.md` - Editing guidelines (KEEP)
- `automatic-validation.md` - Validation guide (KEEP)
- `dogfooding-insights.md` - Usage insights (KEEP)
- `AI-SAFETY-GUIDELINES.md` - Safety guidelines (KEEP)

**Action:** Keep all

### ❓ Unclear / Review
Files that need examination:
- `COMPLETE.md` - What is this?
- `STATUS.md` - Current status?
- `INVISIBLE_FLUX.md` - Vision doc?
- `LEARNINGS.md` - Insights?
- `OPTION_B_STARTED.md` - Incomplete work?
- `PHASE2_SMART_INDENTATION.md` - Implementation?
- `multi-provider-implementation.md` - Duplicate of -complete.md?
- `upgrade-to-sonnet.md` - Migration doc?
- `test-clear-command.md` - Feature doc?

**Action:** Review each and categorize

---

## Proposed New Structure

```
docs/
├── README.md                          # Main documentation
├── QUICKSTART.md                      # Getting started
├── USER_GUIDE.md                      # User manual
├── TROUBLESHOOTING.md                 # Common issues
├── QUICK_REFERENCE.md                 # Command reference
├── ROADMAP.md                         # Future plans (NEW - consolidated)
│
├── guides/                            # User guides
│   ├── multi-provider-setup.md
│   ├── auto-fix-mode.md
│   ├── test-driven-workflow.md
│   └── editing-best-practices.md
│
├── architecture/                      # System design
│   ├── OVERVIEW.md                    # System architecture overview (NEW)
│   ├── orchestration.md               # AI orchestration
│   ├── session-persistence.md         # Session system
│   ├── proactive-monitoring.md        # Monitoring system
│   ├── workflows.md                   # Workflow system
│   ├── desktop-app.md                 # Electron app
│   ├── memory-system.md               # Context management
│   ├── ast-editing.md                 # Code editing
│   └── validation-framework.md        # Validation
│
├── development/                       # Developer docs
│   ├── CONTRIBUTING.md                # How to contribute (NEW)
│   ├── debugging.md                   # Debug guide
│   ├── debug-reference.md             # Debug commands
│   ├── safety-guidelines.md           # AI safety
│   └── testing.md                     # Testing guide (NEW)
│
└── archive/                           # Historical docs
    ├── sessions/                      # Work logs
    ├── implementations/               # Completed features
    ├── testing/                       # Old test results
    └── bugfixes/                      # Specific bug fixes
```

---

## Action Plan

### Phase 1: Create New Structure ✅
```bash
mkdir -p docs/guides
mkdir -p docs/architecture
mkdir -p docs/development
mkdir -p docs/archive/{sessions,implementations,testing,bugfixes}
```

### Phase 2: Move Core Docs
- Keep in root: README, QUICKSTART, USER_GUIDE, TROUBLESHOOTING, QUICK_REFERENCE

### Phase 3: Organize by Category
- Move guides → `docs/guides/`
- Move architecture docs → `docs/architecture/`
- Move dev docs → `docs/development/`

### Phase 4: Archive Historical
- Session summaries → `docs/archive/sessions/`
- Completed implementations → `docs/archive/implementations/`
- Test results → `docs/archive/testing/`
- Bug fixes → `docs/archive/bugfixes/`

### Phase 5: Delete Obsolete
- Delete all `.txt` task files
- Delete duplicate/superseded docs

### Phase 6: Update Content
- Update README with new structure
- Update all core docs with current features
- Fix broken links

### Phase 7: Create Missing Docs
- `docs/architecture/OVERVIEW.md` - System architecture
- `docs/ROADMAP.md` - Consolidated roadmap
- `docs/development/CONTRIBUTING.md` - Contribution guide
- `docs/development/testing.md` - Testing guide

---

## Files to Delete (Confirmed Obsolete)

```
ELECTRON_TASK.txt
REAL_WORKFLOW_TASK.txt
SIMPLE_TASK.txt
STREAMING_DIFF_TASK.txt
requirements.txt (duplicate - root has pyproject.toml)
```

---

## Files to Archive

### implementations/
- ORCHESTRATION_COMPLETE.md (superseded by TOP_3_FEATURES.md)
- multi-provider-implementation-complete.md
- IMPROVEMENTS_COMPLETED.md
- PASTE_MODE_IMPLEMENTATION.md
- MULTILINE_INPUT_SOLUTION.md
- CHANGE_PREVIEW_COMPLETE.md
- PHASE_1_COMPLETE.md
- OPTION_A_COMPLETE.md
- OPTION_B_STARTED.md
- PHASE2_SMART_INDENTATION.md
- phase1-complete.md

### sessions/
- session-summary-2025-11-01.md
- SESSION_SUMMARY.md
- SESSION_COMPLETE.md
- FINAL_SESSION_SUMMARY.md
- FINAL_SUMMARY.md
- WEEK2_COMPLETE.md
- WEEK3_PROGRESS.md
- WEEK3_TEST_WORKFLOW_COMPLETE.md
- TODAYS_IMPROVEMENTS.md
- TODAYS_WORK.md

### testing/
- TEST_RESULTS.md
- RELIABILITY_TEST_RESULTS.md
- WORKFLOW_TEST_RESULTS.md
- DEMO_RESULTS.md
- test-clear-results.md
- test-history-failure-analysis.md

### bugfixes/
- BUGFIX_PATH_HANDLING.md
- openai-400-fix.md
- sonnet-access-issue.md
- CRITICAL_ISSUES.md
- DEBUG_ANALYSIS_MULTILINE_FIX.md

---

## Estimated Time

- Phase 1 (Structure): 5 min
- Phase 2-5 (Organization): 20 min
- Phase 6 (Updates): 30 min
- Phase 7 (New docs): 20 min

**Total: ~75 minutes**

---

## Next Steps

1. Review this plan
2. Execute phases sequentially
3. Commit after each major phase
4. Update main README with new structure
