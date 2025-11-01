# Session Persistence Feature Specification

## Overview
Implement session persistence for Flux Desktop to save and restore user sessions across app restarts.

## Requirements

### 1. What to Persist
- **Terminal History**: All terminal output and commands
- **Working Directory**: Current directory path
- **Command History**: List of recent commands (already in memory)
- **File Explorer State**: Expanded folders, current directory
- **Window State**: Size, position (bonus)
- **Settings**: Typing speed preference

### 2. Storage Location
- Store in: `~/.flux/desktop/sessions/`
- Format: JSON files
- One file per session: `session-{timestamp}.json`
- Keep last 10 sessions, auto-cleanup older ones

### 3. Session Structure
```json
{
  "id": "session-20250101-120000",
  "timestamp": "2025-01-01T12:00:00Z",
  "workingDirectory": "/path/to/project",
  "terminalHistory": [
    {
      "type": "output",
      "content": "text here",
      "timestamp": "..."
    },
    {
      "type": "command", 
      "content": "list files",
      "timestamp": "..."
    }
  ],
  "commandHistory": [
    {
      "command": "list files",
      "timestamp": "..."
    }
  ],
  "fileExplorerState": {
    "currentPath": "/path",
    "expandedPaths": ["/path/src", "/path/tests"]
  },
  "settings": {
    "typingSpeed": 15
  }
}
```

### 4. Implementation Files

#### A. Create `src/main/session-manager.js`
- Class: `SessionManager`
- Methods:
  - `saveSession(sessionData)` - Save current session
  - `loadSession(sessionId)` - Load specific session
  - `getLatestSession()` - Get most recent session
  - `listSessions()` - List all saved sessions
  - `deleteSession(sessionId)` - Remove session
  - `cleanupOldSessions()` - Keep only last 10

#### B. Update `src/main/main.js`
- Add IPC handlers:
  - `save-session` - Save current state
  - `load-session` - Restore session
  - `list-sessions` - Get available sessions
- Auto-save session every 5 minutes
- Auto-save on app quit
- Auto-load latest session on startup (optional)

#### C. Update `src/preload/preload.js`
- Expose session API:
  ```javascript
  window.session = {
    save: (data) => ipcRenderer.invoke('save-session', data),
    load: (id) => ipcRenderer.invoke('load-session', id),
    list: () => ipcRenderer.invoke('list-sessions')
  }
  ```

#### D. Update `src/renderer/renderer.js`
- Add session state tracking:
  - Track all terminal output
  - Track command history
  - Track file explorer state
- Add session controls:
  - "Save Session" button in header
  - "Load Session" dropdown menu
  - Auto-save indicator
- Restore session on load:
  - Replay terminal history
  - Restore command history
  - Navigate to working directory
  - Expand folders

#### E. Update `src/renderer/index.html`
- Add session controls to header:
  ```html
  <button class="icon-btn" id="save-session-btn" title="Save Session">
    <svg><!-- save icon --></svg>
  </button>
  <button class="icon-btn" id="load-session-btn" title="Load Session">
    <svg><!-- folder icon --></svg>
  </button>
  ```

#### F. Add CSS for session UI
- Style for save/load buttons
- Loading indicator
- Session list dropdown

### 5. User Flow

#### Saving a Session
1. User clicks save button (or auto-save triggers)
2. App collects current state
3. Session saved to disk
4. Show brief "Saved" notification

#### Loading a Session
1. User clicks load button
2. Dropdown shows list of sessions with timestamps
3. User selects session
4. App clears current state
5. App restores session:
   - Change directory
   - Replay terminal history (with typewriter effect)
   - Restore command history
   - Restore file explorer state
6. Show "Session restored" message

#### Auto-save
1. Every 5 minutes, auto-save current state
2. On app quit, save current state
3. Show subtle indicator in header

#### Auto-restore
1. On app launch, check for latest session
2. If found and < 24 hours old, offer to restore
3. User can accept or start fresh

### 6. Edge Cases to Handle
- Empty sessions (nothing to save)
- Corrupted session files (handle gracefully)
- Directory no longer exists (fallback to home)
- Disk space issues (cleanup old sessions)
- Very large terminal histories (limit to 10,000 lines)

### 7. Testing Checklist
- [ ] Can save current session
- [ ] Can load saved session
- [ ] Can list all sessions
- [ ] Auto-save works every 5 minutes
- [ ] Save on quit works
- [ ] Terminal history restored correctly
- [ ] Command history restored
- [ ] Working directory restored
- [ ] File explorer state restored
- [ ] Old sessions cleaned up (>10)
- [ ] Handles missing directory gracefully
- [ ] Handles corrupted files gracefully
- [ ] Performance with large histories

### 8. Future Enhancements
- Session names/descriptions
- Session search
- Export/import sessions
- Share sessions via file
- Cloud sync (advanced)

## Implementation Order
1. Create SessionManager class
2. Add IPC handlers in main.js
3. Add session API to preload.js
4. Add state tracking to renderer.js
5. Add UI controls to HTML/CSS
6. Implement auto-save
7. Implement auto-restore
8. Test thoroughly
9. Document usage

## Success Criteria
- Users can save and restore complete sessions
- Sessions persist across app restarts
- No data loss on unexpected quit
- Clean, intuitive UI for session management
- Performance impact < 100ms
