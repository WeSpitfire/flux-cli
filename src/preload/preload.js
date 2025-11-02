const { ipcRenderer } = require('electron');

window.modelSwitcher = {
  switchModel: (model) => ipcRenderer.send('model-switch', model)
};

window.session = {
  save: (data) => ipcRenderer.invoke('save-session', data),
  load: (id) => ipcRenderer.invoke('load-session', id),
  list: () => ipcRenderer.invoke('list-sessions')
};