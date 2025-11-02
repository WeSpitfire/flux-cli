const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Map of tabId -> flux process
const fluxProcesses = new Map();

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

  // Helper to spawn a new Flux process for a tab
  function spawnFluxForTab(tabId, cwd) {
    const projectRoot = path.resolve(path.join(__dirname, '../../..'));
    const venvFluxPath = path.resolve(path.join(projectRoot, 'venv', 'bin', 'flux'));
    const fluxExists = fs.existsSync(venvFluxPath);
    const fluxCommand = fluxExists ? venvFluxPath : 'flux';
    
    // Expand tilde in cwd if present
    let workingDir = cwd || projectRoot;
    if (workingDir.startsWith('~/') || workingDir === '~') {
      const homeDir = require('os').homedir();
      workingDir = path.join(homeDir, workingDir.slice(2)); // Remove ~/ and join with home
    }
    // If it's not an absolute path, resolve it
    if (!path.isAbsolute(workingDir)) {
      workingDir = path.resolve(workingDir);
    }
    
    console.log(`[Tab ${tabId}] Project root:`, projectRoot);
    console.log(`[Tab ${tabId}] Venv flux path:`, venvFluxPath);
    console.log(`[Tab ${tabId}] Flux exists:`, fluxExists);
    console.log(`[Tab ${tabId}] Using command:`, fluxCommand);
    console.log(`[Tab ${tabId}] Working directory (original):`, cwd);
    console.log(`[Tab ${tabId}] Working directory (expanded):`, workingDir);
    
    const fluxProcess = spawn(fluxCommand, [], {
      cwd: workingDir,
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
      console.log(`[Flux ${tabId} stdout]:`, output);
      if (!win.isDestroyed()) {
        win.webContents.send('flux-output', { tabId, data: output });
      }
    });

    fluxProcess.stderr.on('data', (data) => {
      const error = data.toString();
      console.error(`[Flux ${tabId} stderr]:`, error);
      if (!win.isDestroyed()) {
        win.webContents.send('flux-error', { tabId, data: error });
      }
    });

    fluxProcess.on('error', (error) => {
      const errorMsg = `Process error: ${error.message}\n\nTroubleshooting:\n- Ensure Flux CLI is installed: pip install -e .\n- Check that 'flux' command is in PATH\n- Try running 'flux' in terminal to verify`;
      console.error(`[Flux ${tabId} process error]:`, error);
      if (!win.isDestroyed()) {
        win.webContents.send('flux-error', { tabId, data: errorMsg });
      }
    });

    fluxProcess.on('close', (code) => {
      console.log(`[Flux ${tabId}] Process closed with code ${code}`);
      fluxProcesses.delete(tabId);
      
      if (code !== 0 && !win.isDestroyed()) {
        const errorMsg = `Flux process exited with code ${code}`;
        win.webContents.send('flux-error', { tabId, data: errorMsg });
      }
    });

    fluxProcesses.set(tabId, { process: fluxProcess, cwd: workingDir });
    return fluxProcess;
  }

  // IPC handlers for tab-specific flux processes
  ipcMain.on('flux-create-process', (event, { tabId, cwd }) => {
    console.log('Creating flux process for tab:', tabId);
    spawnFluxForTab(tabId, cwd);
  });

  ipcMain.on('flux-command', (event, { tabId, command }) => {
    const fluxData = fluxProcesses.get(tabId);
    if (fluxData && fluxData.process && !fluxData.process.killed) {
      console.log(`Sending command to tab ${tabId}:`, command);
      fluxData.process.stdin.write(command + '\n');
    } else {
      console.error(`No flux process found for tab ${tabId}`);
    }
  });

  ipcMain.on('flux-cancel', (event, { tabId }) => {
    const fluxData = fluxProcesses.get(tabId);
    if (fluxData && fluxData.process && !fluxData.process.killed) {
      console.log(`Cancelling command for tab ${tabId}`);
      
      // Store the cwd before killing process
      const savedCwd = fluxData.cwd;
      
      // Kill the process
      fluxData.process.kill('SIGINT');
      
      // Wait a bit for process to die, then respawn in same directory
      setTimeout(() => {
        console.log(`Respawning flux process for tab ${tabId} in ${savedCwd}`);
        spawnFluxForTab(tabId, savedCwd);
        if (!win.isDestroyed()) {
          win.webContents.send('flux-cancelled', { tabId });
        }
      }, 100);
    }
  });

  ipcMain.on('flux-destroy-process', (event, { tabId }) => {
    const fluxData = fluxProcesses.get(tabId);
    if (fluxData && fluxData.process && !fluxData.process.killed) {
      console.log(`Destroying flux process for tab ${tabId}`);
      fluxData.process.kill();
      fluxProcesses.delete(tabId);
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

// IPC handler to request graph data from a specific Flux process
ipcMain.handle('request-graph-data', async (event, tabId) => {
  return new Promise((resolve, reject) => {
    const fluxData = fluxProcesses.get(tabId);
    if (fluxData && fluxData.process && !fluxData.process.killed) {
      let output = '';
      fluxData.process.stdout.on('data', (data) => {
        output += data.toString();
      });

      fluxData.process.stdin.write('get-graph-data\n');

      fluxData.process.on('close', (code) => {
        if (code === 0) {
          try {
            const graphData = JSON.parse(output);
            resolve(graphData);
          } catch (error) {
            reject('Failed to parse graph data output');
          }
        } else {
          reject('Flux process exited with code ' + code);
        }
      });
    } else {
      reject('No flux process found for tab ' + tabId);
    }
  });
});

// IPC handler to get complete graph data from a specific Flux process
ipcMain.handle('get-codebase-graph', async (event, tabId) => {
  return new Promise((resolve, reject) => {
    const fluxData = fluxProcesses.get(tabId);
    if (fluxData && fluxData.process && !fluxData.process.killed) {
      let output = '';
      fluxData.process.stdout.on('data', (data) => {
        output += data.toString();
      });

      fluxData.process.stdin.write('get-complete-graph\n');

      fluxData.process.on('close', (code) => {
        if (code === 0) {
          try {
            const graphData = JSON.parse(output);
            resolve(graphData);
          } catch (error) {
            reject('Failed to parse graph data output');
          }
        } else {
          reject('Flux process exited with code ' + code);
        }
      });
    } else {
      reject('No flux process found for tab ' + tabId);
    }
  });
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  // Kill all flux processes
  fluxProcesses.forEach((fluxData, tabId) => {
    if (fluxData && fluxData.process && !fluxData.process.killed) {
      console.log(`Cleaning up flux process for tab ${tabId}`);
      fluxData.process.kill();
    }
  });
  fluxProcesses.clear();
  
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
  // Kill all flux processes
  fluxProcesses.forEach((fluxData, tabId) => {
    if (fluxData && fluxData.process && !fluxData.process.killed) {
      console.log(`Cleaning up flux process for tab ${tabId}`);
      fluxData.process.kill();
    }
  });
  fluxProcesses.clear();
});
