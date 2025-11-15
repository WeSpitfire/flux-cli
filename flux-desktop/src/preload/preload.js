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
  
  onTreeEvent: (callback) => {
    ipcRenderer.on('flux-tree-event', (_, { tabId, event, data }) => {
      callback(tabId, event, data);
    });
  },
  
  getCodebaseStats: () => ipcRenderer.invoke('get-codebase-stats'),

  onCancelled: (callback) => {
    ipcRenderer.on('flux-cancelled', (_, { tabId }) => {
      callback(tabId);
    });
  },
  
  openSettings: () => {
    ipcRenderer.send('open-settings');
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

// Expose electron API for file actions
contextBridge.exposeInMainWorld('electron', {
  openInEditor: (filePath) => ipcRenderer.invoke('open-in-editor', filePath),
  showInFinder: (filePath) => ipcRenderer.invoke('show-in-finder', filePath)
});

// Expose settings API
contextBridge.exposeInMainWorld('settings', {
  get: () => ipcRenderer.invoke('settings:get'),
  getApiKey: (provider) => ipcRenderer.invoke('settings:getApiKey', provider),
  setApiKey: (provider, key) => ipcRenderer.invoke('settings:setApiKey', { provider, key }),
  setProvider: (provider) => ipcRenderer.invoke('settings:setProvider', provider),
  setModel: (model) => ipcRenderer.invoke('settings:setModel', model),
  setLLMSettings: (settings) => ipcRenderer.invoke('settings:setLLMSettings', settings),
  setAppearance: (appearance) => ipcRenderer.invoke('settings:setAppearance', appearance),
  setExperimental: (features) => ipcRenderer.invoke('settings:setExperimental', features),
  testConnection: (provider) => ipcRenderer.invoke('settings:testConnection', provider),
  getAvailableModels: (provider) => ipcRenderer.invoke('settings:getAvailableModels', provider),
  reset: () => ipcRenderer.invoke('settings:reset'),
  getPath: () => ipcRenderer.invoke('settings:getPath'),
  applyTheme: (theme) => ipcRenderer.invoke('settings:applyTheme', theme),
  onThemeChange: (callback) => ipcRenderer.on('theme-changed', (_, theme) => callback(theme))
});
