const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let fluxProcess = null;

function createWindow () {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    backgroundColor: '#1a1b26',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  win.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

  // Spawn Flux CLI process in interactive mode
  const projectRoot = path.join(__dirname, '../../..');
  const venvFluxPath = path.join(projectRoot, 'venv', 'bin', 'flux');
  
  const fluxCommand = fs.existsSync(venvFluxPath) ? venvFluxPath : 'flux';
  
  console.log('Spawning Flux CLI from:', projectRoot);
  console.log('Flux command:', fluxCommand);
  
  fluxProcess = spawn(fluxCommand, [], {
    cwd: projectRoot,
    env: { 
      ...process.env,
      PYTHONUNBUFFERED: '1',
      FORCE_COLOR: '1',
      TERM: 'xterm-256color'
    },
    shell: false
  });

  fluxProcess.stdout.on('data', (data) => {
    const output = data.toString();
    console.log('[Flux stdout]:', output);
    win.webContents.send('flux-output', output);
  });

  fluxProcess.stderr.on('data', (data) => {
    const error = data.toString();
    console.error('[Flux stderr]:', error);
    win.webContents.send('flux-error', error);
  });

  fluxProcess.on('error', (error) => {
    const errorMsg = `Process error: ${error.message}\n\nTroubleshooting:\n- Ensure Flux CLI is installed: pip install -e .\n- Check that 'flux' command is in PATH\n- Try running 'flux' in terminal to verify`;
    console.error('[Flux process error]:', error);
    win.webContents.send('flux-error', errorMsg);
  });

  fluxProcess.on('close', (code) => {
    if (code !== 0) {
      const errorMsg = `Flux process exited with code ${code}`;
      console.error('[Flux close]:', errorMsg);
      win.webContents.send('flux-error', errorMsg);
    }
  });

  ipcMain.on('flux-command', (event, command) => {
    if (fluxProcess && !fluxProcess.killed) {
      fluxProcess.stdin.write(command + '\n');
    }
  });

  if (process.argv.includes('--dev')) {
    win.webContents.openDevTools();
  }

  return win;
}

ipcMain.handle('read-dir', async (event, dirPath) => {
  try {
    return await fs.promises.readdir(dirPath);
  } catch (err) {
    console.error('Error reading directory:', err);
    return [];
  }
});

ipcMain.handle('is-directory', async (event, filePath) => {
  try {
    const stats = await fs.promises.stat(filePath);
    return stats.isDirectory();
  } catch (err) {
    return false;
  }
});

ipcMain.handle('join-path', async (event, ...paths) => {
  return path.join(...paths);
});

ipcMain.handle('get-cwd', async () => {
  return process.cwd();
});

ipcMain.handle('select-directory', async () => {
  const { dialog } = require('electron');
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (fluxProcess && !fluxProcess.killed) {
    fluxProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  if (fluxProcess && !fluxProcess.killed) {
    fluxProcess.kill();
  }
});
