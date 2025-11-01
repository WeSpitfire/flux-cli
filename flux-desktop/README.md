# Flux Desktop

Native macOS application for Flux AI Coding Assistant built with Electron.

## Features

- 🖥️ Native macOS window with traffic lights
- 💻 Full terminal emulation with xterm.js
- 🎨 Beautiful dark theme similar to VS Code
- ⚡ Real-time communication with Flux Python backend
- 🎯 Quick action sidebar

## Setup

```bash
# Install dependencies
npm install

# Run the app
npm start
```

## Architecture

```
┌─────────────────────────────────┐
│   Electron Window (macOS)       │
├─────────────────────────────────┤
│  Frontend (renderer process)    │
│  - xterm.js terminal            │
│  - Sidebar UI                   │
│  - IPC communication            │
├─────────────────────────────────┤
│  Backend (main process)         │
│  - Python subprocess            │
│  - IPC handlers                 │
│  - Flux CLI integration         │
└─────────────────────────────────┘
```

## Project Structure

```
flux-desktop/
├── package.json
├── src/
│   ├── main/
│   │   └── main.js          # Electron main process
│   ├── preload/
│   │   └── preload.js       # Secure IPC bridge
│   └── renderer/
│       ├── index.html       # UI structure
│       ├── renderer.js      # Terminal & UI logic
│       └── styles.css       # Dark theme styles
```

## How It Works

1. **Main Process** spawns Flux Python CLI as subprocess
2. **Preload Script** exposes secure IPC API to renderer
3. **Renderer** creates xterm.js terminal and handles user input
4. **Communication** flows via IPC: renderer → main → Python → main → renderer

## Quick Actions

- **New Session** - Clear terminal and start fresh
- **/memory** - Show project memory
- **/undo-history** - Show undo history

## Development

Built using Flux itself as a meta demonstration of AI-assisted development!

## Next Steps

- [ ] Add file tree sidebar
- [ ] Visual diff viewer
- [ ] Settings panel
- [ ] Command palette (⌘K)
- [ ] Multiple terminal tabs
- [ ] Project switcher
