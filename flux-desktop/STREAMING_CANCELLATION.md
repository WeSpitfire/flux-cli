# Streaming Cancellation Feature

## Overview
This document describes the implementation of the streaming cancellation feature in Flux Desktop, allowing users to interrupt long-running LLM operations.

## Architecture

### 1. Backend (main.js)
The backend handles process management and signal forwarding:

```javascript
ipcMain.on('flux-cancel', (event) => {
  if (fluxProcess && !fluxProcess.killed) {
    // Send Ctrl+C (SIGINT) to interrupt the process
    fluxProcess.kill('SIGINT');
    win.webContents.send('flux-cancelled');
  }
});
```

**Key features:**
- Listens for `flux-cancel` IPC events from the renderer
- Sends SIGINT signal to the Flux CLI process
- Confirms cancellation with `flux-cancelled` event

### 2. Preload (preload.js)
The preload script exposes cancellation APIs to the renderer:

```javascript
window.flux = {
  cancelCommand: () => {
    ipcRenderer.send('flux-cancel');
  },
  
  onCancelled: (callback) => {
    ipcRenderer.on('flux-cancelled', (_, data) => {
      callback(data);
    });
  }
};
```

**Key features:**
- `cancelCommand()`: Triggers cancellation
- `onCancelled()`: Listens for cancellation confirmation

### 3. Frontend (renderer.js & index.html)

#### UI Components
The send button toggles between two modes:

**Send Mode (default):**
- Shows paper plane icon
- Blue background (`--accent-primary`)
- Title: "Send (Enter)"

**Stop Mode (during processing):**
- Shows stop square icon
- Red background (`--error`)
- Title: "Stop (Ctrl+C)"

#### State Management
```javascript
function updateSendButton(isProcessing) {
  const sendIcon = sendBtn.querySelector('.send-icon');
  const stopIcon = sendBtn.querySelector('.stop-icon');
  
  if (isProcessing) {
    sendIcon.style.display = 'none';
    stopIcon.style.display = 'block';
    sendBtn.title = 'Stop (Ctrl+C)';
    sendBtn.classList.add('stop-mode');
  } else {
    sendIcon.style.display = 'block';
    stopIcon.style.display = 'none';
    sendBtn.title = 'Send (Enter)';
    sendBtn.classList.remove('stop-mode');
  }
}
```

#### Cancellation Logic
```javascript
function cancelCommand() {
  if (!state.isProcessing) return;
  
  // Send cancel signal to backend
  window.flux.cancelCommand();
  
  // Clear output queue
  outputQueue = [];
  skipAnimation = false;
  isTyping = false;
  
  // Update UI
  terminal.writeln('\r\n\x1b[33m^C Command cancelled\x1b[0m');
  terminal.scrollToBottom();
  updateStatus('', 'Ready');
  state.isProcessing = false;
  updateSendButton(false);
}
```

**Cancellation behavior:**
1. Sends cancel signal to backend via IPC
2. Clears any pending typewriter output
3. Displays cancellation message in terminal
4. Resets UI to ready state
5. Toggles send button back to send mode

## User Interactions

### 1. Click Stop Button
- When processing, clicking the send button triggers cancellation
- Button changes color from blue to red
- Icon changes from send arrow to stop square

### 2. Keyboard Shortcut: Ctrl+C (Skip Animation)
```javascript
if ((e.key === 'c' && (e.ctrlKey || e.metaKey)) || e.key === 'Escape') {
  if (isTyping) {
    e.preventDefault();
    skipAnimation = true;
  }
}
```

- Works when command input is focused
- Only active during typewriter animation
- Immediately flushes all remaining text to terminal
- Does NOT cancel the command - just skips the animation

### 3. Visual Feedback

**Stop button (cancels command):**
- Terminal displays: `^C Command cancelled` (in yellow)
- Status indicator changes to "Ready"
- Send button reverts to send mode
- Output queue is cleared immediately
- Backend process receives SIGINT

**Ctrl+C or Esc (skips animation):**
- Remaining text flushes instantly to terminal
- Status indicator changes to "Ready"
- Send button reverts to send mode
- Command completes normally (not cancelled)

## CSS Styling

```css
.send-btn.stop-mode {
  background-color: var(--error);
}

.send-btn.stop-mode:hover {
  background-color: #ff6b6b;
}
```

**Color scheme:**
- Default send: `#58a6ff` (blue)
- Stop mode: `#f85149` (red)
- Stop hover: `#ff6b6b` (lighter red)

## Integration Points

### State Updates
The following functions call `updateSendButton()`:
1. `sendCommand()` - Sets to stop mode when sending
2. `cancelCommand()` - Resets to send mode
3. `typewriterEffect()` - Resets to send mode when output completes
4. `window.flux.onError()` - Resets to send mode on error

### Process Lifecycle
```
User sends command
  ↓
state.isProcessing = true
  ↓
updateSendButton(true) → Stop mode
  ↓
[Processing... user can cancel]
  ↓
Output complete OR cancelled OR error
  ↓
state.isProcessing = false
  ↓
updateSendButton(false) → Send mode
```

## Testing Checklist

- [ ] Click send button to send command
- [ ] Click stop button while processing
- [ ] Press Ctrl+C while processing
- [ ] Verify cancellation message appears
- [ ] Verify button changes color and icon
- [ ] Verify status changes to "Ready"
- [ ] Verify output queue clears
- [ ] Test on long-running commands
- [ ] Test multiple cancel/send cycles
- [ ] Test keyboard shortcut with Cmd+C (macOS)
- [ ] Verify button tooltip changes
- [ ] Test with empty output queue
- [ ] Test with animation in progress

## Future Enhancements

1. **Graceful Cancellation**
   - Send custom signal to allow Flux to clean up
   - Wait for acknowledgment before forcing kill

2. **Cancellation Confirmation**
   - Optional dialog for long-running tasks
   - "Are you sure?" for destructive operations

3. **Partial Results**
   - Display output received before cancellation
   - Save incomplete responses to history

4. **Cancel Multiple Requests**
   - Queue management for multiple commands
   - Bulk cancellation UI

5. **Timeout Settings**
   - Auto-cancel after configurable timeout
   - Warning before auto-cancel

## Known Limitations

1. **Process Cleanup**: SIGINT may not always cleanly terminate the Flux process. Consider adding SIGKILL fallback after timeout.

2. **Output Buffering**: Some output may still be in the pipeline after cancellation is triggered.

3. **State Recovery**: If the process crashes during cancellation, the UI state may need manual recovery.

4. **Platform Differences**: Signal handling may behave differently on Windows vs Unix systems.

## Error Handling

- Backend checks if process exists before sending signal
- Frontend checks `isProcessing` state before cancelling
- UI remains responsive even if backend fails to cancel
- Output queue is cleared regardless of backend response

## Summary

The streaming cancellation feature provides users with immediate control over long-running operations through:
- Visual toggle between send/stop modes
- Intuitive keyboard shortcut (Ctrl+C)
- Immediate UI feedback
- Clean state management
- Cross-platform signal handling

The implementation maintains consistency with terminal behavior while providing a modern, accessible UI in the Electron application.
