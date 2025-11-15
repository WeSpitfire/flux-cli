// Living Tree - Real-time visualization of Flux's codebase navigation
class LivingTree {
  constructor() {
    this.nodes = new Map(); // path -> node data
    this.edges = new Map(); // edgeId -> edge data
    this.activeFiles = new Set(); // Currently being worked on
    this.svg = null;
    this.simulation = null;
    this.container = null;
    this.init();
  }

  async init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    this.container = document.getElementById('codebase-panel');
    if (!this.container) return;

    // Replace the existing static content with our living tree
    this.container.innerHTML = `
      <div class="sidebar-header">
        <h3>Living Tree</h3>
        <button class="icon-btn" id="center-tree" title="Center View">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="8" cy="8" r="2" fill="currentColor"/>
          </svg>
        </button>
      </div>
      
      <!-- Live Stats -->
      <div class="tree-stats">
        <div class="stat-indicator">
          <div class="stat-dot reading"></div>
          <span id="reading-count">0</span> Reading
        </div>
        <div class="stat-indicator">
          <div class="stat-dot editing"></div>
          <span id="editing-count">0</span> Editing
        </div>
        <div class="stat-indicator">
          <div class="stat-dot connected"></div>
          <span id="connected-count">0</span> Connected
        </div>
      </div>

      <!-- Tree Visualization Canvas -->
      <div class="tree-canvas" id="tree-canvas">
        <svg id="tree-svg" width="100%" height="100%">
          <defs>
            <!-- Gradient for edges -->
            <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" style="stop-color:#58a6ff;stop-opacity:0.3" />
              <stop offset="100%" style="stop-color:#58a6ff;stop-opacity:0.8" />
            </linearGradient>
            
            <!-- Glow filter for active nodes -->
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          <g id="edges-group"></g>
          <g id="nodes-group"></g>
        </svg>
      </div>

      <!-- File Details Panel (shows on hover/click) -->
      <div class="file-details" id="file-details" style="display: none;">
        <div class="file-details-header">
          <div class="file-details-icon"></div>
          <div class="file-details-name"></div>
          <button class="file-details-close">&times;</button>
        </div>
        <div class="file-details-body">
          <div class="detail-row">
            <span class="detail-label">Status:</span>
            <span class="detail-value status-value"></span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Type:</span>
            <span class="detail-value type-value"></span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Connections:</span>
            <span class="detail-value connections-value"></span>
          </div>
          <div class="detail-row related-files">
            <span class="detail-label">Related:</span>
            <div class="related-list"></div>
          </div>
        </div>
      </div>

      <!-- Activity Feed -->
      <div class="activity-feed" id="activity-feed">
        <div class="activity-header">Recent Activity</div>
        <div class="activity-list" id="activity-list">
          <!-- Activity items populate here -->
        </div>
      </div>
    `;

    // Setup SVG
    this.svg = document.getElementById('tree-svg');
    this.nodesGroup = document.getElementById('nodes-group');
    this.edgesGroup = document.getElementById('edges-group');

    // Setup event listeners
    document.getElementById('center-tree')?.addEventListener('click', () => this.centerView());
    document.querySelector('.file-details-close')?.addEventListener('click', () => this.hideFileDetails());

    // Listen for Flux events from main process
    this.setupFluxEventListeners();

