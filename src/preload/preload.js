const { ipcRenderer } = require('electron');

window.session = {
  save: (data) => ipcRenderer.invoke('save-session', data),
  load: (id) => ipcRenderer.invoke('load-session', id),
  list: () => ipcRenderer.invoke('list-sessions')
};