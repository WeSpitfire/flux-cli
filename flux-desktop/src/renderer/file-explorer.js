// Use exposed fileSystem API from preload

// Track current working directory
let currentWorkingDirectory = null;
let activeTabId = null;

function getFileIcon(fileName, isDirectory) {
  if (isDirectory) return '📁';
  const extension = fileName.split('.').pop().toLowerCase();
  switch (extension) {
    case 'js':
    case 'ts':
      return '📜';
    case 'css':
      return '🎨';
    case 'html':
      return '🌐';
    case 'py':
      return '🐍';
    case 'json':
      return '📦';
    case 'md':
    case 'txt':
      return '📝';
    default:
      return '📄';
  }
}

function isProjectDirectory(fileName) {
  // Common project markers
  const projectMarkers = [
    'package.json', 'requirements.txt', 'go.mod', 'Cargo.toml',
    'pom.xml', 'build.gradle', 'composer.json', '.git'
  ];
  return projectMarkers.includes(fileName);
}

function createFileNode(fileName, fullPath, isDirectory, hasProjectMarker = false) {
  const wrapper = document.createElement('div');
  wrapper.classList.add('file-wrapper');

  const nodeEl = document.createElement('div');
  nodeEl.classList.add('file-node');
  nodeEl.dataset.path = fullPath;
  
  // Highlight active working directory
  if (isDirectory && fullPath === currentWorkingDirectory) {
    nodeEl.classList.add('active-directory');
  }
  
  // Add project indicator for directories with project markers
  if (isDirectory && hasProjectMarker) {
    nodeEl.classList.add('project-directory');
  }

  if (isDirectory) {
    const expandIndicator = document.createElement('span');
    expandIndicator.classList.add('expand-indicator');
    expandIndicator.textContent = '▶';
    nodeEl.appendChild(expandIndicator);
  }

  const iconEl = document.createElement('span');
  iconEl.classList.add('file-icon');
  iconEl.textContent = getFileIcon(fileName, isDirectory);
  nodeEl.appendChild(iconEl);

  const nameEl = document.createElement('span');
  nameEl.classList.add('file-name');
  nameEl.textContent = fileName;
  nodeEl.appendChild(nameEl);
  
  // Add "Work Here" button for directories
  if (isDirectory && fullPath !== currentWorkingDirectory) {
    const workHereBtn = document.createElement('button');
    workHereBtn.classList.add('work-here-btn');
    workHereBtn.textContent = '⚡';
    workHereBtn.title = 'Work in this directory';
    workHereBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await changeWorkingDirectory(fullPath);
    });
    nodeEl.appendChild(workHereBtn);
  }

  wrapper.appendChild(nodeEl);

  if (isDirectory) {
    const childrenContainer = document.createElement('div');
    childrenContainer.classList.add('children-container');
    childrenContainer.style.display = 'none';
    wrapper.appendChild(childrenContainer);

    // Click to expand/collapse
    const expandArea = nodeEl.querySelector('.expand-indicator');
    if (expandArea) {
      expandArea.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFolder(nodeEl, fullPath, childrenContainer);
      });
    }
    
    // Double-click directory name to work in it
    nameEl.addEventListener('dblclick', async (e) => {
      e.stopPropagation();
      await changeWorkingDirectory(fullPath);
    });
  } else {
    // Hide files by default - only show in active working directory's immediate children
    // This makes the explorer directory-focused
    wrapper.style.display = 'none';
  }

  return wrapper;
}

async function toggleFolder(nodeEl, dirPath, childrenContainer) {
  const expandIndicator = nodeEl.querySelector('.expand-indicator');
  const isExpanded = childrenContainer.style.display !== 'none';

  if (isExpanded) {
    childrenContainer.style.display = 'none';
    expandIndicator.textContent = '▶';
    nodeEl.classList.remove('expanded');
  } else {
    if (childrenContainer.children.length === 0) {
      // Load directory contents
      await loadDirectory(dirPath, childrenContainer);
    }
    childrenContainer.style.display = 'block';
    expandIndicator.textContent = '▼';
    nodeEl.classList.add('expanded');
  }
}

