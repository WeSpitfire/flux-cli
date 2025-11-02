# Flux Keyboard Shortcuts

Complete reference for all keyboard shortcuts in Flux.

---

## Global Shortcuts

### Navigation
- `Cmd+/` (Mac) / `Ctrl+/` (Win/Linux) - **Show shortcuts overlay**
- `Esc` - **Close any dialog or overlay**
- `Cmd+Q` (Mac) / `Ctrl+Q` (Win/Linux) - **Quit Flux**

### Features
- `Cmd+K` (Mac) / `Ctrl+K` (Win/Linux) - **Open Command Palette**
- `Cmd+Shift+M` (Mac) / `Ctrl+Shift+M` (Win/Linux) - **Open Workflow Manager**
- `Cmd+Shift+W` (Mac) / `Ctrl+Shift+W` (Win/Linux) - **Open Workflow Selector**

---

## Command Palette (`Cmd+K`)

### Search & Navigation
- `Type to search` - **Filter results**
- `↑` / `↓` - **Navigate results**
- `Enter` - **Select highlighted result**
- `Esc` - **Close palette**

### Result Types
- Commands - Recently used commands
- Files - Project files
- History - Command history

---

## Command Intelligence

### Automatic Detection
- Runs automatically when typing risky commands
- No manual shortcuts needed
- Shows confirmation dialog for:
  - `rm -rf` operations
  - `sudo` commands
  - `DROP` database commands
  - Production deployments

### Confirmation Dialog
- `Enter` or `Y` - **Confirm and run command**
- `Esc` or `N` - **Cancel command**
- `E` - **Show detailed explanation**
- `Tab` - **Focus buttons**

---

## Workflow Manager (`Cmd+Shift+M`)

### Library Browser
- `Type in search` - **Filter workflows**
- `↑` / `↓` - **Navigate workflow cards**
- `Enter` - **Run selected workflow**
- `Cmd+N` / `Ctrl+N` - **New workflow**
- `Cmd+I` / `Ctrl+I` - **Import workflow**
- `Esc` - **Close manager**

### Workflow Card Menu
- `Click ⋮ button` - **Open context menu**
- `R` - **Run workflow**
- `E` - **Edit workflow**
- `D` - **Duplicate workflow**
- `X` - **Export workflow**
- `Delete` - **Delete workflow (with confirmation)**

### Sort & Filter
- Uses dropdown menus (no shortcuts)
- **Sort by:** Name, Recent, Steps
- **Filter by:** Tags

---

## Workflow Editor

### Editing
- `Tab` - **Navigate form fields**
- `Cmd+S` / `Ctrl+S` - **Save workflow**
- `Cmd+Enter` / `Ctrl+Enter` - **Save and close**
- `Esc` - **Cancel (if no changes)**

### Steps
- `Click "Add Step"` - **Add new step**
- `Delete on step` - **Remove step**
- `Cmd+D` / `Ctrl+D` - **Duplicate step** (when focused)
- `Cmd+↑` / `Ctrl+↑` - **Move step up**
- `Cmd+↓` / `Ctrl+↓` - **Move step down**

---

## Workflow Selector (`Cmd+Shift+W`)

### Quick Run
- `Type to search` - **Filter workflows**
- `↑` / `↓` - **Navigate workflow list**
- `Enter` - **Run selected workflow**
- `Esc` - **Close selector**

### During Search
- Search is fuzzy - matches name and description
- Results update instantly as you type
- Most recently used workflows appear first

---

## Workflow Execution

### Progress Dialog
- Shows automatically when workflow starts
- No navigation shortcuts during execution
- `Esc` or `Cancel button` - **Stop workflow (with confirmation)**

### Variable Input
- `Tab` - **Navigate form fields**
- `Enter` - **Submit form and start**
- `Esc` - **Cancel workflow**

### Confirmation Prompts
- `Y` or `Enter` - **Confirm (Yes)**
- `N` or `Esc` - **Cancel (No)**
- `Tab` - **Focus buttons**

---

## Text Editing

### Standard Text Input
- `Cmd+A` / `Ctrl+A` - **Select all**
- `Cmd+C` / `Ctrl+C` - **Copy**
- `Cmd+X` / `Ctrl+X` - **Cut**
- `Cmd+V` / `Ctrl+V` - **Paste**
- `Cmd+Z` / `Ctrl+Z` - **Undo**
- `Cmd+Shift+Z` / `Ctrl+Y` - **Redo**

### Command Input
- `↑` - **Previous command in history**
- `↓` - **Next command in history**
- `Tab` - **Autocomplete (if available)**
- `Ctrl+C` - **Cancel current command**

---

## Accessibility

### Screen Reader Support
- All interactive elements have ARIA labels
- Keyboard navigation supported throughout
- Focus indicators visible
- Semantic HTML structure

### Focus Management
- `Tab` - **Next focusable element**
- `Shift+Tab` - **Previous focusable element**
- `Enter` or `Space` - **Activate button/link**
- Focus is trapped in dialogs until closed

