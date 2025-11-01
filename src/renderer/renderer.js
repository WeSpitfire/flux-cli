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

// Expose session API
window.session = {
  save: () => window.session.save(sessionTracker.getCurrentState()),
  load: (id) => window.session.load(id).then((state) => {
    // Restore session state
  }),
  list: () => window.session.list()
};