const { remote } = require('electron');
const fs = require('fs');
const path = require('path');

class SessionTracker {
  constructor() {
    this.terminalHistory = [];
    this.commandHistory = [];
    this.fileExplorerState = {
      currentPath: '/',
      expandedPaths: []
    };
    this.settings = {
      typingSpeed: 15
    };
  }

  trackTerminalOutput(output) {
    this.terminalHistory.push({
      type: 'output',
      content: output,
      timestamp: new Date().toISOString()
    });
  }

  trackCommand(command) {
    this.commandHistory.push({
      command,
      timestamp: new Date().toISOString()
    });
  }

  updateFileExplorerState(currentPath, expandedPaths) {
    this.fileExplorerState = {
      currentPath,
      expandedPaths
    };
  }

  updateSettings(settings) {
    this.settings = settings;
  }

  getCurrentState() {
    return {
      terminalHistory: this.terminalHistory,
      commandHistory: this.commandHistory,
      fileExplorerState: this.fileExplorerState,
      settings: this.settings
    };
  }
}

const sessionTracker = new SessionTracker();

// Track terminal output
remote.getCurrentWindow().webContents.on('did-finish-load', () => {
  remote.getCurrentWindow().webContents.on('console-message', (event, level, message) => {
    sessionTracker.trackTerminalOutput(message);
  });
});

// Track command history
remote.getCurrentWindow().webContents.on('ipc-message', (event, channel, ...args) => {
  if (channel === 'flux-command') {
    sessionTracker.trackCommand(args[0]);
  }
});

// Track file explorer state
// (implement this)

// Initialize xterm.js for terminal
const { Terminal } = require('xterm');
require('xterm/css/xterm.css');

const terminalContainer = document.createElement('div');
terminalContainer.id = 'terminal-container';
document.body.appendChild(terminalContainer);

const terminal = new Terminal({
  cursorBlink: true,
  theme: {
    background: '#1e1e1e', // Dark background
    foreground: '#dcdcdc', // Light text
    cursor: '#c678dd', // Cursor color
    selection: '#44475a', // Selection color
    black: '#282c34',
    red: '#e06c75',
    green: '#98c379',
    yellow: '#e5c07b',
    blue: '#61afef',
    magenta: '#c678dd',
    cyan: '#56b6c2',
    white: '#abb2bf',
    brightBlack: '#5c6370',
    brightRed: '#e06c75',
    brightGreen: '#98c379',
    brightYellow: '#e5c07b',
    brightBlue: '#61afef',
    brightMagenta: '#c678dd',
    brightCyan: '#56b6c2',
    brightWhite: '#ffffff'
  }
});

terminal.open(terminalContainer);

function applyOutputColor(type, message) {
  switch (type) {
    case 'command':
      terminal.writeln(`\x1b[34m${message}\x1b[0m`); // Blue for commands
      break;
    case 'output':
      terminal.writeln(message); // Default color for output
      break;
    case 'error':
      terminal.writeln(`\x1b[31m${message}\x1b[0m`); // Red for errors
      break;
    default:
      terminal.writeln(message);
  }
}

// Example usage
applyOutputColor('command', 'echo Hello, World!');
applyOutputColor('output', 'Hello, World!');
applyOutputColor('error', 'Error: Something went wrong');

// Function to toggle themes
function toggleTheme(theme) {
  const themes = {
    dark: {
      background: '#1e1e1e',
      foreground: '#dcdcdc',
      cursor: '#c678dd',
      selection: '#44475a',
      black: '#282c34',
      red: '#e06c75',
      green: '#98c379',
      yellow: '#e5c07b',
      blue: '#61afef',
      magenta: '#c678dd',
      cyan: '#56b6c2',
      white: '#abb2bf',
      brightBlack: '#5c6370',
      brightRed: '#e06c75',
      brightGreen: '#98c379',
      brightYellow: '#e5c07b',
      brightBlue: '#61afef',
      brightMagenta: '#c678dd',
      brightCyan: '#56b6c2',
      brightWhite: '#ffffff'
    },
    light: {
      background: '#ffffff',
      foreground: '#000000',
      cursor: '#000000',
      selection: '#dcdcdc',
      black: '#000000',
      red: '#d70000',
      green: '#5f8700',
      yellow: '#af8700',
      blue: '#0087ff',
      magenta: '#af005f',
      cyan: '#00afaf',
      white: '#e4e4e4',
      brightBlack: '#4e4e4e',
      brightRed: '#ff0000',
      brightGreen: '#87d700',
      brightYellow: '#ffd700',
      brightBlue: '#5fafff',
      brightMagenta: '#ff5faf',
      brightCyan: '#5fffff',
      brightWhite: '#ffffff'
    }
  };
  terminal.setOption('theme', themes[theme]);
}

// Add event listener for theme toggle
const themeToggle = document.createElement('button');
themeToggle.innerText = 'Toggle Theme';
document.body.appendChild(themeToggle);
themeToggle.addEventListener('click', () => {
  const currentTheme = terminal.getOption('theme').background === '#1e1e1e' ? 'light' : 'dark';
  toggleTheme(currentTheme);
});

// Initialize UI for model selection
function initializeUI() {
  const modelSelect = document.createElement('select');
  modelSelect.id = 'modelSelect';

  const openAIOption = document.createElement('option');
  openAIOption.value = 'openai';
  openAIOption.text = 'OpenAI';
  modelSelect.appendChild(openAIOption);

  const claudeOption = document.createElement('option');
  claudeOption.value = 'claude';
  claudeOption.text = 'Claude';
  modelSelect.appendChild(claudeOption);

  document.body.appendChild(modelSelect);

  // Add event listener to handle model selection
  modelSelect.addEventListener('change', (event) => {
    const selectedModel = event.target.value;
    console.log(`Selected model: ${selectedModel}`);
    // You can send an IPC message here to update the main process
    // ipcRenderer.send('model-switch', selectedModel);
  });
}

// Call the function to initialize the UI
initializeUI();

// Expose session API
window.session = {
  save: () => window.session.save(sessionTracker.getCurrentState()),
  load: (id) => window.session.load(id).then((state) => {
    // Restore session state
  }),
  list: () => window.session.list()
};