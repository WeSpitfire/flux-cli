const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const SessionManager = require('./session-manager');
const sessionManager = new SessionManager();

let fluxProcess = null;

function createWindow () {
  // ... (existing code)
}

ipcMain.handle('save-session', (event, sessionData) => {
  sessionManager.saveSession(sessionData);
});

ipcMain.handle('load-session', (event, sessionId) => {
  return sessionManager.loadSession(sessionId);
});

ipcMain.handle('list-sessions', (event) => {
  return sessionManager.listSessions();
});

// Auto-save session every 5 minutes
setInterval(() => {
  sessionManager.saveSession(getCurrentState());
}, 5 * 60 * 1000);

// Auto-save on app quit
app.on('before-quit', () => {
  sessionManager.saveSession(getCurrentState());
});

// Auto-load latest session on startup (optional)
app.on('ready', () => {
  const latestSession = sessionManager.getLatestSession();
  if (latestSession) {
    sessionManager.loadSession(latestSession.id);
  }
});

// IPC handler to get codebase stats from Flux CLI
ipcMain.handle('get-codebase-stats', async () => {
  return new Promise((resolve, reject) => {
    const fluxProcess = spawn('flux', ['--stats'], { shell: true });

    let output = '';
    fluxProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    fluxProcess.stderr.on('data', (data) => {
      console.error('Flux CLI error:', data.toString());
    });

    fluxProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const stats = JSON.parse(output);
          resolve(stats);
        } catch (error) {
          reject('Failed to parse stats output');
        }
      } else {
        reject('Flux CLI exited with code ' + code);
      }
    });
  });
});

app.whenReady().then(createWindow);

// ... (existing code)