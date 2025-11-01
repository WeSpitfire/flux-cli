// Use exposed fileSystem API from preload

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

function createFileNode(fileName, fullPath, isDirectory) {
  const wrapper = document.createElement('div');
  wrapper.classList.add('file-wrapper');

  const nodeEl = document.createElement('div');
  nodeEl.classList.add('file-node');
  nodeEl.dataset.path = fullPath;

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

  wrapper.appendChild(nodeEl);

  if (isDirectory) {
    const childrenContainer = document.createElement('div');
    childrenContainer.classList.add('children-container');
    childrenContainer.style.display = 'none';
    wrapper.appendChild(childrenContainer);

    nodeEl.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleFolder(nodeEl, fullPath, childrenContainer);
    });
  } else {
    nodeEl.addEventListener('click', (e) => {
      e.stopPropagation();
      console.log('Open file:', fullPath);
      // TODO: Implement file opening
    });
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

async function loadDirectory(dirPath, container) {
  try {
    const files = await window.fileSystem.readDir(dirPath);
    
    // Filter out hidden files and node_modules
    const filteredFiles = files.filter(file => 
      !file.startsWith('.') && file !== 'node_modules'
    );

    // Sort: directories first, then files
    const sortedFiles = await Promise.all(
      filteredFiles.map(async (file) => {
        const fullPath = await window.fileSystem.joinPath(dirPath, file);
        const isDirectory = await window.fileSystem.isDirectory(fullPath);
        return { file, fullPath, isDirectory };
      })
    );

    sortedFiles.sort((a, b) => {
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.file.localeCompare(b.file);
    });

    sortedFiles.forEach(({ file, fullPath, isDirectory }) => {
      const nodeEl = createFileNode(file, fullPath, isDirectory);
      container.appendChild(nodeEl);
    });
  } catch (err) {
    console.error('Error reading directory:', err);
  }
}

async function initFileExplorer() {
  const fileTreeContainer = document.getElementById('file-tree-container');
  const dirPathEl = document.getElementById('directory-path');
  
  try {
    const rootPath = await window.fileSystem.getCwd();
    dirPathEl.textContent = rootPath;
    await loadDirectory(rootPath, fileTreeContainer);
  } catch (err) {
    console.error('Error initializing file explorer:', err);
    dirPathEl.textContent = 'Error loading directory';
  }
}

// Export loadDirectory for use by directory changer
window.loadDirectory = loadDirectory;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initFileExplorer);
} else {
  initFileExplorer();
}
