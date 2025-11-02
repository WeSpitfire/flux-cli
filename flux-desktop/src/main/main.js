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
    if (!win.isDestroyed()) {
      win.webContents.send('flux-output', output);
    }
  });

  fluxProcess.stderr.on('data', (data) => {
    const error = data.toString();
    console.error('[Flux stderr]:', error);
    if (!win.isDestroyed()) {
      win.webContents.send('flux-error', error);
    }
  });

  fluxProcess.on('error', (error) => {
    const errorMsg = `Process error: ${error.message}\n\nTroubleshooting:\n- Ensure Flux CLI is installed: pip install -e .\n- Check that 'flux' command is in PATH\n- Try running 'flux' in terminal to verify`;
    console.error('[Flux process error]:', error);
    if (!win.isDestroyed()) {
      win.webContents.send('flux-error', errorMsg);
    }
  });

  fluxProcess.on('close', (code) => {
    if (code !== 0) {
      const errorMsg = `Flux process exited with code ${code}`;
      console.error('[Flux close]:', errorMsg);
      if (!win.isDestroyed()) {
        win.webContents.send('flux-error', errorMsg);
      }
    }
  });

  ipcMain.on('flux-command', (event, command) => {
    if (fluxProcess && !fluxProcess.killed) {
      fluxProcess.stdin.write(command + '\n');
    }
  });

  ipcMain.on('flux-cancel', (event) => {
    if (fluxProcess && !fluxProcess.killed) {
      // Send Ctrl+C (SIGINT) to interrupt the process
      fluxProcess.kill('SIGINT');
      if (!win.isDestroyed()) {
        win.webContents.send('flux-cancelled');
      }
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

ipcMain.handle('search-files', async (event, { directory, query, maxResults = 50 }) => {
  const results = [];
  const ignoredDirs = new Set(['node_modules', '.git', 'dist', 'build', 'venv', '__pycache__', '.DS_Store']);
  const ignoredFiles = new Set(['.gitignore', '.DS_Store']);
  
  async function searchDir(dir, depth = 0) {
    if (depth > 10) return; // Limit depth to prevent infinite recursion
    if (results.length >= maxResults) return; // Stop if we have enough results
    
    try {
      const entries = await fs.promises.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        if (results.length >= maxResults) break;
        
        // Skip ignored files/dirs
        if (ignoredDirs.has(entry.name) || ignoredFiles.has(entry.name)) continue;
        if (entry.name.startsWith('.') && entry.name !== '.') continue; // Skip hidden files except .
        
        const fullPath = path.join(dir, entry.name);
        const relativePath = path.relative(directory, fullPath);
        
        if (entry.isDirectory()) {
          // Recursively search subdirectories
          await searchDir(fullPath, depth + 1);
        } else if (entry.isFile()) {
          // Check if filename matches query
          const lowerName = entry.name.toLowerCase();
          const lowerQuery = query.toLowerCase();
          
          if (lowerName.includes(lowerQuery)) {
            results.push({
              name: entry.name,
              path: relativePath,
              fullPath: fullPath,
              type: getFileType(entry.name)
            });
          }
        }
      }
    } catch (err) {
      // Silently skip directories we can't read
      console.error('Error reading directory:', dir, err.message);
    }
  }
  
  function getFileType(filename) {
    const ext = path.extname(filename).toLowerCase();
    const typeMap = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.py': 'python',
      '.java': 'java',
      '.c': 'c',
      '.cpp': 'cpp',
      '.h': 'header',
      '.css': 'stylesheet',
      '.scss': 'stylesheet',
      '.html': 'html',
      '.json': 'json',
      '.md': 'markdown',
      '.txt': 'text',
      '.yaml': 'config',
      '.yml': 'config',
      '.toml': 'config',
      '.xml': 'xml',
      '.svg': 'image',
      '.png': 'image',
      '.jpg': 'image',
      '.gif': 'image'
    };
    return typeMap[ext] || 'file';
  }
  
  await searchDir(directory);
  return results;
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
