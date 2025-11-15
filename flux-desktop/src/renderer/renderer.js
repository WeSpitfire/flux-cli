// xterm modules are loaded via script tags in index.html
// Access them from global scope
const Terminal = window.Terminal;
const FitAddon = window.FitAddon.FitAddon;
const WebLinksAddon = window.WebLinksAddon.WebLinksAddon;

// Global state for tab management
const terminals = new Map(); // tabId -> terminal instance
let tabManager = null;
let sessionManager = null;
let terminalFormatter = null;

// Expose terminals globally for session management
window.terminals = terminals;

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

async function initializeApp() {
  // Load appearance settings
  try {
    const settings = await window.settings.get();
    if (settings.appearance) {
      // Load typing speed
      if (settings.appearance.typingSpeed !== undefined) {
        const speeds = [0, 5, 10, 15, 25, 40];
        TYPING_SPEED = speeds[settings.appearance.typingSpeed] || 15;
        console.log('[Settings] Loaded typing speed:', TYPING_SPEED, 'ms');
      }
      
      // Load and apply theme
      const theme = settings.appearance.theme || 'dark';
      applyTheme(theme);
      console.log('[Settings] Loaded theme:', theme);
    }
  } catch (error) {
    console.warn('[Settings] Failed to load appearance settings, using defaults:', error);
  }
  
  // Initialize TabManager first
  tabManager = new window.TabManager();
  
  // Expose globally for cross-file access
  window.tabManager = tabManager;
  
  // Initialize Terminal Formatter
  terminalFormatter = new window.TerminalFormatter();
  
  // Expose initialization function for TabManager to call
  window.initializeTerminalForTab = initializeTerminalForTab;
  
  // Initialize SessionManager and restore previous session
  sessionManager = new window.SessionManager();
  sessionManager.init(tabManager);
  window.sessionManager = sessionManager;
  
  // Setup global event listeners
  setupGlobalEventListeners();
  
  // Listen for theme changes from settings window
  if (window.settings && window.settings.onThemeChange) {
    window.settings.onThemeChange((theme) => {
      console.log('[Settings] Theme change received:', theme);
      applyTheme(theme);
    });
  }
}