async function changeWorkingDirectory(newPath) {
  if (!window.tabManager || !window.tabManager.activeTabId) {
    console.error('No active tab');
    return;
  }
  
  const tabId = window.tabManager.activeTabId;
  activeTabId = tabId;
  
  try {
    console.log('Changing working directory to:', newPath);
    
    // Show loading state
    const dirPathEl = document.getElementById('directory-path');
    dirPathEl.innerHTML = `<span class="loading">⏳ Switching to ${newPath.split('/').pop()}...</span>`;
    
    // Call IPC to change directory
    const result = await window.flux.changeWorkingDirectory(tabId, newPath);
    
    if (result.success) {
      currentWorkingDirectory = newPath;
      dirPathEl.textContent = newPath;
      
      // Reload file tree to show new directory
      const fileTreeContainer = document.getElementById('file-tree-container');
      fileTreeContainer.innerHTML = '';
      await loadDirectory(newPath, fileTreeContainer);
      
      // Auto-trigger /index for new directory
      console.log('Auto-indexing new directory...');
      setTimeout(() => {
        if (window.flux && window.flux.sendCommand) {
          window.flux.sendCommand(tabId, '/index');
        }
      }, 500);
    } else {
      console.error('Failed to change directory:', result.error);
      dirPathEl.innerHTML = `<span class="error">⚠️ Failed: ${result.error}</span>`;
    }
  } catch (err) {
    console.error('Error changing directory:', err);
  }
}

async function loadDirectory(dirPath, container) {
  try {
    const files = await window.fileSystem.readDir(dirPath);
    
    // Filter out hidden files and node_modules
    const filteredFiles = files.filter(file => 
      !file.startsWith('.') && file !== 'node_modules'
    );
    
    // Check for project markers in this directory
    const hasProjectMarker = filteredFiles.some(file => isProjectDirectory(file));

    // Sort: directories first, then files
    const sortedFiles = await Promise.all(
      filteredFiles.map(async (file) => {
        const fullPath = await window.fileSystem.joinPath(dirPath, file);
        const isDirectory = await window.fileSystem.isDirectory(fullPath);
        
        // Check if this subdirectory has project markers
        let subHasProjectMarker = false;
        if (isDirectory) {
          try {
            const subFiles = await window.fileSystem.readDir(fullPath);
            subHasProjectMarker = subFiles.some(f => isProjectDirectory(f));
          } catch (e) {
            // Ignore errors reading subdirectories
          }
        }
        
        return { file, fullPath, isDirectory, hasProjectMarker: subHasProjectMarker };
      })
    );

    sortedFiles.sort((a, b) => {
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.file.localeCompare(b.file);
    });

    sortedFiles.forEach(({ file, fullPath, isDirectory, hasProjectMarker }) => {
      const nodeEl = createFileNode(file, fullPath, isDirectory, hasProjectMarker);
      container.appendChild(nodeEl);
    });
  } catch (err) {
    console.error('Error reading directory:', err);
  }
}

async function initFileExplorer() {
  console.log('[File Explorer] Initializing...');
  const fileTreeContainer = document.getElementById('file-tree-container');
  const dirPathEl = document.getElementById('directory-path');
  
  console.log('[File Explorer] Found elements:', { 
    fileTreeContainer: !!fileTreeContainer, 
    dirPathEl: !!dirPathEl 
  });
  
  if (!fileTreeContainer || !dirPathEl) {
    console.error('[File Explorer] Required DOM elements not found!');
    // Retry after a delay in case Vue is still rendering
    setTimeout(() => {
      console.log('[File Explorer] Retrying initialization...');
      initFileExplorer();
    }, 500);
    return;
  }
  
  if (!window.fileSystem || !window.fileSystem.getCwd) {
    console.error('[File Explorer] fileSystem API not available!');
    dirPathEl.textContent = 'File system API not available';
    return;
  }
  
  try {
    const rootPath = await window.fileSystem.getCwd();
    console.log('[File Explorer] Got working directory:', rootPath);
    currentWorkingDirectory = rootPath;
    dirPathEl.textContent = rootPath;
    await loadDirectory(rootPath, fileTreeContainer);
    console.log('[File Explorer] File tree loaded successfully');
    
    // Listen for working directory changes from other sources
    if (window.flux && window.flux.onWorkingDirectoryChanged) {
      window.flux.onWorkingDirectoryChanged((tabId, newPath) => {
        console.log('Working directory changed externally:', newPath);
        currentWorkingDirectory = newPath;
        dirPathEl.textContent = newPath;
        
        // Reload file tree
        fileTreeContainer.innerHTML = '';
        loadDirectory(newPath, fileTreeContainer);
      });
    }
  } catch (err) {
    console.error('Error initializing file explorer:', err);
    dirPathEl.textContent = 'Error loading directory';
  }
}

// Export loadDirectory for use by directory changer
window.loadDirectory = loadDirectory;

// Initialize when Vue has mounted the DOM
let initStarted = false;

function startInit() {
  if (initStarted) return;
  initStarted = true;
  console.log('[File Explorer] Starting initialization...');
  initFileExplorer();
}

window.addEventListener('vue-mounted', () => {
  console.log('[File Explorer] Vue mounted event received');
  startInit();
});

// Fallback: if vue-mounted already fired, init after a delay
setTimeout(() => {
  if (!initStarted && document.getElementById('file-tree-container')) {
    console.log('[File Explorer] Fallback initialization (vue-mounted may have already fired)');
    startInit();
  }
}, 1000);
