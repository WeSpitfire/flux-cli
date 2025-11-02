// Import xterm modules
const { Terminal } = require('xterm');
const { FitAddon } = require('xterm-addon-fit');
const { WebLinksAddon } = require('xterm-addon-web-links');

// Global state for tab management
const terminals = new Map(); // tabId -> terminal instance
let tabManager = null;
let sessionManager = null;

// Expose terminals globally for session management
window.terminals = terminals;

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

function initializeApp() {
  // Initialize TabManager first
  tabManager = new window.TabManager();
  
  // Expose globally for cross-file access
  window.tabManager = tabManager;
  
  // Expose initialization function for TabManager to call
  window.initializeTerminalForTab = initializeTerminalForTab;
  
  // Initialize SessionManager and restore previous session
  sessionManager = new window.SessionManager();
  sessionManager.init(tabManager);
  window.sessionManager = sessionManager;
  
  // Setup global event listeners
  setupGlobalEventListeners();
}

// Create terminal configuration
function getTerminalConfig() {
  return {
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
    convertEol: true
  };
}

// Initialize terminal for a specific tab
function initializeTerminalForTab(tabId, containerElement) {
  console.log('Initializing terminal for tab:', tabId);
  
  // Create terminal instance
  const terminal = new Terminal(getTerminalConfig());
  
  // Load addons
  const fitAddon = new FitAddon();
  const webLinksAddon = new WebLinksAddon();
  terminal.loadAddon(fitAddon);
  terminal.loadAddon(webLinksAddon);
  
  // Open terminal in container
  terminal.open(containerElement);
  
  // Fit after a short delay to ensure container is visible
  setTimeout(() => {
    fitAddon.fit();
  }, 50);
  
  // Welcome message
  terminal.writeln('\x1b[1;34m╔════════════════════════════════════════════╗\x1b[0m');
  terminal.writeln('\x1b[1;34m║\x1b[0m     \x1b[1;36mFlux AI Coding Assistant\x1b[0m            \x1b[1;34m║\x1b[0m');
  terminal.writeln('\x1b[1;34m╚════════════════════════════════════════════╝\x1b[0m');
  terminal.writeln('');
  terminal.writeln('\x1b[32m✓\x1b[0m Ready to assist with your coding tasks');
  terminal.writeln('\x1b[2mType a command below or ask Flux anything...\x1b[0m');
  terminal.writeln('');
  
  // Store terminal instance
  terminals.set(tabId, {
    terminal,
    fitAddon,
    state: {
      commandHistory: [],
      historyIndex: -1,
      isProcessing: false,
      outputQueue: [],
      isTyping: false,
      typingTimer: null
    }
  });
  
  // Update tab data (tabManager is available globally now)
  if (window.tabManager && window.tabManager.tabs) {
    const tab = window.tabManager.tabs.get(tabId);
    if (tab) {
      tab.terminal = terminal;
      // Create flux process for this tab
      window.flux.createProcess(tabId, tab.cwd);
    }
  }
  
  return terminal;
}

// Setup global event listeners
function setupGlobalEventListeners() {
  // Resize handler for all terminals
  window.addEventListener('resize', () => {
    terminals.forEach(({ fitAddon }) => {
      if (fitAddon) fitAddon.fit();
    });
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
const typingIndicator = document.getElementById('typing-indicator');

// Show/hide typing indicator
function showTypingIndicator() {
  if (typingIndicator) {
    typingIndicator.style.display = 'block';
  }
}

function hideTypingIndicator() {
  if (typingIndicator) {
    typingIndicator.style.display = 'none';
  }
}

// Update status
function updateStatus(status, text) {
  statusDot.className = `status-dot ${status}`;
  statusText.textContent = text;
  
  // Show typing indicator when processing
  if (status === 'processing') {
    showTypingIndicator();
  } else {
    hideTypingIndicator();
  }
}

// Get active terminal instance and state
function getActiveTerminal() {
  if (!tabManager || !tabManager.activeTabId) return null;
  return terminals.get(tabManager.activeTabId);
}

// Add to history
function addToHistory(command) {
  const activeTerminal = getActiveTerminal();
  if (!activeTerminal) return;
  
  const timestamp = new Date().toLocaleTimeString();
  activeTerminal.state.commandHistory.unshift({ command, timestamp });
  
  // Keep only last 50 commands
  if (activeTerminal.state.commandHistory.length > 50) {
    activeTerminal.state.commandHistory.pop();
  }
  
  // Update history UI
  updateHistoryUI();
  
  // Schedule session save
  if (window.sessionManager) {
    window.sessionManager.scheduleSave();
  }
}

// Update history UI
function updateHistoryUI() {
  const activeTerminal = getActiveTerminal();
  if (!activeTerminal) return;
  
  historyList.innerHTML = activeTerminal.state.commandHistory
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
      commandInput.value = activeTerminal.state.commandHistory[index].command;
      commandInput.focus();
    });
  });
}

