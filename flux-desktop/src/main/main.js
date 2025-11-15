const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const SettingsManager = require('./settingsManager');

// Map of tabId -> flux process data
const fluxProcesses = new Map();

// Map of tabId -> retry state for auto-restart
const retryState = new Map();

// Settings manager instance
let settingsManager;

// Auto-restart configuration
const MAX_RETRIES = 5;
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30000;

function createWindow () {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    backgroundColor: '#1a1b26',
    titleBarStyle: 'hiddenInset', // Modern macOS style
    vibrancy: 'under-window',      // Translucent window
    visualEffectState: 'active',
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  win.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

  // Helper to get or initialize retry state for a tab
  function getRetryState(tabId) {
    if (!retryState.has(tabId)) {
      retryState.set(tabId, {
        attempts: 0,
        lastAttempt: 0,
        backoffMs: INITIAL_BACKOFF_MS,
        manualStop: false
      });
    }
    return retryState.get(tabId);
  }

  // Reset retry state on successful start
  function resetRetryState(tabId) {
    const state = getRetryState(tabId);
    state.attempts = 0;
    state.backoffMs = INITIAL_BACKOFF_MS;
  }

  // Schedule a restart with exponential backoff
  function scheduleRestart(tabId, cwd, errorMsg) {
    const state = getRetryState(tabId);
    
    // Don't auto-restart if manually stopped or max retries exceeded
    if (state.manualStop || state.attempts >= MAX_RETRIES) {
      if (state.attempts >= MAX_RETRIES) {
        const finalMsg = `\n\n❌ Auto-restart failed after ${MAX_RETRIES} attempts.\nPlease check the Flux CLI installation or restart the tab manually.`;
        if (!win.isDestroyed()) {
          win.webContents.send('flux-error', { tabId, data: errorMsg + finalMsg });
        }
      }
      return;
    }
    
    state.attempts++;
    state.lastAttempt = Date.now();
    
    const waitTime = Math.min(state.backoffMs, MAX_BACKOFF_MS);
    console.log(`[Tab ${tabId}] Scheduling restart attempt ${state.attempts}/${MAX_RETRIES} in ${waitTime}ms`);
    
    // Notify user of auto-restart
    if (!win.isDestroyed()) {
      const restartMsg = `\n⚠️  Process crashed. Auto-restarting in ${waitTime/1000}s (attempt ${state.attempts}/${MAX_RETRIES})...`;
      win.webContents.send('flux-error', { tabId, data: errorMsg + restartMsg });
    }
    
    setTimeout(async () => {
      console.log(`[Tab ${tabId}] Attempting restart ${state.attempts}/${MAX_RETRIES}`);
      await spawnFluxForTab(tabId, cwd);
    }, waitTime);
    
    // Exponential backoff
    state.backoffMs = Math.min(state.backoffMs * 2, MAX_BACKOFF_MS);
  }

  // Helper to spawn a new Flux process for a tab
  async function spawnFluxForTab(tabId, cwd) {
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
    
    // Get API keys from settings if available
    const env = { 
      ...process.env,
      PYTHONUNBUFFERED: '1',
      FORCE_COLOR: '1',
      TERM: 'xterm-256color',
      FLUX_DESKTOP_MODE: '1'  // Enable tree events for Living Tree visualization
    };
    
    // Inject API keys and settings from settings manager
    if (settingsManager) {
      try {
        // Get best working provider (validates keys)
        const bestProvider = await settingsManager.getBestWorkingProvider();
        
        if (bestProvider.validated && bestProvider.key) {
          const settings = settingsManager.getSettings();
          
          // Use the validated provider
          env.FLUX_PROVIDER = bestProvider.provider;
          env.FLUX_MODEL = bestProvider.model;
          env.FLUX_MAX_TOKENS = String(settings.maxTokens);
          env.FLUX_TEMPERATURE = String(settings.temperature);
          env.FLUX_REQUIRE_APPROVAL = settings.requireApproval ? 'true' : 'false';
          
          // Set the working API key
          if (bestProvider.provider === 'anthropic') {
            env.ANTHROPIC_API_KEY = bestProvider.key;
          } else if (bestProvider.provider === 'openai') {
            env.OPENAI_API_KEY = bestProvider.key;
          }
          
          const fallbackMsg = bestProvider.fallback ? ' (fallback)' : '';
          const cachedMsg = bestProvider.cached ? ' (cached)' : '';
          console.log(`[Tab ${tabId}] Using provider: ${bestProvider.provider}${fallbackMsg}${cachedMsg}, model: ${bestProvider.model}`);
        } else {
          console.error(`[Tab ${tabId}] No valid API keys found:`, bestProvider.error);
          // Still set basic env vars from settings
          const settings = settingsManager.getSettings();
          env.FLUX_PROVIDER = settings.provider;
          env.FLUX_MODEL = settings.model;
        }
      } catch (error) {
        console.error(`[Tab ${tabId}] Failed to get best provider:`, error);
      }
    }
    
    const fluxProcess = spawn(fluxCommand, [], {
      cwd: workingDir,
      env: env,
      shell: false
    });

    fluxProcess.stdout.on('data', (data) => {
      const output = data.toString();
      try {
        console.log(`[Flux ${tabId} stdout]:`, output);
      } catch (err) {
        // Ignore EPIPE errors from logging
      }
      
      // Parse and forward tree events for Living Tree visualization
      const treeEventRegex = /__FLUX_TREE_EVENT__(.+?)__END__/g;
      let match;
      let cleanedOutput = output;
      
      while ((match = treeEventRegex.exec(output)) !== null) {
        try {
          const eventData = JSON.parse(match[1]);
          if (!win.isDestroyed()) {
            // Forward tree event to renderer
            win.webContents.send('flux-tree-event', { 
              tabId, 
              event: eventData.event,
              data: eventData.data 
            });
          }
          // Remove event from output so it doesn't appear in terminal
          cleanedOutput = cleanedOutput.replace(match[0], '');
        } catch (err) {
          console.error(`[Tab ${tabId}] Failed to parse tree event:`, err);
        }
      }
      
      // Send cleaned output (without tree events) to terminal
      if (!win.isDestroyed() && cleanedOutput.trim()) {
        win.webContents.send('flux-output', { tabId, data: cleanedOutput });
      }
    });

    fluxProcess.stderr.on('data', (data) => {
      const error = data.toString();
      try {
        console.error(`[Flux ${tabId} stderr]:`, error);
      } catch (err) {
        // Ignore EPIPE errors from logging
      }
      if (!win.isDestroyed()) {
        win.webContents.send('flux-error', { tabId, data: error });
      }
    });

    fluxProcess.on('error', (error) => {
      const errorMsg = `Process error: ${error.message}\n\nTroubleshooting:\n- Ensure Flux CLI is installed: pip install -e .\n- Check that 'flux' command is in PATH\n- Try running 'flux' in terminal to verify`;
      console.error(`[Flux ${tabId} process error]:`, error);
      
      // Schedule auto-restart
      scheduleRestart(tabId, workingDir, errorMsg);
    });

    fluxProcess.on('close', (code) => {
      console.log(`[Flux ${tabId}] Process closed with code ${code}`);
      const state = getRetryState(tabId);
      
      fluxProcesses.delete(tabId);
      
      // If process crashed (non-zero exit code) and wasn't manually stopped
      if (code !== 0 && !state.manualStop) {
        const errorMsg = `Flux process exited with code ${code}`;
        console.error(`[Flux ${tabId}] Unexpected exit:`, errorMsg);
        
        // Schedule auto-restart
        scheduleRestart(tabId, workingDir, errorMsg);
      } else if (code === 0) {
        // Reset retry state on clean exit
        resetRetryState(tabId);
      }
    });

    fluxProcesses.set(tabId, { process: fluxProcess, cwd: workingDir });
    
    // Process started successfully, reset retry state
    resetRetryState(tabId);
    
    return fluxProcess;
  }

  // IPC handlers for tab-specific flux processes
  ipcMain.on('flux-create-process', async (event, { tabId, cwd }) => {
    console.log('Creating flux process for tab:', tabId);
    await spawnFluxForTab(tabId, cwd);
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
      setTimeout(async () => {
        console.log(`Respawning flux process for tab ${tabId} in ${savedCwd}`);
        await spawnFluxForTab(tabId, savedCwd);
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
      
      // Mark as manual stop to prevent auto-restart
      const state = getRetryState(tabId);
      state.manualStop = true;
      
      fluxData.process.kill();
      fluxProcesses.delete(tabId);
      retryState.delete(tabId);
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
    // Find flux command
    const projectRoot = path.resolve(path.join(__dirname, '../../..'));
    const venvFluxPath = path.resolve(path.join(projectRoot, 'venv', 'bin', 'flux'));
    const fluxExists = fs.existsSync(venvFluxPath);
    const fluxCommand = fluxExists ? venvFluxPath : 'flux';
    
    console.log('[Codebase Stats] Using flux command:', fluxCommand);
    
    const fluxProcess = spawn(fluxCommand, ['graph', '--format=json'], {
      cwd: process.cwd(),
      shell: false
    });

    let output = '';
    let errorOutput = '';
    
    fluxProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    fluxProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
      console.error('[Codebase Stats] Flux stderr:', data.toString());
    });

    fluxProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const graphData = JSON.parse(output);
          
          // Transform to expected format
          const result = {
            stats: graphData.stats || {
              totalFiles: 0,
              totalEntities: 0,
              contextTokens: 0
            },
            hotFiles: [],
            dependencies: [],
            entities: []
          };
          
          // Convert files to hotFiles format (most recently modified)
          if (graphData.files) {
            const filesList = Object.entries(graphData.files).map(([path, data]) => ({
              path,
              changes: 0,  // We don't track changes yet
              lastModified: 'Unknown'
            }));
            result.hotFiles = filesList.slice(0, 10);
          }
          
          // Convert entities
          if (graphData.entities) {
            result.entities = Object.values(graphData.entities).slice(0, 20);
          }
          
          resolve(result);
        } catch (error) {
          console.error('[Codebase Stats] Failed to parse JSON:', error);
          console.error('[Codebase Stats] Output was:', output);
          reject('Failed to parse graph data: ' + error.message);
        }
      } else {
        console.error('[Codebase Stats] Flux exited with code:', code);
        console.error('[Codebase Stats] Error output:', errorOutput);
        
        // Fallback to mock data on error
        resolve({
          stats: {
            totalFiles: 0,
            totalEntities: 0,
            contextTokens: 0
          },
          hotFiles: [],
          dependencies: [],
          entities: [],
          error: `Flux CLI error (code ${code}): ${errorOutput}`
        });
      }
    });
    
    fluxProcess.on('error', (error) => {
      console.error('[Codebase Stats] Failed to spawn flux:', error);
      // Fallback to empty data
      resolve({
        stats: {
          totalFiles: 0,
          totalEntities: 0,
          contextTokens: 0
        },
        hotFiles: [],
        dependencies: [],
        entities: [],
        error: `Failed to run flux: ${error.message}`
      });
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

// ========================================
// FILE ACTIONS IPC HANDLERS
// ========================================

// Open file in default editor
ipcMain.handle('open-in-editor', async (event, filePath) => {
  const { shell } = require('electron');
  try {
    await shell.openPath(filePath);
    return { success: true };
  } catch (error) {
    console.error('[File Actions] Failed to open file:', error);
    return { success: false, error: error.message };
  }
});

// Show file in Finder (macOS) / Explorer (Windows) / File Manager (Linux)
ipcMain.handle('show-in-finder', async (event, filePath) => {
  const { shell } = require('electron');
  try {
    shell.showItemInFolder(filePath);
    return { success: true };
  } catch (error) {
    console.error('[File Actions] Failed to show in Finder:', error);
    return { success: false, error: error.message };
  }
});

// ========================================
// SETTINGS IPC HANDLERS
// ========================================

// Get all settings
ipcMain.handle('settings:get', async () => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.getSettings();
});

// Get API key (masked)
ipcMain.handle('settings:getApiKey', async (event, provider) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.getApiKey(provider, true);
});

