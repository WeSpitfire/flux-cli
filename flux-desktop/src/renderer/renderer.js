// Import xterm modules
const { Terminal } = require('xterm');
const { FitAddon } = require('xterm-addon-fit');
const { WebLinksAddon } = require('xterm-addon-web-links');

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

function initializeApp() {
// State management
const state = {
  commandHistory: [],
  historyIndex: -1,
  isProcessing: false
};

// Expose state globally for command palette
window.fluxState = state;

// Initialize terminal
const terminal = new Terminal({
  theme: {
    background: '#1a1b26',
    foreground: '#c0caf5',
    cursor: '#c0caf5',
    cursorAccent: '#1a1b26',
    selection: 'rgba(122, 162, 247, 0.3)',
    black: '#1a1b26',
    red: '#f7768e',
    green: '#9ece6a',
    yellow: '#e0af68',
    blue: '#7aa2f7',
    magenta: '#bb9af7',
    cyan: '#7dcfff',
    white: '#c0caf5',
    brightBlack: '#414868',
    brightRed: '#f7768e',
    brightGreen: '#9ece6a',
    brightYellow: '#e0af68',
    brightBlue: '#7aa2f7',
    brightMagenta: '#bb9af7',
    brightCyan: '#7dcfff',
    brightWhite: '#c0caf5'
  },
  fontFamily: "'SF Mono', 'Monaco', 'Cascadia Code', 'Courier New', monospace",
  fontSize: 14,
  lineHeight: 1.5,
  cursorBlink: true,
  cursorStyle: 'block',
  scrollback: 10000,
  allowTransparency: true,
  convertEol: true  // Convert \n to \r\n for proper line breaks
});

// Load addons
const fitAddon = new FitAddon();
const webLinksAddon = new WebLinksAddon();
terminal.loadAddon(fitAddon);
terminal.loadAddon(webLinksAddon);

// Open terminal
const terminalElement = document.getElementById('terminal');
console.log('Terminal element:', terminalElement);
console.log('Terminal element dimensions:', terminalElement.offsetWidth, 'x', terminalElement.offsetHeight);

terminal.open(terminalElement);
console.log('Terminal opened');

fitAddon.fit();
console.log('FitAddon applied');
console.log('Terminal cols:', terminal.cols, 'rows:', terminal.rows);

// Welcome message
terminal.writeln('\x1b[1;34m╔════════════════════════════════════════════╗\x1b[0m');
terminal.writeln('\x1b[1;34m║\x1b[0m     \x1b[1;36mFlux AI Coding Assistant\x1b[0m            \x1b[1;34m║\x1b[0m');
terminal.writeln('\x1b[1;34m╚════════════════════════════════════════════╝\x1b[0m');
terminal.writeln('');
terminal.writeln('\x1b[32m✓\x1b[0m Ready to assist with your coding tasks');
terminal.writeln('\x1b[2mType a command below or ask Flux anything...\x1b[0m');
terminal.writeln('');

// Resize handler
window.addEventListener('resize', () => {
  fitAddon.fit();
});

// DOM elements
const commandInput = document.getElementById('command-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const sidebar = document.getElementById('sidebar');
const historyList = document.getElementById('history-list');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

// Update status
function updateStatus(status, text) {
  statusDot.className = `status-dot ${status}`;
  statusText.textContent = text;
}

// Add to history
function addToHistory(command) {
  const timestamp = new Date().toLocaleTimeString();
  state.commandHistory.unshift({ command, timestamp });
  
  // Keep only last 50 commands
  if (state.commandHistory.length > 50) {
    state.commandHistory.pop();
  }
  
  // Update history UI
  updateHistoryUI();
}

// Update history UI
function updateHistoryUI() {
  historyList.innerHTML = state.commandHistory
    .map((item, index) => `
      <div class="history-item fade-in" data-index="${index}">
        <div class="history-item-command">${escapeHtml(item.command)}</div>
        <div class="history-item-time">${item.timestamp}</div>
      </div>
    `)
    .join('');
  
  // Add click handlers
  document.querySelectorAll('.history-item').forEach(item => {
    item.addEventListener('click', () => {
      const index = parseInt(item.dataset.index);
      commandInput.value = state.commandHistory[index].command;
      commandInput.focus();
    });
  });
}

// Escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Toggle send button UI between send and stop modes
function updateSendButton(isProcessing) {
  const sendIcon = sendBtn.querySelector('.send-icon');
  const stopIcon = sendBtn.querySelector('.stop-icon');
  
  if (isProcessing) {
    sendIcon.style.display = 'none';
    stopIcon.style.display = 'block';
    sendBtn.title = 'Stop';
    sendBtn.classList.add('stop-mode');
  } else {
    sendIcon.style.display = 'block';
    stopIcon.style.display = 'none';
    sendBtn.title = 'Send (Enter)';
    sendBtn.classList.remove('stop-mode');
  }
}

// Cancel command
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
  stopInactivityCheck(); // Stop checking for inactivity
}

// Send command
function sendCommand() {
  // If processing, stop instead of send
  if (state.isProcessing) {
    cancelCommand();
    return;
  }
  
  const command = commandInput.value.trim();
  if (!command) return;
  
  // Analyze command with intelligence system
  if (window.commandIntelligence) {
    const analysis = window.commandIntelligence.analyzeCommand(command);
    
    // If command needs confirmation or has typo, show dialog
    if (analysis.needsConfirmation || analysis.typoCorrection) {
      window.commandConfirmDialog.show(
        command,
        analysis,
        // On confirm - execute command
        (confirmedCommand) => {
          executeCommand(confirmedCommand);
        },
        // On cancel - do nothing
        () => {
          // Command cancelled
        },
        // On edit - put back in input
        (editedCommand) => {
          commandInput.value = editedCommand;
          commandInput.focus();
        }
      );
      return;
    }
  }
  
  // Safe command - execute directly
  executeCommand(command);
}

// Execute command (extracted for reuse)
function executeCommand(command) {
  // Clear input
  commandInput.value = '';
  
  // Update status
  updateStatus('processing', 'Processing...');
  state.isProcessing = true;
  updateSendButton(true);
  
  // Write command to terminal with nice formatting
  terminal.writeln(`\r\n\x1b[1;36mYou: \x1b[0m${command}`);
  terminal.scrollToBottom();
  
  // Add to history
  addToHistory(command);
  state.historyIndex = -1;
  
  // Send to backend
  window.flux.sendCommand(command);
  
  // Start inactivity detection (resets processing state if no output for 3 seconds)
  startInactivityCheck();
}

// Typewriter effect for readable output
let outputQueue = [];
let isTyping = false;
let TYPING_SPEED = 15; // milliseconds per character (adjustable: lower = faster)
let skipAnimation = false;
let lastOutputTime = null;
let inactivityCheckInterval = null;

function typewriterEffect() {
  if (outputQueue.length === 0) {
    isTyping = false;
    skipAnimation = false;
    updateStatus('', 'Ready');
    state.isProcessing = false;
    updateSendButton(false);
    stopInactivityCheck(); // Stop checking for inactivity
    return;
  }
  
  isTyping = true;
  
  // If skip is requested, flush all at once
  if (skipAnimation) {
    const remainingText = outputQueue.join('');
    outputQueue = [];
    terminal.write(remainingText);
    terminal.scrollToBottom();
    isTyping = false;
    skipAnimation = false;
    updateStatus('', 'Ready');
    state.isProcessing = false;
    updateSendButton(false);
    stopInactivityCheck(); // Stop checking for inactivity
    return;
  }
  
  const char = outputQueue.shift();
  terminal.write(char);
  
  // Auto-scroll periodically (not on every character for performance)
  if (outputQueue.length % 50 === 0) {
    terminal.scrollToBottom();
  }
  
  setTimeout(typewriterEffect, TYPING_SPEED);
}

// Inactivity detection - reset state if no output for 3 seconds after last output
function startInactivityCheck() {
  lastOutputTime = Date.now();
  
  // Clear existing interval
  if (inactivityCheckInterval) {
    clearInterval(inactivityCheckInterval);
  }
  
  inactivityCheckInterval = setInterval(() => {
    // If we're still processing but haven't received output in 3 seconds
    // and there's no more output queued, assume command finished
    if (state.isProcessing && lastOutputTime) {
      const timeSinceOutput = Date.now() - lastOutputTime;
      if (timeSinceOutput > 3000 && outputQueue.length === 0 && !isTyping) {
        console.log('No output for 3s, resetting processing state');
        clearInterval(inactivityCheckInterval);
        inactivityCheckInterval = null;
        state.isProcessing = false;
        updateSendButton(false);
        updateStatus('', 'Ready');
      }
    }
  }, 500); // Check every 500ms
}

function stopInactivityCheck() {
  if (inactivityCheckInterval) {
    clearInterval(inactivityCheckInterval);
    inactivityCheckInterval = null;
  }
  lastOutputTime = null;
}

// Handle flux output with typewriter effect
window.flux.onOutput((data) => {
  console.log('Received flux output:', data.length, 'chars');
  lastOutputTime = Date.now(); // Update last output time
  
  // Add characters to queue
  for (let i = 0; i < data.length; i++) {
    outputQueue.push(data[i]);
  }
  
  // Start typing if not already typing
  if (!isTyping) {
    typewriterEffect();
  }
});

// Handle flux errors
window.flux.onError((data) => {
  terminal.write(`\x1b[31m${data}\x1b[0m`);
  updateStatus('error', 'Error');
  state.isProcessing = false;
  updateSendButton(false);
  stopInactivityCheck(); // Stop checking for inactivity
});

// Handle flux cancellation
window.flux.onCancelled(() => {
  // Cancellation already handled in cancelCommand()
  // This is for backend confirmation if needed
});

// Auto-grow textarea
commandInput.addEventListener('input', () => {
  commandInput.style.height = 'auto';
  commandInput.style.height = commandInput.scrollHeight + 'px';
});

// Input event handlers
commandInput.addEventListener('keydown', (e) => {
  // Send on Enter (without Shift)
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendCommand();
  }
  
  // Skip animation on Ctrl+C or Escape
  if ((e.key === 'c' && (e.ctrlKey || e.metaKey)) || e.key === 'Escape') {
    if (isTyping) {
      e.preventDefault();
      skipAnimation = true;
    }
  }
  
  // History navigation with Up/Down arrows
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (state.historyIndex < state.commandHistory.length - 1) {
      state.historyIndex++;
      commandInput.value = state.commandHistory[state.historyIndex].command;
    }
  }
  
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (state.historyIndex > 0) {
      state.historyIndex--;
      commandInput.value = state.commandHistory[state.historyIndex].command;
    } else if (state.historyIndex === 0) {
      state.historyIndex = -1;
      commandInput.value = '';
    }
  }
});

