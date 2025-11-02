const { ipcRenderer } = require('electron');

// Expose Flux API to renderer
window.flux = {
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
  
  onCancelled: (callback) => {
    ipcRenderer.on('flux-cancelled', (_, { tabId }) => {
      callback(tabId);
    });
  }
};

// Expose file system API
window.fileSystem = {
  readDir: (dirPath) => ipcRenderer.invoke('read-dir', dirPath),
  isDirectory: (filePath) => ipcRenderer.invoke('is-directory', filePath),
  joinPath: (...paths) => ipcRenderer.invoke('join-path', ...paths),
  getCwd: () => ipcRenderer.invoke('get-cwd'),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  searchFiles: (directory, query, maxResults) => ipcRenderer.invoke('search-files', { directory, query, maxResults })
};
