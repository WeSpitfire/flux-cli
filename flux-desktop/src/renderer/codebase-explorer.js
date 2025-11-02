// Codebase Explorer - Visualizes Flux's codebase intelligence
class CodebaseExplorer {
  constructor() {
    this.graphData = null;
    this.currentFile = null;
    this.init();
  }

  async init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    // Get DOM elements
    this.elements = {
      totalFiles: document.getElementById('total-files'),
      totalEntities: document.getElementById('total-entities'),
      contextTokens: document.getElementById('context-tokens'),
      hotFilesList: document.getElementById('hot-files-list'),
      dependenciesList: document.getElementById('dependencies-list'),
      entitiesList: document.getElementById('entities-list'),
      refreshBtn: document.getElementById('refresh-graph')
    };

    // Setup event listeners
    if (this.elements.refreshBtn) {
      this.elements.refreshBtn.addEventListener('click', () => this.refresh());
    }

    // Setup tab switching to load data when explorer tab is activated
    const explorerTab = document.querySelector('[data-tab="codebase"]');
    if (explorerTab) {
      explorerTab.addEventListener('click', () => this.loadGraphData());
    }

    // Load initial data
    this.loadGraphData();
  }

  async loadGraphData() {
    try {
      this.showLoading();
      
      // Mock data for now - in production this would come from Flux CLI via IPC
      // TODO: Replace with actual IPC call to Flux CLI
      const graphData = await this.fetchGraphData();
      
      if (graphData) {
        this.graphData = graphData;
        this.renderStats();
        this.renderHotFiles();
        this.renderDependencies();
        this.renderEntities();
      }
    } catch (error) {
      console.error('Error loading codebase graph:', error);
      this.showError('Failed to load codebase data');
    }
  }

  async fetchGraphData() {
    // For now, return mock data that matches Flux CLI structure
    // TODO: Replace with actual IPC handler: window.codebase.getGraph()
    
    return {
      stats: {
        totalFiles: 100,
        totalEntities: 593,
        contextTokens: 3247
      },
      hotFiles: [
        { path: 'src/renderer/renderer.js', changes: 47, lastModified: '2 hours ago' },
        { path: 'src/renderer/styles.css', changes: 32, lastModified: '1 hour ago' },
        { path: 'src/main/main.js', changes: 28, lastModified: '3 hours ago' },
        { path: 'flux/core/codebase_intelligence.py', changes: 19, lastModified: '1 day ago' },
        { path: 'src/renderer/index.html', changes: 15, lastModified: '2 hours ago' }
      ],
      dependencies: [
        { name: 'electron', type: 'npm', usedBy: 15 },
        { name: 'xterm', type: 'npm', usedBy: 8 },
        { name: 'anthropic', type: 'pip', usedBy: 12 },
        { name: 'openai', type: 'pip', usedBy: 10 },
        { name: 'networkx', type: 'pip', usedBy: 5 }
      ],
      entities: [
        { name: 'CodebaseGraph', type: 'class', file: 'flux/core/codebase_intelligence.py', line: 46 },
        { name: 'ContextManager', type: 'class', file: 'flux/core/context_manager.py', line: 20 },
        { name: 'sendCommand', type: 'function', file: 'src/renderer/renderer.js', line: 189 },
        { name: 'createWindow', type: 'function', file: 'src/main/main.js', line: 8 },
        { name: 'FileManager', type: 'class', file: 'src/renderer/file-explorer.js', line: 3 }
      ]
    };
  }

  renderStats() {
    if (!this.graphData || !this.graphData.stats) return;

    const { totalFiles, totalEntities, contextTokens } = this.graphData.stats;

    this.updateElement(this.elements.totalFiles, totalFiles);
    this.updateElement(this.elements.totalEntities, totalEntities);
    this.updateElement(this.elements.contextTokens, this.formatNumber(contextTokens));
  }

  renderHotFiles() {
    if (!this.graphData || !this.graphData.hotFiles) {
      this.showEmptyState(this.elements.hotFilesList, '📁', 'No hot files detected');
      return;
    }

    const html = this.graphData.hotFiles.map(file => `
      <div class="file-item" data-path="${file.path}">
        <div class="file-item-info">
          <div class="file-item-name">${this.getFileName(file.path)}</div>
          <div class="file-item-meta">${file.lastModified}</div>
        </div>
        <div class="file-item-badge">
          ${file.changes} changes
        </div>
      </div>
    `).join('');

    this.elements.hotFilesList.innerHTML = html;

    // Add click handlers
    this.elements.hotFilesList.querySelectorAll('.file-item').forEach(item => {
      item.addEventListener('click', () => {
        const path = item.dataset.path;
        this.onFileClick(path);
      });
    });
  }

  renderDependencies() {
    if (!this.graphData || !this.graphData.dependencies) {
      this.showEmptyState(this.elements.dependenciesList, '📦', 'No dependencies found');
      return;
    }

    const html = this.graphData.dependencies.map(dep => `
      <div class="dependency-item">
        <div class="dependency-icon">${this.getDependencyIcon(dep.type)}</div>
        <div class="dependency-name">${dep.name}</div>
        <div class="dependency-count">${dep.usedBy} files</div>
      </div>
    `).join('');

    this.elements.dependenciesList.innerHTML = html;
  }

  renderEntities() {
    if (!this.graphData || !this.graphData.entities) {
      this.showEmptyState(this.elements.entitiesList, '⚡', 'No entities found');
      return;
    }

    const html = this.graphData.entities.map(entity => `
      <div class="entity-item" data-file="${entity.file}" data-line="${entity.line}">
        <div class="entity-icon">${this.getEntityIcon(entity.type)}</div>
        <div class="entity-info">
          <div class="entity-name">${entity.name}</div>
          <span class="entity-type">${entity.type}</span>
          <div class="entity-location">${this.getFileName(entity.file)}:${entity.line}</div>
        </div>
      </div>
    `).join('');

    this.elements.entitiesList.innerHTML = html;

    // Add click handlers
    this.elements.entitiesList.querySelectorAll('.entity-item').forEach(item => {
      item.addEventListener('click', () => {
        const file = item.dataset.file;
        const line = item.dataset.line;
        this.onEntityClick(file, line);
      });
    });
  }

  // Helper methods

  updateElement(element, value) {
    if (element) {
      element.textContent = value;
    }
  }

  formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  }

  getFileName(path) {
    return path.split('/').pop();
  }

  getDependencyIcon(type) {
    const icons = {
      'npm': '📦',
      'pip': '🐍',
      'gem': '💎',
      'cargo': '📦'
    };
    return icons[type] || '📦';
  }

  getEntityIcon(type) {
    const icons = {
      'class': '🏛️',
      'function': '⚡',
      'variable': '📌',
      'import': '📥'
    };
    return icons[type] || '📄';
  }

  showLoading() {
    const loadingHtml = '<div class="loading-text">Loading...</div>';
    if (this.elements.hotFilesList) this.elements.hotFilesList.innerHTML = loadingHtml;
    if (this.elements.dependenciesList) this.elements.dependenciesList.innerHTML = loadingHtml;
    if (this.elements.entitiesList) this.elements.entitiesList.innerHTML = loadingHtml;
  }

  showEmptyState(element, icon, text) {
    if (!element) return;
    element.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">${icon}</div>
        <div class="empty-state-text">${text}</div>
      </div>
    `;
  }

  showError(message) {
    console.error(message);
    if (this.elements.hotFilesList) {
      this.showEmptyState(this.elements.hotFilesList, '❌', message);
    }
  }

  // Event handlers

  onFileClick(path) {
    console.log('File clicked:', path);
    // TODO: Implement file opening
    // Could send to terminal: `cat ${path}` or open in editor
  }

  onEntityClick(file, line) {
    console.log('Entity clicked:', file, line);
    // TODO: Implement jump to definition
    // Could open file at specific line
  }

  async refresh() {
    console.log('Refreshing codebase graph...');
    await this.loadGraphData();
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.codebaseExplorer = new CodebaseExplorer();
  });
} else {
  window.codebaseExplorer = new CodebaseExplorer();
}
