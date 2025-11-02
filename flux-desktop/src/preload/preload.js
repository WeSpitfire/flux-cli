const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('flux', {
  createProcess: (tabId, cwd) => {
    ipcRenderer.send('flux-create-process', { tabId, cwd });
  },
  
  destroyProcess: (tabId) => {
    ipcRenderer.send('flux-destroy-process', { tabId });
  },
  
  sendCommand: (tabId, command) => {
    ipcRenderer.send('flux-command', { tabId, command });
  },
  
  cancelCommand: (tabId) => {
    ipcRenderer.send('flux-cancel', { tabId });
  },
  
  onOutput: (callback) => {
    ipcRenderer.on('flux-output', (_, { tabId, data }) => {
      callback(tabId, data);
    });
  },
  
  onError: (callback) => {
    ipcRenderer.on('flux-error', (_, { tabId, data }) => {
      callback(tabId, data);
    });
  },
  
  getCodebaseStats: () => ipcRenderer.invoke('get-codebase-stats'),

  onCancelled: (callback) => {
    ipcRenderer.on('flux-cancelled', (_, { tabId }) => {
      callback(tabId);
    });
  }
});

// Expose codebase API
contextBridge.exposeInMainWorld('codebase', {
  getGraph: () => ipcRenderer.invoke('get-codebase-stats')
});

// Expose file system API
contextBridge.exposeInMainWorld('fileSystem', {
  readDir: (dirPath) => ipcRenderer.invoke('read-dir', dirPath),
  isDirectory: (filePath) => ipcRenderer.invoke('is-directory', filePath),
  joinPath: (...paths) => ipcRenderer.invoke('join-path', ...paths),
  getCwd: () => ipcRenderer.invoke('get-cwd'),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  searchFiles: (directory, query, maxResults) => ipcRenderer.invoke('search-files', { directory, query, maxResults })
});