---

## Pro Tips

### Speed Tips
1. **Learn 3 shortcuts first:**
   - `Cmd+K` - Command Palette (most used)
   - `Cmd+Shift+M` - Workflow Manager
   - `Cmd+/` - Show shortcuts

2. **Use fuzzy search:**
   - Type partial matches: "gcp" matches "Git Commit & Push"
   - No need to type full names
   - Search is case-insensitive

3. **Chain workflows:**
   - Save common sequences as workflows
   - Use variables for flexibility
   - Share workflows with team

### Efficiency Patterns
- **Command Palette** for one-off commands
- **Workflows** for repetitive tasks
- **Intelligence** prevents mistakes
- **Manager** for organizing workflows

### Custom Workflows
Create workflows for:
- `Cmd+Shift+1` - Custom workflow #1 (configure in settings)
- `Cmd+Shift+2` - Custom workflow #2
- `Cmd+Shift+3` - Custom workflow #3

---

## Shortcuts by Feature

### Most Used (Top 10)
1. `Cmd+K` - Command Palette
2. `Cmd+Shift+M` - Workflow Manager
3. `Cmd+Shift+W` - Run Workflow
4. `Cmd+/` - Show Shortcuts
5. `Esc` - Close Dialog
6. `Enter` - Confirm/Select
7. `↑↓` - Navigate Lists
8. `Tab` - Navigate Forms
9. `Cmd+S` - Save
10. `Cmd+N` - New Item

### Power User Combos
- `Cmd+K` → Type → `Enter` - **Quick command**
- `Cmd+Shift+M` → Type → `Enter` - **Quick workflow**
- `Cmd+Shift+W` → `Enter` - **Run recent workflow**
- `Cmd+/` → Search - **Find any shortcut**

---

## Customization

### Changing Shortcuts (Future)
Currently shortcuts are fixed, but planned features:
- Custom keyboard shortcuts
- Configurable key bindings
- Import/export shortcut configs
- Preset shortcut schemes (Vim, Emacs, etc.)

### Platform Differences
- **Mac:** Uses `Cmd` key (⌘)
- **Windows/Linux:** Uses `Ctrl` key
- All other keys are the same
- Function keys (F1-F12) reserved for future use

---

## Conflicts & Resolution

### Known Conflicts
- `Cmd+K` may conflict with browser search
  - **Solution:** Use Flux in standalone app
- `Cmd+Shift+M` may conflict with dev tools
  - **Solution:** Disable browser shortcut or use Flux app

### Avoiding Conflicts
- Flux uses uncommon combinations (`Shift+M`, `Shift+W`)
- Global shortcuts can be disabled in preferences
- Per-feature shortcuts always work in dialogs

---

## Learning Shortcuts

### Discoverability
- Hover tooltips show shortcuts
- Shortcuts displayed in menus
- `Cmd+/` overlay shows all shortcuts
- Help text includes shortcut hints

### Practice Mode (Future)
- Interactive tutorial
- Shortcut trainer
- Speed challenges
- Achievement badges

---

## Mobile/Touch Support

### Touch Gestures
- **Swipe right** - Go back
- **Swipe left** - Go forward
- **Long press** - Context menu
- **Pinch** - Zoom (where applicable)

### On-Screen Buttons
- All shortcuts have on-screen equivalents
- Touch-friendly button sizes
- Gesture hints shown on first use

---

## Quick Reference Card

### Print This!
```
╔══════════════════════════════════════════╗
║         FLUX KEYBOARD SHORTCUTS          ║
╠══════════════════════════════════════════╣
║ Cmd+K           Open Command Palette     ║
║ Cmd+Shift+M     Workflow Manager         ║
║ Cmd+Shift+W     Run Workflow             ║
║ Cmd+/           Show Shortcuts           ║
║ Esc             Close Dialog             ║
║ ↑↓              Navigate                 ║
║ Enter           Select/Confirm           ║
║ Tab             Next Field               ║
╚══════════════════════════════════════════╝
```

---

## Support

### Getting Help
- Press `Cmd+/` to see all shortcuts
- Check tooltips on buttons
- Read workflow guide: `WORKFLOW_USER_GUIDE.md`
- Run tests: `test-workflow-system.html`

### Reporting Issues
If a shortcut doesn't work:
1. Check if dialog is focused
2. Verify key combination
3. Check for browser conflicts
4. Report bug with OS/browser details

---

## Changelog

### Version 1.0 (Current)
- Initial keyboard shortcut implementation
- Global navigation shortcuts
- Feature-specific shortcuts
- Dialog and form shortcuts

### Coming Soon
- Custom key bindings
- Shortcut recorder
- Vim mode
- Emacs mode

---

**Remember:** Practice makes perfect! Start with `Cmd+K`, `Cmd+Shift+M`, and `Cmd+/` - these three shortcuts cover 80% of use cases.

Happy keystroking! ⌨️
