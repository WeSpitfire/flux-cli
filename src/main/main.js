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

app.whenReady().then(createWindow);

// ... (existing code)