sendBtn.addEventListener('click', sendCommand);

// Clear button
clearBtn.addEventListener('click', () => {
  // Also clear any pending output
  outputQueue = [];
  skipAnimation = false;
  isTyping = false;
  terminal.clear();
  terminal.writeln('\x1b[2mTerminal cleared\x1b[0m');
});

// Toggle sidebar
toggleSidebarBtn.addEventListener('click', () => {
  sidebar.classList.toggle('collapsed');
});

// Tab switching
const sidebarTabs = document.querySelectorAll('.sidebar-tab');
const sidebarPanels = document.querySelectorAll('.sidebar-panel');

sidebarTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const tabName = tab.dataset.tab;
    
    // Update tab active state
    sidebarTabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    
    // Update panel active state
    sidebarPanels.forEach(p => p.classList.remove('active'));
    document.getElementById(`${tabName}-panel`).classList.add('active');
  });
});

// Directory selection
const changeDirBtn = document.getElementById('change-directory');
if (changeDirBtn) {
  changeDirBtn.addEventListener('click', async () => {
    const newDir = await window.fileSystem.selectDirectory();
    if (newDir) {
      // Clear and reload file tree
      const fileTreeContainer = document.getElementById('file-tree-container');
      fileTreeContainer.innerHTML = '';
      
      // Update directory path display
      const dirPathEl = document.getElementById('directory-path');
      dirPathEl.textContent = newDir;
      
      // Reload file explorer with new directory
      if (window.loadDirectory) {
        await window.loadDirectory(newDir, fileTreeContainer);
      }
    }
  });
}

// Settings button - adjust typing speed
const settingsBtn = document.getElementById('settings-btn');
if (settingsBtn) {
  settingsBtn.addEventListener('click', () => {
    const speeds = [
      { name: 'Instant', value: 0 },
      { name: 'Very Fast', value: 5 },
      { name: 'Fast', value: 10 },
      { name: 'Normal', value: 15 },
      { name: 'Slow', value: 25 },
      { name: 'Very Slow', value: 40 }
    ];
    
    const currentSpeed = speeds.find(s => s.value === TYPING_SPEED) || speeds[3];
    const currentIndex = speeds.indexOf(currentSpeed);
    const nextIndex = (currentIndex + 1) % speeds.length;
    
    TYPING_SPEED = speeds[nextIndex].value;
    
    // Show feedback in terminal
    terminal.writeln(`\r\n\x1b[90mTyping speed: ${speeds[nextIndex].name}\x1b[0m`);
    terminal.scrollToBottom();
  });
}

// Focus input on load
commandInput.focus();

} // End of initializeApp
