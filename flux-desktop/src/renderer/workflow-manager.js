// Workflow Manager UI
// Library browser, editor, import/export functionality

class WorkflowManager {
  constructor(workflowEngine) {
    this.engine = workflowEngine;
    this.managerDialog = null;
    this.editorDialog = null;
    this.currentWorkflow = null;
    
    this.setupEventListeners();
  }
  
  setupEventListeners() {
    // Keyboard shortcut: Cmd/Ctrl+Shift+M for Manager
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'm') {
        e.preventDefault();
        this.showManager();
      }
    });
  }
  
  /**
   * Show workflow library manager
   */
  showManager() {
    const workflows = this.engine.listWorkflows();
    
    this.managerDialog = document.createElement('div');
    this.managerDialog.className = 'workflow-manager-overlay';
    this.managerDialog.innerHTML = `
      <div class="workflow-manager-dialog">
        <div class="workflow-manager-header">
          <h2>📚 Workflow Library</h2>
          <div class="workflow-manager-actions">
            <button class="workflow-btn-secondary workflow-import-btn">
              📥 Import
            </button>
            <button class="workflow-btn-primary workflow-new-btn">
              ➕ New Workflow
            </button>
            <button class="workflow-close-btn" aria-label="Close">×</button>
          </div>
        </div>
        
        <div class="workflow-manager-toolbar">
          <div class="workflow-search-box">
            <input type="text" 
                   placeholder="Search workflows..." 
                   class="workflow-search-input">
          </div>
          <div class="workflow-filters">
            <select class="workflow-sort-select">
              <option value="name">Sort by Name</option>
              <option value="recent">Recently Used</option>
              <option value="steps">Most Steps</option>
            </select>
            <select class="workflow-tag-filter">
              <option value="">All Tags</option>
              ${this.getAllTags(workflows).map(tag => `<option value="${tag}">${tag}</option>`).join('')}
            </select>
          </div>
        </div>
        
        <div class="workflow-library-grid">
          ${workflows.length === 0 ? `
            <div class="workflow-empty-state">
              <div class="workflow-empty-icon">📦</div>
              <h3>No Workflows Yet</h3>
              <p>Create your first workflow to get started</p>
              <button class="workflow-btn-primary workflow-create-first-btn">
                Create Workflow
              </button>
            </div>
          ` : workflows.map(workflow => this.renderWorkflowCard(workflow)).join('')}
        </div>
      </div>
    `;
    
    document.body.appendChild(this.managerDialog);
    this.setupManagerInteractions();
  }
  
  /**
   * Render workflow card in library
   */
  renderWorkflowCard(workflow) {
    const tags = workflow.tags ? workflow.tags.map(tag => 
      `<span class="workflow-card-tag">${tag}</span>`
    ).join('') : '';
    
    return `
      <div class="workflow-card" data-workflow-name="${workflow.name}">
        <div class="workflow-card-header">
          <h3>${workflow.name}</h3>
          <div class="workflow-card-menu">
            <button class="workflow-card-menu-btn">⋮</button>
            <div class="workflow-card-menu-dropdown">
              <button data-action="run">▶️ Run</button>
              <button data-action="edit">✏️ Edit</button>
              <button data-action="duplicate">📋 Duplicate</button>
              <button data-action="export">📤 Export</button>
              <button data-action="delete">🗑️ Delete</button>
            </div>
          </div>
        </div>
        <p class="workflow-card-description">${workflow.description || 'No description'}</p>
        <div class="workflow-card-tags">${tags}</div>
        <div class="workflow-card-meta">
          <span>📝 ${workflow.steps.length} steps</span>
          ${workflow.author ? `<span>👤 ${workflow.author}</span>` : ''}
        </div>
      </div>
    `;
  }
  
  /**
   * Get all unique tags from workflows
   */
  getAllTags(workflows) {
    const tags = new Set();
    workflows.forEach(workflow => {
      if (workflow.tags) {
        workflow.tags.forEach(tag => tags.add(tag));
      }
    });
    return Array.from(tags).sort();
  }
  
  /**
   * Setup manager interactions
   */
  setupManagerInteractions() {
    const dialog = this.managerDialog;
    const searchInput = dialog.querySelector('.workflow-search-input');
    const sortSelect = dialog.querySelector('.workflow-sort-select');
    const tagFilter = dialog.querySelector('.workflow-tag-filter');
    const closeBtn = dialog.querySelector('.workflow-close-btn');
    const newBtn = dialog.querySelector('.workflow-new-btn');
    const importBtn = dialog.querySelector('.workflow-import-btn');
    
    // Search
    searchInput?.addEventListener('input', (e) => {
      this.filterWorkflows(e.target.value, sortSelect.value, tagFilter.value);
    });
    
    // Sort
    sortSelect?.addEventListener('change', (e) => {
      this.filterWorkflows(searchInput.value, e.target.value, tagFilter.value);
    });
    
    // Tag filter
    tagFilter?.addEventListener('change', (e) => {
      this.filterWorkflows(searchInput.value, sortSelect.value, e.target.value);
    });
    
    // Close
    closeBtn?.addEventListener('click', () => this.closeManager());
    
    // New workflow
    newBtn?.addEventListener('click', () => this.createNewWorkflow());
    
    // Import
    importBtn?.addEventListener('click', () => this.showImportDialog());
    
    // Card actions
    dialog.querySelectorAll('.workflow-card').forEach(card => {
      const workflowName = card.dataset.workflowName;
      const menuBtn = card.querySelector('.workflow-card-menu-btn');
      const dropdown = card.querySelector('.workflow-card-menu-dropdown');
      
      // Toggle dropdown
      menuBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
      });
      
      // Handle actions
      dropdown?.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const action = e.target.dataset.action;
          this.handleWorkflowAction(workflowName, action);
          dropdown.classList.remove('show');
        });
      });
      
      // Click card to run
      card.addEventListener('click', () => {
        this.closeManager();
        // Trigger workflow run (integrate with WorkflowUI)
        window.dispatchEvent(new CustomEvent('run-workflow', { detail: { name: workflowName } }));
      });
    });
    
    // Close dropdown on outside click
    document.addEventListener('click', () => {
      dialog.querySelectorAll('.workflow-card-menu-dropdown.show').forEach(d => {
        d.classList.remove('show');
      });
    });
  }
  
  /**
   * Filter workflows based on search, sort, and tags
   */
  filterWorkflows(searchQuery, sortBy, tagFilter) {
    let workflows = this.engine.listWorkflows();
    
    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      workflows = workflows.filter(w => 
        w.name.toLowerCase().includes(query) ||
        (w.description && w.description.toLowerCase().includes(query))
      );
    }
    
    // Filter by tag
    if (tagFilter) {
      workflows = workflows.filter(w => 
        w.tags && w.tags.includes(tagFilter)
      );
    }
    
    // Sort
    workflows.sort((a, b) => {
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortBy === 'steps') {
        return b.steps.length - a.steps.length;
      }
      return 0; // recent (would need usage tracking)
    });
    
    // Re-render grid
    const grid = this.managerDialog.querySelector('.workflow-library-grid');
    grid.innerHTML = workflows.map(w => this.renderWorkflowCard(w)).join('');
    
    // Re-attach event listeners
    this.setupManagerInteractions();
  }
  
  /**
   * Handle workflow actions (run, edit, duplicate, export, delete)
   */
  handleWorkflowAction(workflowName, action) {
    const workflow = this.engine.getWorkflow(workflowName);
    
    switch (action) {
      case 'run':
        this.closeManager();
        window.dispatchEvent(new CustomEvent('run-workflow', { detail: { name: workflowName } }));
        break;
      case 'edit':
        this.showEditor(workflow);
        break;
      case 'duplicate':
        this.duplicateWorkflow(workflow);
        break;
      case 'export':
        this.exportWorkflow(workflow);
        break;
      case 'delete':
        this.deleteWorkflow(workflowName);
        break;
    }
  }
  
  /**
   * Show workflow editor
   */
  showEditor(workflow = null) {
    const isNew = !workflow;
    this.currentWorkflow = workflow || {
      name: '',
      description: '',
      tags: [],
      variables: [],
      steps: []
    };
    
    this.editorDialog = document.createElement('div');
    this.editorDialog.className = 'workflow-editor-overlay';
    this.editorDialog.innerHTML = `
      <div class="workflow-editor-dialog">
        <div class="workflow-editor-header">
          <h2>${isNew ? '➕ New Workflow' : '✏️ Edit Workflow'}</h2>
          <button class="workflow-close-btn" aria-label="Close">×</button>
        </div>
        
        <div class="workflow-editor-content">
          <div class="workflow-editor-sidebar">
            <div class="workflow-editor-section">
              <label>Name</label>
              <input type="text" 
                     class="workflow-input" 
                     id="workflow-name"
                     value="${this.currentWorkflow.name}"
                     placeholder="My Workflow">
            </div>
            
            <div class="workflow-editor-section">
              <label>Description</label>
              <textarea class="workflow-textarea" 
                        id="workflow-description"
                        placeholder="What does this workflow do?">${this.currentWorkflow.description || ''}</textarea>
            </div>
            
            <div class="workflow-editor-section">
              <label>Tags (comma-separated)</label>
              <input type="text" 
                     class="workflow-input" 
                     id="workflow-tags"
                     value="${this.currentWorkflow.tags?.join(', ') || ''}"
                     placeholder="deploy, git, docker">
            </div>
            
            <div class="workflow-editor-section">
              <label>Author</label>
              <input type="text" 
                     class="workflow-input" 
                     id="workflow-author"
                     value="${this.currentWorkflow.author || ''}"
                     placeholder="Your name">
            </div>
          </div>
          
          <div class="workflow-editor-main">
            <div class="workflow-editor-steps-header">
              <h3>Steps</h3>
              <button class="workflow-btn-secondary workflow-add-step-btn">
                ➕ Add Step
              </button>
            </div>
            
            <div class="workflow-steps-list" id="workflow-steps">
              ${this.currentWorkflow.steps.map((step, index) => 
                this.renderStepEditor(step, index)
              ).join('')}
            </div>
            
            ${this.currentWorkflow.steps.length === 0 ? `
              <div class="workflow-empty-steps">
                <p>No steps yet. Add your first step to get started.</p>
              </div>
            ` : ''}
          </div>
        </div>
        
        <div class="workflow-editor-footer">
          <button class="workflow-btn-secondary workflow-cancel-btn">Cancel</button>
          <button class="workflow-btn-primary workflow-save-btn">Save Workflow</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(this.editorDialog);
    this.setupEditorInteractions();
  }
  
  /**
   * Render step editor
   */
  renderStepEditor(step, index) {
    return `
      <div class="workflow-step-editor" data-step-index="${index}">
        <div class="workflow-step-editor-header">
          <span class="workflow-step-number">${index + 1}</span>
          <select class="workflow-step-type-select" data-step-index="${index}">
            <option value="command" ${step.type === 'command' ? 'selected' : ''}>Command</option>
            <option value="confirm" ${step.type === 'confirm' ? 'selected' : ''}>Confirm</option>
            <option value="input" ${step.type === 'input' ? 'selected' : ''}>Input</option>
            <option value="select" ${step.type === 'select' ? 'selected' : ''}>Select</option>
            <option value="conditional" ${step.type === 'conditional' ? 'selected' : ''}>Conditional</option>
            <option value="parallel" ${step.type === 'parallel' ? 'selected' : ''}>Parallel</option>
            <option value="success" ${step.type === 'success' ? 'selected' : ''}>Success</option>
            <option value="error" ${step.type === 'error' ? 'selected' : ''}>Error</option>
          </select>
          <button class="workflow-step-delete-btn" data-step-index="${index}">🗑️</button>
        </div>
        
        <div class="workflow-step-editor-fields">
          ${this.renderStepFields(step, index)}
        </div>
      </div>
    `;
  }
  
  /**
   * Render step-specific fields
   */
  renderStepFields(step, index) {
    switch (step.type) {
      case 'command':
        return `
          <input type="text" 
                 placeholder="Step name (optional)" 
                 value="${step.name || ''}"
                 data-field="name"
                 data-step-index="${index}">
          <input type="text" 
                 placeholder="Command (e.g., npm test)" 
                 value="${step.command || ''}"
                 data-field="command"
                 data-step-index="${index}">
        `;
      case 'confirm':
        return `
          <input type="text" 
                 placeholder="Confirmation message" 
                 value="${step.message || ''}"
                 data-field="message"
                 data-step-index="${index}">
        `;
      case 'input':
        return `
          <input type="text" 
                 placeholder="Prompt message" 
                 value="${step.prompt || ''}"
                 data-field="prompt"
                 data-step-index="${index}">
          <input type="text" 
                 placeholder="Variable name (e.g., commitMessage)" 
                 value="${step.variable || ''}"
                 data-field="variable"
                 data-step-index="${index}">
        `;
      case 'success':
      case 'error':
        return `
          <input type="text" 
                 placeholder="Message" 
                 value="${step.message || ''}"
                 data-field="message"
                 data-step-index="${index}">
        `;
      default:
        return `<p>Configure ${step.type} step</p>`;
    }
  }
  
  /**
   * Setup editor interactions
   */
  setupEditorInteractions() {
    const dialog = this.editorDialog;
    const closeBtn = dialog.querySelector('.workflow-close-btn');
    const cancelBtn = dialog.querySelector('.workflow-cancel-btn');
    const saveBtn = dialog.querySelector('.workflow-save-btn');
    const addStepBtn = dialog.querySelector('.workflow-add-step-btn');
    
    // Close/Cancel
    closeBtn?.addEventListener('click', () => this.closeEditor());
    cancelBtn?.addEventListener('click', () => this.closeEditor());
    
    // Save
    saveBtn?.addEventListener('click', () => this.saveWorkflow());
    
    // Add step
    addStepBtn?.addEventListener('click', () => this.addStep());
    
    // Step type change
    dialog.querySelectorAll('.workflow-step-type-select').forEach(select => {
      select.addEventListener('change', (e) => {
        const index = parseInt(e.target.dataset.stepIndex);
        this.currentWorkflow.steps[index].type = e.target.value;
        this.refreshEditor();
      });
    });
    
    // Delete step
    dialog.querySelectorAll('.workflow-step-delete-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.target.dataset.stepIndex);
        this.currentWorkflow.steps.splice(index, 1);
        this.refreshEditor();
      });
    });
    
    // Field changes
    dialog.querySelectorAll('[data-field]').forEach(input => {
      input.addEventListener('input', (e) => {
        const index = parseInt(e.target.dataset.stepIndex);
        const field = e.target.dataset.field;
        this.currentWorkflow.steps[index][field] = e.target.value;
      });
    });
  }
  
  /**
   * Add new step
   */
  addStep() {
    this.currentWorkflow.steps.push({
      type: 'command',
      name: '',
      command: ''
    });
    this.refreshEditor();
  }
  
  /**
   * Refresh editor UI
   */
  refreshEditor() {
    const stepsList = this.editorDialog.querySelector('#workflow-steps');
    stepsList.innerHTML = this.currentWorkflow.steps.map((step, index) => 
      this.renderStepEditor(step, index)
    ).join('');
    this.setupEditorInteractions();
  }
  
  /**
   * Save workflow
   */
  saveWorkflow() {
    // Collect form data
    const name = this.editorDialog.querySelector('#workflow-name').value;
    const description = this.editorDialog.querySelector('#workflow-description').value;
    const tagsInput = this.editorDialog.querySelector('#workflow-tags').value;
    const author = this.editorDialog.querySelector('#workflow-author').value;
    
    if (!name) {
      alert('Please provide a workflow name');
      return;
    }
    
    const workflow = {
      ...this.currentWorkflow,
      name,
      description,
      tags: tagsInput ? tagsInput.split(',').map(t => t.trim()) : [],
      author
    };
    
    // Register with engine
    this.engine.registerWorkflow(workflow);
    
    // Save to localStorage
    this.saveToLocalStorage();
    
    // Close editor and refresh manager
    this.closeEditor();
    if (this.managerDialog) {
      this.closeManager();
      this.showManager();
    }
    
    this.showNotification(`✅ Workflow "${name}" saved!`);
  }
  
  /**
   * Create new workflow
   */
  createNewWorkflow() {
    this.closeManager();
    this.showEditor(null);
  }
  
  /**
   * Duplicate workflow
   */
  duplicateWorkflow(workflow) {
    const duplicate = {
      ...workflow,
      name: `${workflow.name} (Copy)`,
      steps: [...workflow.steps]
    };
    this.showEditor(duplicate);
  }
  
  /**
   * Export workflow as JSON
   */
  exportWorkflow(workflow) {
    const json = JSON.stringify(workflow, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflow.name.replace(/\s+/g, '-').toLowerCase()}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
    this.showNotification(`📤 Exported "${workflow.name}"`);
  }
  
  /**
   * Show import dialog
   */
  showImportDialog() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const workflow = JSON.parse(event.target.result);
            this.engine.registerWorkflow(workflow);
            this.saveToLocalStorage();
            this.closeManager();
            this.showManager();
            this.showNotification(`📥 Imported "${workflow.name}"`);
          } catch (error) {
            alert('Invalid workflow file');
          }
        };
        reader.readAsText(file);
      }
    });
    
    input.click();
  }
  
  /**
   * Delete workflow
   */
  deleteWorkflow(workflowName) {
    if (confirm(`Delete workflow "${workflowName}"?`)) {
      // Remove from engine
      this.engine.workflows.delete(workflowName);
      this.saveToLocalStorage();
      
      // Refresh UI
      this.closeManager();
      this.showManager();
      
      this.showNotification(`🗑️ Deleted "${workflowName}"`);
    }
  }
  
  /**
   * Save all workflows to localStorage
   */
  saveToLocalStorage() {
    const workflows = this.engine.listWorkflows();
    localStorage.setItem('flux-workflows', JSON.stringify(workflows));
  }
  
  /**
   * Load workflows from localStorage
   */
  loadFromLocalStorage() {
    const saved = localStorage.getItem('flux-workflows');
    if (saved) {
      try {
        const workflows = JSON.parse(saved);
        workflows.forEach(w => this.engine.registerWorkflow(w));
      } catch (error) {
        console.error('Failed to load workflows:', error);
      }
    }
  }
  
  /**
   * Show notification
   */
  showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'workflow-notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.add('show'), 10);
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }
  
  closeManager() {
    if (this.managerDialog) {
      this.managerDialog.remove();
      this.managerDialog = null;
    }
  }
  
  closeEditor() {
    if (this.editorDialog) {
      this.editorDialog.remove();
      this.editorDialog = null;
    }
  }
}

// Export for use in renderer
if (typeof module !== 'undefined' && module.exports) {
  module.exports = WorkflowManager;
}