// Expose updateHistoryUI globally for session manager
window.updateHistoryUI = updateHistoryUI;

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
  const activeTerminal = getActiveTerminal();
  if (!activeTerminal || !activeTerminal.state.isProcessing) return;
  
  // Send cancel signal to backend for active tab
  window.flux.cancelCommand(tabManager.activeTabId);
  
  // Clear this tab's output queue
  activeTerminal.state.outputQueue = [];
  skipAnimation = false;
  activeTerminal.state.isTyping = false;
  if (activeTerminal.state.typingTimer) {
    clearTimeout(activeTerminal.state.typingTimer);
    activeTerminal.state.typingTimer = null;
  }
  
  // Update UI
  activeTerminal.terminal.writeln('\r\n\x1b[33m^C Command cancelled\x1b[0m');
  activeTerminal.terminal.scrollToBottom();
  updateStatus('', 'Ready');
  activeTerminal.state.isProcessing = false;
  updateSendButton(false);
  hideTypingIndicator();
  stopInactivityCheck();
}

// Send command
function sendCommand() {
  const activeTerminal = getActiveTerminal();
  if (!activeTerminal) return;
  
  // If processing, stop instead of send
  if (activeTerminal.state.isProcessing) {
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
  const activeTerminal = getActiveTerminal();
  if (!activeTerminal) return;
  
  // Clear input
  commandInput.value = '';
  
  // Update status
  updateStatus('processing', 'Processing...');
  activeTerminal.state.isProcessing = true;
  updateSendButton(true);
  
  // Write command to terminal with nice formatting
  activeTerminal.terminal.writeln(`\r\n\x1b[1;36mYou: \x1b[0m${command}`);
  activeTerminal.terminal.scrollToBottom();
  
  // Add to history
  addToHistory(command);
  activeTerminal.state.historyIndex = -1;
  
  // Send to backend with active tab ID
  window.flux.sendCommand(tabManager.activeTabId, command);
  
  // Start inactivity detection
  startInactivityCheck();
}

// Typewriter effect settings
let TYPING_SPEED = 15; // milliseconds per character (adjustable: lower = faster)
let skipAnimation = false;
let lastOutputTime = null;
let inactivityCheckInterval = null;

function typewriterEffectForTab(tabId) {
  const terminalData = terminals.get(tabId);
  if (!terminalData) return;
  
  const { terminal, state } = terminalData;
  
  if (state.outputQueue.length === 0) {
    state.isTyping = false;
    state.typingTimer = null;
    
    // Only update UI if this is the active tab
    if (tabId === tabManager.activeTabId) {
      skipAnimation = false;
      updateStatus('', 'Ready');
      state.isProcessing = false;
      updateSendButton(false);
      hideTypingIndicator();
      stopInactivityCheck();
    }
    return;
  }
  
  state.isTyping = true;
  
  // If skip is requested, flush all at once
  if (skipAnimation && tabId === tabManager.activeTabId) {
    const remainingText = state.outputQueue.join('');
    state.outputQueue = [];
    terminal.write(remainingText);
    terminal.scrollToBottom();
    state.isTyping = false;
    state.typingTimer = null;
    skipAnimation = false;
    updateStatus('', 'Ready');
    state.isProcessing = false;
    updateSendButton(false);
    stopInactivityCheck();
    return;
  }
  
  const char = state.outputQueue.shift();
  terminal.write(char);
  
  // Auto-scroll periodically
  if (state.outputQueue.length % 50 === 0) {
    terminal.scrollToBottom();
  }
  
  state.typingTimer = setTimeout(() => typewriterEffectForTab(tabId), TYPING_SPEED);
}

// Inactivity detection - reset state if no output for 3 seconds after last output
function startInactivityCheck() {
  lastOutputTime = Date.now();
  
  // Clear existing interval
  if (inactivityCheckInterval) {
    clearInterval(inactivityCheckInterval);
  }
  
  inactivityCheckInterval = setInterval(() => {
    const activeTerminal = getActiveTerminal();
    if (!activeTerminal) return;
    
    // If we're still processing but haven't received output in 3 seconds
    if (activeTerminal.state.isProcessing && lastOutputTime) {
      const timeSinceOutput = Date.now() - lastOutputTime;
      if (timeSinceOutput > 3000 && activeTerminal.state.outputQueue.length === 0 && !activeTerminal.state.isTyping) {
        console.log('No output for 3s, resetting processing state');
        clearInterval(inactivityCheckInterval);
        inactivityCheckInterval = null;
        activeTerminal.state.isProcessing = false;
        updateSendButton(false);
        updateStatus('', 'Ready');
      }
    }
  }, 500);
}

function stopInactivityCheck() {
  if (inactivityCheckInterval) {
    clearInterval(inactivityCheckInterval);
    inactivityCheckInterval = null;
  }
  lastOutputTime = null;
}

// Handle flux output with typewriter effect - now with tabId
window.flux.onOutput((tabId, data) => {
  console.log(`Received flux output for tab ${tabId}:`, data.length, 'chars');
  
  // Get terminal for this tab
  const terminalData = terminals.get(tabId);
  if (!terminalData) {
    console.warn(`No terminal found for tab ${tabId}`);
    return;
  }
  
  // Add characters to this tab's queue
  for (let i = 0; i < data.length; i++) {
    terminalData.state.outputQueue.push(data[i]);
  }
  
  // Update last output time if this is the active tab
  if (tabId === tabManager.activeTabId) {
    lastOutputTime = Date.now();
  }
  
  // Start typing animation for this tab if not already typing
  if (!terminalData.state.isTyping) {
    typewriterEffectForTab(tabId);
  }
});

// Handle flux errors - now with tabId
window.flux.onError((tabId, data) => {
  console.error(`Flux error for tab ${tabId}:`, data);
  
  const terminalData = terminals.get(tabId);
  if (terminalData) {
    terminalData.terminal.write(`\x1b[31m${data}\x1b[0m`);
    terminalData.state.isProcessing = false;
  }
  
  // Only update UI if this is the active tab
  if (tabId === tabManager.activeTabId) {
    updateStatus('error', 'Error');
    updateSendButton(false);
    stopInactivityCheck();
  }
});

// Handle flux cancellation - now with tabId
window.flux.onCancelled((tabId) => {
  console.log(`Command cancelled for tab ${tabId}`);
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
    const activeTerminal = getActiveTerminal();
    if (activeTerminal && activeTerminal.state.historyIndex < activeTerminal.state.commandHistory.length - 1) {
      activeTerminal.state.historyIndex++;
      commandInput.value = activeTerminal.state.commandHistory[activeTerminal.state.historyIndex].command;
    }
  }
  
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    const activeTerminal = getActiveTerminal();
    if (activeTerminal) {
      if (activeTerminal.state.historyIndex > 0) {
        activeTerminal.state.historyIndex--;
        commandInput.value = activeTerminal.state.commandHistory[activeTerminal.state.historyIndex].command;
      } else if (activeTerminal.state.historyIndex === 0) {
        activeTerminal.state.historyIndex = -1;
        commandInput.value = '';
      }
    }
  }
});

sendBtn.addEventListener('click', sendCommand);

// Clear button
clearBtn.addEventListener('click', () => {
  const activeTerminal = getActiveTerminal();
  if (!activeTerminal) return;
  
  // Clear any pending output for this tab
  activeTerminal.state.outputQueue = [];
  skipAnimation = false;
  activeTerminal.state.isTyping = false;
  if (activeTerminal.state.typingTimer) {
    clearTimeout(activeTerminal.state.typingTimer);
    activeTerminal.state.typingTimer = null;
  }
  activeTerminal.terminal.clear();
  activeTerminal.terminal.writeln('\x1b[2mTerminal cleared\x1b[0m');
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
    const activeTerminal = getActiveTerminal();
    if (!activeTerminal) return;
    
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
    activeTerminal.terminal.writeln(`\r\n\x1b[90mTyping speed: ${speeds[nextIndex].name}\x1b[0m`);
    activeTerminal.terminal.scrollToBottom();
  });
}

// Focus input on load
commandInput.focus();

} // End of initializeApp
