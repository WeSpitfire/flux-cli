# Task: Complete Flux Desktop UI

## Current State
The Electron app has:
- ✅ Basic terminal (xterm.js) 
- ✅ Python Flux CLI spawning in main process
- ✅ IPC communication setup
- ⚠️ Missing: styles.css (UI is just a box)
- ⚠️ Missing: Proper layout and styling

## Goal
Make the UI functional and professional by creating `styles.css`

## Requirements

### 1. Create `src/renderer/styles.css` with:

**Layout:**
- App container: full height, flexbox row
- Sidebar: 280px wide, dark background (#2d2d2d)
- Main content: flex-grow, terminal takes full space
- Terminal container: full height/width, dark theme

**Sidebar styling:**
- Header with Flux logo and version
- Quick action buttons (blue, hover effects)
- File explorer section
- Connection status indicator (green=connected, red=disconnected)

**Terminal styling:**
- Black/dark background (#1e1e1e)
- Proper padding and spacing
- Full height, scrollable

**Colors:**
- Background: #1e1e1e (dark)
- Sidebar: #2d2d2d (slightly lighter)
- Text: #d4d4d4 (light gray)
- Accent: #007acc (VS Code blue)
- Success: #0dbc79 (green)
- Error: #cd3131 (red)

### 2. Fix any missing CSS classes referenced in HTML:
- `.app-container`
- `.sidebar`, `.sidebar-header`, `.sidebar-content`
- `.main-content`, `.terminal-container`
- `.action-btn`
- `.connection-status`, `.connected`, `.disconnected`

### 3. Ensure responsive layout:
- Terminal resizes properly
- Sidebar stays fixed width
- No horizontal scroll

## Files to Create/Modify
- **CREATE**: `src/renderer/styles.css` (main task)
- **VERIFY**: `src/renderer/index.html` (check all classes exist)

## Testing
After creating styles.css, the app should:
1. Have a professional dark UI
2. Sidebar visible on left with buttons
3. Terminal taking up main area
4. No "just a box" - proper layout

## Notes
- Use modern CSS (flexbox/grid)
- Match VS Code's dark theme aesthetics
- Keep it clean and minimal