    // Initialize with current working directory as root
    this.initializeRoot();
  }

  async initializeRoot() {
    // Get current directory from tab manager or file system API
    const activeTab = window.tabManager?.getActiveTab();
    let cwd = activeTab?.cwd;
    
    // Fallback to file system API if tab manager not available
    if (!cwd && window.fileSystem?.getCwd) {
      try {
        cwd = await window.fileSystem.getCwd();
      } catch (err) {
        console.warn('[LivingTree] Could not get cwd:', err);
        cwd = '/';
      }
    }
    
    if (cwd) {
      this.addNode(cwd, 'directory', 'root');
    }
  }

  setupFluxEventListeners() {
    // Listen for file operations from Flux via IPC
    if (window.flux && window.flux.onTreeEvent) {
      window.flux.onTreeEvent((tabId, event, data) => {
        console.log('[LivingTree] Received event:', event, data);
        
        // Route events to appropriate handlers
        switch (event) {
          case 'file-read':
            this.onFileRead(data.path, data.parent);
            break;
          case 'file-edit':
            this.onFileEdit(data.path);
            break;
          case 'file-create':
            this.onFileCreate(data.path, data.parent);
            break;
          case 'file-delete':
            this.onFileDelete(data.path);
            break;
          case 'dependency-found':
            this.onDependencyFound(data.from, data.to, data.type);
            break;
          case 'analysis-start':
            this.onAnalysisStart(data.path);
            break;
          case 'analysis-complete':
            this.onAnalysisComplete(data.path);
            break;
          case 'search-result':
            this.onSearchResult(data.query, data.path, data.matches);
            break;
          default:
            console.warn('[LivingTree] Unknown event type:', event);
        }
      });
    } else {
      console.warn('[LivingTree] Flux bridge not available - tree events disabled');
    }
  }

  // Event handlers for Flux operations

  onFileRead(path, parent = null) {
    this.addNode(path, this.getFileType(path), 'reading');
    if (parent) {
      this.addEdge(parent, path, 'read');
    }
    this.addActivity('read', path);
    this.updateStats();
  }

  onFileEdit(path) {
    this.updateNodeStatus(path, 'editing');
    this.addActivity('edit', path);
    this.updateStats();
  }

  onFileCreate(path, parent = null) {
    this.addNode(path, this.getFileType(path), 'creating');
    if (parent) {
      this.addEdge(parent, path, 'created');
    }
    this.addActivity('create', path);
    this.updateStats();
  }

  onDependencyFound(from, to, type) {
    this.addNode(to, this.getFileType(to), 'connected');
    this.addEdge(from, to, type || 'dependency');
    this.updateStats();
  }

  onAnalysisComplete(path) {
    this.updateNodeStatus(path, 'analyzed');
    setTimeout(() => {
      this.updateNodeStatus(path, 'idle');
      this.updateStats();
    }, 2000);
  }

  onAnalysisStart(path) {
    this.addNode(path, this.getFileType(path), 'analyzing');
    this.addActivity('analyze', path);
    this.updateStats();
  }

  onFileDelete(path) {
    // Remove node from graph
    const node = this.nodes.get(path);
    if (node) {
      const g = this.nodesGroup.querySelector(`[data-path="${path}"]`);
      if (g) {
        g.style.transition = 'opacity 0.3s ease';
        g.style.opacity = '0';
        setTimeout(() => {
          if (g.parentNode) g.parentNode.removeChild(g);
        }, 300);
      }
      this.nodes.delete(path);
    }
    this.addActivity('delete', path);
    this.updateStats();
  }

  onSearchResult(query, path, matches) {
    this.addNode(path, this.getFileType(path), 'connected');
    this.addActivity('analyze', path);
    this.updateStats();
  }

  // Node management

  addNode(path, type, status = 'idle') {
    if (this.nodes.has(path)) {
      // Update existing node
      const node = this.nodes.get(path);
      node.status = status;
      this.updateNodeVisual(path);
      return;
    }

    // Create new node
    const node = {
      path,
      type,
      status,
      x: Math.random() * 400 + 50, // Initial random position
      y: Math.random() * 400 + 50,
      connections: new Set()
    };

    this.nodes.set(path, node);
    this.createNodeVisual(path);
    this.animateNodeIn(path);
  }

  createNodeVisual(path) {
    const node = this.nodes.get(path);
    if (!node) return;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'tree-node');
    g.setAttribute('data-path', path);
    g.setAttribute('transform', `translate(${node.x}, ${node.y})`);

    // Circle
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('r', '8');
    circle.setAttribute('class', `node-circle status-${node.status}`);
    
    // Outer ring (for active states)
    const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    ring.setAttribute('r', '12');
    ring.setAttribute('class', 'node-ring');
    ring.setAttribute('fill', 'none');
    ring.setAttribute('stroke', this.getStatusColor(node.status));
    ring.setAttribute('stroke-width', '2');
    ring.setAttribute('opacity', '0');

    // Label
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('class', 'node-label');
    text.setAttribute('x', '0');
    text.setAttribute('y', '25');
    text.textContent = this.getFileName(path);

    g.appendChild(ring);
    g.appendChild(circle);
    g.appendChild(text);

    // Add event listeners
    g.addEventListener('mouseenter', () => this.onNodeHover(path));
    g.addEventListener('mouseleave', () => this.onNodeLeave(path));
    g.addEventListener('click', () => this.onNodeClick(path));
    g.addEventListener('contextmenu', (e) => this.onNodeRightClick(path, e));

    this.nodesGroup.appendChild(g);
  }

  updateNodeVisual(path) {
    const node = this.nodes.get(path);
    if (!node) return;

    const g = this.nodesGroup.querySelector(`[data-path="${path}"]`);
    if (!g) return;

    const circle = g.querySelector('.node-circle');
    const ring = g.querySelector('.node-ring');

    // Update classes
    circle.setAttribute('class', `node-circle status-${node.status}`);
    ring.setAttribute('stroke', this.getStatusColor(node.status));

    // Animate active states
    if (node.status === 'reading' || node.status === 'editing') {
      this.pulseNode(g);
    }
  }

  updateNodeStatus(path, status) {
    const node = this.nodes.get(path);
    if (node) {
      node.status = status;
      this.updateNodeVisual(path);
    }
  }

  // Edge management

  addEdge(from, to, type = 'dependency') {
    const edgeId = `${from}->${to}`;
    if (this.edges.has(edgeId)) return;

    const edge = { from, to, type };
    this.edges.set(edgeId, edge);

    // Update node connections
    this.nodes.get(from)?.connections.add(to);
    this.nodes.get(to)?.connections.add(from);

    this.createEdgeVisual(edgeId);
    this.animateEdgeIn(edgeId);
  }

  createEdgeVisual(edgeId) {
    const edge = this.edges.get(edgeId);
    if (!edge) return;

    const fromNode = this.nodes.get(edge.from);
    const toNode = this.nodes.get(edge.to);
    if (!fromNode || !toNode) return;

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('class', `tree-edge edge-${edge.type}`);
    line.setAttribute('data-edge-id', edgeId);
    line.setAttribute('x1', fromNode.x);
    line.setAttribute('y1', fromNode.y);
    line.setAttribute('x2', toNode.x);
    line.setAttribute('y2', toNode.y);
    line.setAttribute('stroke', 'url(#edge-gradient)');
    line.setAttribute('stroke-width', '2');
    line.setAttribute('opacity', '0');

    this.edgesGroup.appendChild(line);
  }

  updateEdgePositions() {
    this.edges.forEach((edge, edgeId) => {
      const line = this.edgesGroup.querySelector(`[data-edge-id="${edgeId}"]`);
      if (!line) return;

      const fromNode = this.nodes.get(edge.from);
      const toNode = this.nodes.get(edge.to);
      if (!fromNode || !toNode) return;

      line.setAttribute('x1', fromNode.x);
      line.setAttribute('y1', fromNode.y);
      line.setAttribute('x2', toNode.x);
      line.setAttribute('y2', toNode.y);
    });
  }

  // Animations

  animateNodeIn(path) {
    const g = this.nodesGroup.querySelector(`[data-path="${path}"]`);
    if (!g) return;

    // Fade in with scale
    g.style.opacity = '0';
    g.style.transform = `translate(${this.nodes.get(path).x}px, ${this.nodes.get(path).y}px) scale(0)`;
    
    requestAnimationFrame(() => {
      g.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
      g.style.opacity = '1';
      g.style.transform = `translate(${this.nodes.get(path).x}px, ${this.nodes.get(path).y}px) scale(1)`;
    });
  }

  animateEdgeIn(edgeId) {
    const line = this.edgesGroup.querySelector(`[data-edge-id="${edgeId}"]`);
    if (!line) return;

    // Fade in
    setTimeout(() => {
      line.style.transition = 'opacity 0.5s ease';
      line.setAttribute('opacity', '0.6');
    }, 100);
  }

  pulseNode(nodeElement) {
    const ring = nodeElement.querySelector('.node-ring');
    if (!ring) return;

    // Pulse animation
    ring.style.transition = 'all 0.6s ease-in-out';
    ring.setAttribute('opacity', '1');
    ring.setAttribute('r', '16');

    setTimeout(() => {
      ring.setAttribute('opacity', '0');
      ring.setAttribute('r', '12');
    }, 600);
  }

  // Activity Feed

  addActivity(action, path) {
    const activityList = document.getElementById('activity-list');
    if (!activityList) return;

    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
      <div class="activity-icon ${action}">${this.getActivityIcon(action)}</div>
      <div class="activity-content">
        <div class="activity-action">${this.getActivityLabel(action)}</div>
        <div class="activity-file">${this.getFileName(path)}</div>
      </div>
      <div class="activity-time">now</div>
    `;

    // Add to top
    activityList.insertBefore(item, activityList.firstChild);

    // Limit to 10 items
    while (activityList.children.length > 10) {
      activityList.removeChild(activityList.lastChild);
    }

    // Fade in
    item.style.opacity = '0';
    requestAnimationFrame(() => {
      item.style.transition = 'opacity 0.3s ease';
      item.style.opacity = '1';
    });
  }

  // Stats

  updateStats() {
    const reading = Array.from(this.nodes.values()).filter(n => n.status === 'reading').length;
    const editing = Array.from(this.nodes.values()).filter(n => n.status === 'editing').length;
    const connected = this.edges.size;

    document.getElementById('reading-count').textContent = reading;
    document.getElementById('editing-count').textContent = editing;
    document.getElementById('connected-count').textContent = connected;
  }

  // File Details Panel

  showFileDetails(path) {
    const node = this.nodes.get(path);
    if (!node) return;

    const panel = document.getElementById('file-details');
    panel.style.display = 'block';

    panel.querySelector('.file-details-name').textContent = this.getFileName(path);
    panel.querySelector('.file-details-icon').textContent = this.getFileIcon(node.type);
    panel.querySelector('.status-value').textContent = node.status;
    panel.querySelector('.type-value').textContent = node.type;
    panel.querySelector('.connections-value').textContent = node.connections.size;

    // Show related files
    const relatedList = panel.querySelector('.related-list');
    relatedList.innerHTML = '';
    node.connections.forEach(connPath => {
      const item = document.createElement('div');
      item.className = 'related-item';
      item.textContent = this.getFileName(connPath);
      item.addEventListener('click', () => this.onNodeClick(connPath));
      relatedList.appendChild(item);
    });
  }

  hideFileDetails() {
    document.getElementById('file-details').style.display = 'none';
  }

  // Event Handlers

  onNodeHover(path) {
    const g = this.nodesGroup.querySelector(`[data-path="${path}"]`);
    if (g) {
      g.querySelector('.node-ring').setAttribute('opacity', '0.5');
    }
  }

  onNodeLeave(path) {
    const g = this.nodesGroup.querySelector(`[data-path="${path}"]`);
    const node = this.nodes.get(path);
    if (g && node.status !== 'reading' && node.status !== 'editing') {
      g.querySelector('.node-ring').setAttribute('opacity', '0');
    }
  }

  onNodeClick(path) {
    this.showFileDetails(path);
    this.highlightConnections(path);
  }

  onNodeRightClick(path, event) {
    event.preventDefault();
    event.stopPropagation();
    
    // Show context menu
    if (window.treeContextMenu) {
      window.treeContextMenu.show(path, event.clientX, event.clientY, event.target);
    }
  }

  highlightConnections(path) {
    const node = this.nodes.get(path);
    if (!node) return;

    // Dim all edges
    this.edgesGroup.querySelectorAll('.tree-edge').forEach(edge => {
      edge.setAttribute('opacity', '0.2');
    });

    // Highlight connected edges
    node.connections.forEach(connPath => {
      const edgeId1 = `${path}->${connPath}`;
      const edgeId2 = `${connPath}->${path}`;
      
      const edge1 = this.edgesGroup.querySelector(`[data-edge-id="${edgeId1}"]`);
      const edge2 = this.edgesGroup.querySelector(`[data-edge-id="${edgeId2}"]`);
      
      if (edge1) edge1.setAttribute('opacity', '1');
      if (edge2) edge2.setAttribute('opacity', '1');
    });
  }

  highlightDependents(path) {
    const node = this.nodes.get(path);
    if (!node) return;

    // Dim all edges
    this.edgesGroup.querySelectorAll('.tree-edge').forEach(edge => {
      edge.setAttribute('opacity', '0.2');
    });

    // Dim all nodes
    this.nodesGroup.querySelectorAll('.tree-node').forEach(n => {
      n.style.opacity = '0.3';
    });

    // Highlight this node
    const thisNode = this.nodesGroup.querySelector(`[data-path="${path}"]`);
    if (thisNode) thisNode.style.opacity = '1';

    // Find and highlight dependents (files that depend on this file)
    this.edges.forEach((edge, edgeId) => {
      if (edge.to === path) {
        // This edge points TO our file, so 'from' depends on us
        const edgeElement = this.edgesGroup.querySelector(`[data-edge-id="${edgeId}"]`);
        if (edgeElement) edgeElement.setAttribute('opacity', '1');
        
        const dependentNode = this.nodesGroup.querySelector(`[data-path="${edge.from}"]`);
        if (dependentNode) dependentNode.style.opacity = '1';
      }
    });
  }

  centerView() {
    // Center the view on the root node
    // TODO: Implement panning/zooming
    console.log('Center view');
  }

  // Helpers

  getFileName(path) {
    return path.split('/').pop() || path;
  }

  getFileType(path) {
    const ext = path.split('.').pop();
    const typeMap = {
      'js': 'javascript',
      'ts': 'typescript',
      'py': 'python',
      'css': 'style',
      'html': 'markup',
      'json': 'config'
    };
    return typeMap[ext] || 'file';
  }

  getFileIcon(type) {
    const icons = {
      'javascript': '📜',
      'typescript': '📘',
      'python': '🐍',
      'style': '🎨',
      'markup': '📄',
      'config': '⚙️',
      'directory': '📁',
      'file': '📄'
    };
    return icons[type] || '📄';
  }

  getStatusColor(status) {
    const colors = {
      'reading': '#58a6ff',
      'editing': '#3fb950',
      'creating': '#d29922',
      'connected': '#bc8cff',
      'analyzed': '#39c5cf',
      'idle': '#6e7681'
    };
    return colors[status] || '#6e7681';
  }

  getActivityIcon(action) {
    const icons = {
      'read': '👁️',
      'edit': '✏️',
      'create': '✨',
      'delete': '🗑️',
      'analyze': '🔍'
    };
    return icons[action] || '📝';
  }

  getActivityLabel(action) {
    const labels = {
      'read': 'Reading',
      'edit': 'Editing',
      'create': 'Creating',
      'delete': 'Deleting',
      'analyze': 'Analyzing'
    };
    return labels[action] || action;
  }
}

// Initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.livingTree = new LivingTree();
  });
} else {
  window.livingTree = new LivingTree();
}