// Create terminal configuration
function getTerminalConfig() {
  return {
    theme: {
      background: '#0d1117',
      foreground: '#e6edf3',
      cursor: '#58a6ff',
      cursorAccent: '#0d1117',
      selection: 'rgba(88, 166, 255, 0.3)',
      black: '#0d1117',
      red: '#ff7b72',
      green: '#3fb950',
      yellow: '#d29922',
      blue: '#58a6ff',
      magenta: '#bc8cff',
      cyan: '#39c5cf',
      white: '#e6edf3',
      brightBlack: '#6e7681',
      brightRed: '#ffa198',
      brightGreen: '#56d364',
      brightYellow: '#e3b341',
      brightBlue: '#79c0ff',
      brightMagenta: '#d2a8ff',
      brightCyan: '#56d4dd',
      brightWhite: '#f0f6fc'
    },
    fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Monaco', monospace",
    fontSize: 14,
    lineHeight: 1.6,
    letterSpacing: 0.5,
    cursorBlink: true,
    cursorStyle: 'block',
    scrollback: 10000,
    allowTransparency: true,
    convertEol: true,
    fontWeight: 400,
    fontWeightBold: 600
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
  
  // Minimal startup - just the logo
  terminal.writeln('\x1b[38;5;110m⚡ Flux\x1b[0m');
  
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
      typingTimer: null,
      hasFluxHeader: false,
      outputBuffer: '', // Buffer for formatting
      lastOutputTime: Date.now()
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

// Auto-expand textarea as user types
function autoExpandTextarea() {
  commandInput.style.height = 'auto';
  commandInput.style.height = Math.min(commandInput.scrollHeight, 200) + 'px';
}

// Setup textarea auto-expand
if (commandInput) {
  commandInput.addEventListener('input', autoExpandTextarea);
  // Also handle paste
  commandInput.addEventListener('paste', () => {
    setTimeout(autoExpandTextarea, 0);
  });
}

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

// Update status - simple and clean
function updateStatus(status, text) {
  statusDot.className = `status-dot ${status}`;
  
  if (status === 'processing') {
    statusText.textContent = 'Thinking...';
    showTypingIndicator();
  } else {
    statusText.textContent = text || 'Ready';
    hideTypingIndicator();
  }
}

// Auto-fix notification system
let autoFixNotificationTimeout = null;

function showAutoFixNotification(filePath, fixCount, fixTypes) {
  // Don't show during active processing
  const activeTerminal = getActiveTerminal();
  if (activeTerminal && activeTerminal.state.isProcessing) {
    return;
  }
  
  // Clear any existing notification timeout
  if (autoFixNotificationTimeout) {
    clearTimeout(autoFixNotificationTimeout);
  }
  
  // Show notification in status bar
  const message = `✨ Fixed ${filePath} (${fixCount} fix)`;
  statusDot.className = 'status-dot success';
  statusText.textContent = message;
  statusText.title = `Fixed: ${fixTypes}`; // Show details on hover
  
  // Add visual feedback
  statusDot.style.animation = 'pulse 0.5s ease-in-out';
  
  // Clear the notification after 5 seconds
  autoFixNotificationTimeout = setTimeout(() => {
    if (!activeTerminal || !activeTerminal.state.isProcessing) {
      statusDot.className = 'status-dot';
      statusText.textContent = 'Ready';
      statusText.title = '';
      statusDot.style.animation = '';
    }
  }, 5000);
}

// Status rotation functions removed - keeping it simple

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
  
  // Clear input and reset height
  commandInput.value = '';
  commandInput.style.height = 'auto';
  
  // Update status
  updateStatus('processing', 'Processing...');
  activeTerminal.state.isProcessing = true;
  updateSendButton(true);
  
  // Write command to terminal with simple formatting
  activeTerminal.terminal.writeln('');
  activeTerminal.terminal.writeln('\x1b[2m─\x1b[0m');
  activeTerminal.terminal.write('\x1b[38;5;153m→ \x1b[0m');
  activeTerminal.terminal.write(command);
  activeTerminal.terminal.writeln('');
  activeTerminal.terminal.writeln('');
  activeTerminal.terminal.scrollToBottom();
  
  // Add to history
  addToHistory(command);
  activeTerminal.state.historyIndex = -1;
  
  // For multi-line commands, encode newlines so they arrive as a single line
  // Flux will decode them on the other end
  const hasNewlines = command.includes('\n');
  
  if (hasNewlines) {
    // Replace actual newlines with placeholder that won't be split
    const encoded = command.replace(/\n/g, '<<<NEWLINE>>>');
    window.flux.sendCommand(tabManager.activeTabId, encoded);
  } else {
    // Send single-line command directly
    window.flux.sendCommand(tabManager.activeTabId, command);
  }
  
  // Start inactivity detection
  startInactivityCheck();
}

// Typewriter effect settings
let TYPING_SPEED = 0; // milliseconds per character (0 = instant, adjustable: lower = faster)
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
    
    // Clear buffer (already processed and added to queue by onOutput handler)
    state.outputBuffer = '';
    state.hasFluxHeader = false; // Reset header flag
    
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
  
  // If instant mode (TYPING_SPEED = 0) or skip requested, flush all at once
  if (TYPING_SPEED === 0 || (skipAnimation && tabId === tabManager.activeTabId)) {
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
  
  // Character-by-character mode (for slower typing speeds)
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

// Word wrapping helper function
function wrapText(text, maxWidth) {
  // Don't wrap if text contains ANSI codes (formatting)
  if (text.includes('\x1b[')) {
    return text;
  }
  
  const lines = [];
  const paragraphs = text.split('\n');
  
  for (const paragraph of paragraphs) {
    if (paragraph.length <= maxWidth) {
      lines.push(paragraph);
      continue;
    }
    
    let currentLine = '';
    const words = paragraph.split(' ');
    
    for (const word of words) {
      // If word itself is longer than maxWidth, just add it
      if (word.length > maxWidth) {
        if (currentLine) {
          lines.push(currentLine);
          currentLine = '';
        }
        lines.push(word);
        continue;
      }
      
      // Check if adding this word would exceed the width
      const testLine = currentLine ? currentLine + ' ' + word : word;
      if (testLine.length <= maxWidth) {
        currentLine = testLine;
      } else {
        // Push current line and start new one with this word
        if (currentLine) {
          lines.push(currentLine);
        }
        currentLine = word;
      }
    }
    
    // Push remaining line
    if (currentLine) {
      lines.push(currentLine);
    }
  }
  
  return lines.join('\r\n');
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
  
  // Detect auto-fix notifications and show in status bar
  const autoFixMatch = data.match(/✨ Auto-fixed (.+?) \((\d+) fix: (.+?)\)/);
  if (autoFixMatch && tabId === tabManager.activeTabId) {
    const [, filePath, fixCount, fixTypes] = autoFixMatch;
    showAutoFixNotification(filePath, parseInt(fixCount), fixTypes);
  }
  
  // No header needed - keep output clean
  
  // Add to buffer for formatting
  terminalData.state.outputBuffer += data;
  terminalData.state.lastOutputTime = Date.now();
  
  // Check if we should format the buffer
  // Format when we detect complete code blocks or after a pause
  const shouldFormat = terminalFormatter.hasCodeBlock(terminalData.state.outputBuffer);
  
  if (shouldFormat) {
    // Format the buffer
    const formatted = terminalFormatter.formatOutput(terminalData.state.outputBuffer);
    
    // Clear buffer and add formatted output to queue
    terminalData.state.outputBuffer = '';
    for (let i = 0; i < formatted.length; i++) {
      terminalData.state.outputQueue.push(formatted[i]);
    }
  } else {
    // Wrap the data to prevent word splitting
    const termWidth = terminalData.terminal.cols - 2; // Leave margin
    const wrappedData = wrapText(data, termWidth);
    
    // Add wrapped data to queue
    for (let i = 0; i < wrappedData.length; i++) {
      terminalData.state.outputQueue.push(wrappedData[i]);
    }
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

// Input event handlers
commandInput.addEventListener('keydown', (e) => {
  // Send on Enter (without Shift)
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendCommand();
  } else if (e.key === 'Enter' && e.shiftKey) {
    // Allow Shift+Enter for new line, then auto-expand
    setTimeout(autoExpandTextarea, 0);
  }
  
  // Skip animation on Ctrl+C or Escape
  if ((e.key === 'c' && (e.ctrlKey || e.metaKey)) || e.key === 'Escape') {
    const activeTerminal = getActiveTerminal();
    if (activeTerminal && activeTerminal.state.isTyping) {
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

// Settings button - open settings window
const settingsBtn = document.getElementById('settings-btn');
console.log('[Settings] Settings button found:', settingsBtn);
if (settingsBtn) {
  settingsBtn.addEventListener('click', () => {
    console.log('[Settings] Opening settings window...');
    window.flux.openSettings();
  });
  console.log('[Settings] Settings button handler attached');
} else {
  console.error('[Settings] Settings button not found in DOM!');
}

// Apply theme (used for initial load and theme changes)
function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === 'light') {
    root.classList.add('light-theme');
    updateAllTerminalThemes('light');
  } else {
    root.classList.remove('light-theme');
    updateAllTerminalThemes('dark');
  }
}

// Theme toggle functionality (toggles between light and dark)
window.toggleTheme = function() {
  const root = document.documentElement;
  const isLightTheme = root.classList.contains('light-theme');
  
  if (isLightTheme) {
    applyTheme('dark');
  } else {
    applyTheme('light');
  }
};

function updateAllTerminalThemes(theme) {
  const themes = {
    dark: {
      background: '#0d1117',
      foreground: '#e6edf3',
      cursor: '#58a6ff',
      cursorAccent: '#0d1117',
      selection: 'rgba(88, 166, 255, 0.3)',
      black: '#0d1117',
      red: '#ff7b72',
      green: '#3fb950',
      yellow: '#d29922',
      blue: '#58a6ff',
      magenta: '#bc8cff',
      cyan: '#39c5cf',
      white: '#e6edf3',
      brightBlack: '#6e7681',
      brightRed: '#ffa198',
      brightGreen: '#56d364',
      brightYellow: '#e3b341',
      brightBlue: '#79c0ff',
      brightMagenta: '#d2a8ff',
      brightCyan: '#56d4dd',
      brightWhite: '#f0f6fc'
    },
    light: {
      background: '#ffffff',
      foreground: '#1f2328',
      cursor: '#0969da',
      cursorAccent: '#ffffff',
      selection: 'rgba(9, 105, 218, 0.2)',
      black: '#1f2328',
      red: '#d1242f',
      green: '#116329',
      yellow: '#953800',
      blue: '#0969da',
      magenta: '#8250df',
      cyan: '#1b7c83',
      white: '#6e7781',
      brightBlack: '#656d76',
      brightRed: '#ff7b72',
      brightGreen: '#3fb950',
      brightYellow: '#d29922',
      brightBlue: '#58a6ff',
      brightMagenta: '#bc8cff',
      brightCyan: '#39c5cf',
      brightWhite: '#ffffff'
    }
  };
  
  // Update all terminal instances
  terminals.forEach(({ terminal }) => {
    if (terminal) {
      terminal.options.theme = themes[theme];
    }
  });
}

// Focus input on load
commandInput.focus();

} // End of initializeApp
