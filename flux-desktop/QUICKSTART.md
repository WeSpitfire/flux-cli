# Flux Desktop - Quick Start Guide

Get up and running with Flux Desktop in under 5 minutes!

## Prerequisites

✅ Node.js 18+ installed  
✅ Python 3.8+ installed  
✅ Flux CLI installed

## Installation

### Step 1: Install Flux CLI (if not already installed)

```bash
cd /Users/developer/SynologyDrive/flux-cli
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Verify installation:
```bash
flux --help
```

### Step 2: Install Flux Desktop dependencies

```bash
cd flux-desktop
npm install
```

## Launch

### Using the launch script (recommended):

```bash
cd flux-desktop
./launch.sh
```

### Or manually:

```bash
cd flux-desktop
npm run dev
```

## First Steps

1. **App opens** - You should see a modern terminal interface
2. **Welcome message** - Terminal displays a welcome banner
3. **Status indicator** - Header shows "Ready" with a green dot
4. **Type a command** - Try: `"list files in current directory"`
5. **Press Enter** - Watch Flux process your request!

## Basic Usage

### Sending Commands

Type in the input field at the bottom and press `Enter`:

```
list files
```

```
create a hello world script
```

```
explain what this code does: [paste code]
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send command |
| `↑` / `↓` | Navigate command history |
| `Ctrl+K` or `Cmd+K` | Clear terminal |

### Using History

- **View history**: Click sidebar toggle to see past commands
- **Reuse commands**: Click any history item to populate input
- **Navigate**: Use up/down arrow keys

## Troubleshooting

### Terminal not showing output?

1. Check the status indicator (should be green "Ready")
2. Look at the terminal where you ran `npm run dev` for errors
3. Open DevTools (auto-opens in dev mode) and check Console

### "Process error: spawn flux ENOENT"?

Flux CLI not found. Install it:
```bash
cd /Users/developer/SynologyDrive/flux-cli
pip install -e .
```

### Commands not sending?

1. Check if Flux process is running: `ps aux | grep flux`
2. Restart the app
3. Check `TROUBLESHOOTING.md` for detailed help

## Features Overview

### 🖥️ Terminal
- Full xterm.js terminal emulation
- 10,000 line scrollback
- Clickable links
- ANSI color support

### 📝 Command History  
- Last 50 commands saved
- Timestamps
- Quick reuse by clicking

### 🎨 Modern UI
- Dark theme (Tokyo Night)
- Professional design
- Smooth animations
- Status indicators

### ⌨️ Keyboard-First
- Full keyboard navigation
- History search
- Quick shortcuts

## Tips

1. **Start simple**: Try basic commands like "list files" first
2. **Use history**: Don't retype - use arrow keys or click history
3. **Clear often**: Use Ctrl+K to keep terminal clean
4. **Check status**: Always glance at the status indicator
5. **Read output**: Flux provides detailed explanations

## Next Steps

Once you're comfortable:

- Try complex refactoring tasks
- Use Flux for code generation
- Ask Flux to explain complex code
- Let Flux help with debugging

## Getting Help

- Check `TROUBLESHOOTING.md` for common issues
- Check `FIXES_APPLIED.md` for technical details
- Open DevTools to see detailed logs
- Run `npm run dev` to see console output

## Feedback

If something isn't working:

1. Check DevTools Console for errors
2. Check terminal output where you ran `npm run dev`
3. Try the troubleshooting steps
4. Check if Flux CLI works standalone: `flux --help`

---

**Happy coding with Flux! 🚀**
