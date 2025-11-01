const { ipcRenderer } = require('electron');

// Expose Flux API to renderer
window.flux = {
  sendCommand: (command) => {
    ipcRenderer.send('flux-command', command);
  },
  
  onOutput: (callback) => {
    ipcRenderer.on('flux-output', (_, data) => {
      callback(data);
    });
  },
  
  onError: (callback) => {
    ipcRenderer.on('flux-error', (_, data) => {
      callback(data);
    });
  }
};

// Expose file system API
window.fileSystem = {
  readDir: (dirPath) => ipcRenderer.invoke('read-dir', dirPath),
  isDirectory: (filePath) => ipcRenderer.invoke('is-directory', filePath),
  joinPath: (...paths) => ipcRenderer.invoke('join-path', ...paths),
  getCwd: () => ipcRenderer.invoke('get-cwd'),
  selectDirectory: () => ipcRenderer.invoke('select-directory')
};