// Set API key
ipcMain.handle('settings:setApiKey', async (event, { provider, key }) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  try {
    return settingsManager.setApiKey(provider, key);
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// Set provider
ipcMain.handle('settings:setProvider', async (event, provider) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  try {
    return settingsManager.setProvider(provider);
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// Set model
ipcMain.handle('settings:setModel', async (event, model) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.setModel(model);
});

// Update LLM settings
ipcMain.handle('settings:setLLMSettings', async (event, settings) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.setLLMSettings(settings);
});

// Update appearance
ipcMain.handle('settings:setAppearance', async (event, appearance) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.setAppearance(appearance);
});

// Update experimental features
ipcMain.handle('settings:setExperimental', async (event, features) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.setExperimental(features);
});

// Test API connection
ipcMain.handle('settings:testConnection', async (event, provider) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return await settingsManager.testConnection(provider);
});

// Get available models
ipcMain.handle('settings:getAvailableModels', async (event, provider) => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.getAvailableModels(provider);
});

// Reset to defaults
ipcMain.handle('settings:reset', async () => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.resetToDefaults();
});

// Get settings file path
ipcMain.handle('settings:getPath', async () => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return settingsManager.getSettingsPath();
});

// Get best working provider
ipcMain.handle('settings:getBestWorkingProvider', async () => {
  if (!settingsManager) {
    settingsManager = new SettingsManager();
  }
  return await settingsManager.getBestWorkingProvider();
});

// Apply theme to all windows
ipcMain.handle('settings:applyTheme', async (event, theme) => {
  // Broadcast theme change to all windows
  BrowserWindow.getAllWindows().forEach(window => {
    if (!window.isDestroyed()) {
      window.webContents.send('theme-changed', theme);
    }
  });
  return { success: true };
});

// IPC handler to open settings window
ipcMain.on('open-settings', () => {
  const settingsWindow = new BrowserWindow({
    width: 900,
    height: 700,
    backgroundColor: '#1a1b26',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    },
    title: 'Flux Settings',
    minimizable: false,
    maximizable: false,
    fullscreenable: false
  });
  
  settingsWindow.loadFile(path.join(__dirname, '..', 'renderer', 'settings.html'));
  
  // Optional: Open dev tools for debugging
  if (process.argv.includes('--dev')) {
    settingsWindow.webContents.openDevTools();
  }
});

app.whenReady().then(() => {
  // Initialize settings manager
  settingsManager = new SettingsManager();
  createWindow();
});

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
