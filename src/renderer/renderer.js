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