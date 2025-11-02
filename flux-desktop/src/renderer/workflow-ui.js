// Workflow UI Components
// Selector dialog, progress display, and execution controls

class WorkflowUI {
  constructor(workflowEngine) {
    this.engine = workflowEngine;
    this.selectorDialog = null;
    this.progressDialog = null;
    this.currentExecution = null;
    
    this.setupEventListeners();
  }
  
  setupEventListeners() {
    // Listen to workflow engine events
    this.engine.on('start', (data) => this.onWorkflowStart(data));
    this.engine.on('step-start', (data) => this.onStepStart(data));
    this.engine.on('step-complete', (data) => this.onStepComplete(data));
    this.engine.on('step-error', (data) => this.onStepError(data));
    this.engine.on('complete', (data) => this.onWorkflowComplete(data));
    this.engine.on('error', (data) => this.onWorkflowError(data));
    this.engine.on('cancelled', () => this.onWorkflowCancelled());
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Cmd/Ctrl+Shift+W to open workflow selector
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'w') {
        e.preventDefault();
        this.showWorkflowSelector();
      }
      
      // Escape to close dialogs
      if (e.key === 'Escape') {
        if (this.selectorDialog) {
          this.closeSelector();
        }
      }
    });
  }
  
  /**
   * Show workflow selector dialog
   */
  showWorkflowSelector() {
    const workflows = this.engine.listWorkflows();
    
    if (workflows.length === 0) {
      this.showNoWorkflowsMessage();
      return;
    }
    
    // Create dialog
    this.selectorDialog = document.createElement('div');
    this.selectorDialog.className = 'workflow-selector-overlay';
    this.selectorDialog.innerHTML = `
      <div class="workflow-selector-dialog">
        <div class="workflow-selector-header">
          <h2>🚀 Select Workflow</h2>
          <button class="workflow-close-btn" aria-label="Close">×</button>
        </div>
        
        <div class="workflow-search-box">
          <input type="text" 
                 placeholder="Search workflows..." 
                 class="workflow-search-input"
                 autofocus>
        </div>
        
        <div class="workflow-list">
          ${workflows.map((workflow, index) => `
            <div class="workflow-item" data-workflow-name="${workflow.name}" data-index="${index}">
              <div class="workflow-item-header">
                <span class="workflow-item-name">${workflow.name}</span>
                ${workflow.tags ? `
                  <div class="workflow-item-tags">
                    ${workflow.tags.map(tag => `<span class="workflow-tag">${tag}</span>`).join('')}
                  </div>
                ` : ''}
              </div>
              <div class="workflow-item-description">${workflow.description || 'No description'}</div>
              <div class="workflow-item-meta">
                ${workflow.steps.length} steps
                ${workflow.author ? `· by ${workflow.author}` : ''}
              </div>
            </div>
          `).join('')}
        </div>
        
        <div class="workflow-selector-footer">
          <div class="workflow-shortcuts">
            <span><kbd>↑↓</kbd> Navigate</span>
            <span><kbd>Enter</kbd> Run</span>
            <span><kbd>Esc</kbd> Close</span>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(this.selectorDialog);
    
    // Setup interactions
    this.setupSelectorInteractions();
  }
  
  setupSelectorInteractions() {
    const dialog = this.selectorDialog;
    const searchInput = dialog.querySelector('.workflow-search-input');
    const workflowItems = dialog.querySelectorAll('.workflow-item');
    const closeBtn = dialog.querySelector('.workflow-close-btn');
    
    let selectedIndex = 0;
    
    // Highlight first item
    if (workflowItems.length > 0) {
      workflowItems[0].classList.add('selected');
    }
    
    // Search functionality
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      let visibleIndex = 0;
      
      workflowItems.forEach((item, index) => {
        const name = item.querySelector('.workflow-item-name').textContent.toLowerCase();
        const description = item.querySelector('.workflow-item-description').textContent.toLowerCase();
        const matches = name.includes(query) || description.includes(query);
        
        item.style.display = matches ? 'block' : 'none';
        
        if (matches && visibleIndex === 0) {
          item.classList.add('selected');
          selectedIndex = index;
        } else {
          item.classList.remove('selected');
        }
        
        if (matches) visibleIndex++;
      });
    });
    
    // Keyboard navigation
    searchInput.addEventListener('keydown', (e) => {
      const visibleItems = Array.from(workflowItems).filter(item => item.style.display !== 'none');
      
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const currentSelected = visibleItems.findIndex(item => item.classList.contains('selected'));
        if (currentSelected < visibleItems.length - 1) {
          visibleItems[currentSelected]?.classList.remove('selected');
          visibleItems[currentSelected + 1]?.classList.add('selected');
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const currentSelected = visibleItems.findIndex(item => item.classList.contains('selected'));
        if (currentSelected > 0) {
          visibleItems[currentSelected]?.classList.remove('selected');
          visibleItems[currentSelected - 1]?.classList.add('selected');
        }
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selected = dialog.querySelector('.workflow-item.selected');
        if (selected) {
          const workflowName = selected.dataset.workflowName;
          this.closeSelector();
          this.runWorkflow(workflowName);
        }
      }
    });
    
    // Click to select and run
    workflowItems.forEach((item) => {
      item.addEventListener('click', () => {
        const workflowName = item.dataset.workflowName;
        this.closeSelector();
        this.runWorkflow(workflowName);
      });
    });
    
    // Close button
    closeBtn.addEventListener('click', () => this.closeSelector());
    
    // Click outside to close
    dialog.addEventListener('click', (e) => {
      if (e.target === dialog) {
        this.closeSelector();
      }
    });
  }
  
  closeSelector() {
    if (this.selectorDialog) {
      this.selectorDialog.remove();
      this.selectorDialog = null;
    }
  }
  
  showNoWorkflowsMessage() {
    const message = document.createElement('div');
    message.className = 'workflow-message';
    message.innerHTML = `
      <div class="workflow-message-content">
        <h3>📦 No Workflows Yet</h3>
        <p>Create workflows to automate your tasks.</p>
        <button class="workflow-message-btn">Learn How</button>
      </div>
    `;
    document.body.appendChild(message);
    
    setTimeout(() => message.remove(), 3000);
  }
  
  /**
   * Run workflow with optional variables
   */
  async runWorkflow(workflowName, variables = {}) {
    const workflow = this.engine.getWorkflow(workflowName);
    
    if (!workflow) {
      this.showError(`Workflow "${workflowName}" not found`);
      return;
    }
    
    // If workflow has required variables, prompt for them
    if (workflow.variables && workflow.variables.some(v => v.required)) {
      const inputVariables = await this.promptForVariables(workflow.variables);
      if (!inputVariables) return; // User cancelled
      Object.assign(variables, inputVariables);
    }
    
    // Show progress dialog
    this.showProgressDialog(workflow);
    
    try {
      await this.engine.executeWorkflow(workflowName, variables);
    } catch (error) {
      console.error('Workflow execution error:', error);
    }
  }
  
  /**
   * Prompt user for workflow variables
   */
  async promptForVariables(variableDefs) {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'workflow-selector-overlay';
      overlay.innerHTML = `
        <div class="workflow-variables-dialog">
          <h3>🔧 Workflow Variables</h3>
          <form class="workflow-variables-form">
            ${variableDefs.map(varDef => {
              if (varDef.type === 'select') {
                return `
                  <div class="workflow-variable-field">
                    <label>${varDef.description || varDef.name}</label>
                    <select name="${varDef.name}">
                      ${varDef.options.map(opt => `
                        <option value="${opt}" ${opt === varDef.default ? 'selected' : ''}>${opt}</option>
                      `).join('')}
                    </select>
                  </div>
                `;
              } else {
                return `
                  <div class="workflow-variable-field">
                    <label>${varDef.description || varDef.name}</label>
                    <input type="text" 
                           name="${varDef.name}" 
                           value="${varDef.default || ''}"
                           ${varDef.required ? 'required' : ''}>
                  </div>
                `;
              }
            }).join('')}
            
            <div class="workflow-variables-buttons">
              <button type="submit" class="workflow-btn-primary">Run Workflow</button>
              <button type="button" class="workflow-btn-secondary workflow-cancel-btn">Cancel</button>
            </div>
          </form>
        </div>
      `;
      
      document.body.appendChild(overlay);
      
      const form = overlay.querySelector('.workflow-variables-form');
      const cancelBtn = overlay.querySelector('.workflow-cancel-btn');
      
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const variables = {};
        for (const [key, value] of formData.entries()) {
          variables[key] = value;
        }
        overlay.remove();
        resolve(variables);
      });
      
      cancelBtn.addEventListener('click', () => {
        overlay.remove();
        resolve(null);
      });
      
      // Focus first input
      const firstInput = form.querySelector('input, select');
      if (firstInput) firstInput.focus();
    });
  }
  
  /**
   * Show workflow progress dialog
   */
  showProgressDialog(workflow) {
    this.progressDialog = document.createElement('div');
    this.progressDialog.className = 'workflow-progress-overlay';
    this.progressDialog.innerHTML = `
      <div class="workflow-progress-dialog">
        <div class="workflow-progress-header">
          <h3>🚀 ${workflow.name}</h3>
          <div class="workflow-progress-status">Running...</div>
        </div>
        
        <div class="workflow-progress-bar-container">
          <div class="workflow-progress-bar" style="width: 0%"></div>
        </div>
        
        <div class="workflow-steps-list"></div>
        
        <div class="workflow-progress-controls">
          <button class="workflow-btn-danger workflow-cancel-btn">Cancel</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(this.progressDialog);
    
    // Setup cancel button
    const cancelBtn = this.progressDialog.querySelector('.workflow-cancel-btn');
    cancelBtn.addEventListener('click', () => {
      if (confirm('Cancel workflow execution?')) {
        this.engine.cancelExecution();
      }
    });
  }
  
  /**
   * Update progress dialog
   */
  updateProgress(stepIndex, total) {
    if (!this.progressDialog) return;
    
    const percent = ((stepIndex + 1) / total) * 100;
    const progressBar = this.progressDialog.querySelector('.workflow-progress-bar');
    progressBar.style.width = `${percent}%`;
  }
  
  /**
   * Add step to progress display
   */
  addStepToProgress(step, status = 'running') {
    if (!this.progressDialog) return;
    
    const stepsList = this.progressDialog.querySelector('.workflow-steps-list');
    const stepElement = document.createElement('div');
    stepElement.className = `workflow-step-item workflow-step-${status}`;
    stepElement.dataset.stepName = step.name;
    
    const icons = {
      running: '⏳',
      success: '✅',
      error: '❌',
      pending: '⏸️'
    };
    
    stepElement.innerHTML = `
      <span class="workflow-step-icon">${icons[status]}</span>
      <span class="workflow-step-name">${step.name || step.command || step.type}</span>
    `;
    
    stepsList.appendChild(stepElement);
    
    // Auto-scroll to latest step
    stepElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
  
  /**
   * Update step status in progress display
   */
  updateStepStatus(stepName, status) {
    if (!this.progressDialog) return;
    
    const stepElement = this.progressDialog.querySelector(`[data-step-name="${stepName}"]`);
    if (!stepElement) return;
    
    stepElement.className = `workflow-step-item workflow-step-${status}`;
    
    const icons = {
      running: '⏳',
      success: '✅',
      error: '❌',
      pending: '⏸️'
    };
    
    const icon = stepElement.querySelector('.workflow-step-icon');
    if (icon) icon.textContent = icons[status];
  }
  
  /**
   * Event handlers for workflow execution
   */
  onWorkflowStart(data) {
    console.log('Workflow started:', data);
  }
  
  onStepStart(data) {
    this.updateProgress(data.index, data.workflow?.steps?.length || 1);
    this.addStepToProgress(data.step, 'running');
  }
  
  onStepComplete(data) {
    this.updateStepStatus(data.step.name, 'success');
  }
  
  onStepError(data) {
    this.updateStepStatus(data.step.name, 'error');
  }
  
  onWorkflowComplete(data) {
    if (!this.progressDialog) return;
    
    const status = this.progressDialog.querySelector('.workflow-progress-status');
    status.textContent = '✅ Complete!';
    status.style.color = '#10b981';
    
    const controls = this.progressDialog.querySelector('.workflow-progress-controls');
    controls.innerHTML = `
      <button class="workflow-btn-primary workflow-close-btn">Done</button>
    `;
    
    const closeBtn = controls.querySelector('.workflow-close-btn');
    closeBtn.addEventListener('click', () => this.closeProgress());
    
    // Auto-close after 3 seconds
    setTimeout(() => this.closeProgress(), 3000);
  }
  
  onWorkflowError(data) {
    if (!this.progressDialog) return;
    
    const status = this.progressDialog.querySelector('.workflow-progress-status');
    status.textContent = '❌ Failed';
    status.style.color = '#ef4444';
    
    const controls = this.progressDialog.querySelector('.workflow-progress-controls');
    controls.innerHTML = `
      <button class="workflow-btn-secondary workflow-close-btn">Close</button>
    `;
    
    const closeBtn = controls.querySelector('.workflow-close-btn');
    closeBtn.addEventListener('click', () => this.closeProgress());
  }
  
  onWorkflowCancelled() {
    if (!this.progressDialog) return;
    
    const status = this.progressDialog.querySelector('.workflow-progress-status');
    status.textContent = '⏸️ Cancelled';
    status.style.color = '#f59e0b';
    
    const controls = this.progressDialog.querySelector('.workflow-progress-controls');
    controls.innerHTML = `
      <button class="workflow-btn-secondary workflow-close-btn">Close</button>
    `;
    
    const closeBtn = controls.querySelector('.workflow-close-btn');
    closeBtn.addEventListener('click', () => this.closeProgress());
  }
  
  closeProgress() {
    if (this.progressDialog) {
      this.progressDialog.remove();
      this.progressDialog = null;
    }
  }
  
  showError(message) {
    const errorEl = document.createElement('div');
    errorEl.className = 'workflow-error-toast';
    errorEl.textContent = message;
    document.body.appendChild(errorEl);
    
    setTimeout(() => errorEl.remove(), 3000);
  }
}

// Export for use in renderer
if (typeof module !== 'undefined' && module.exports) {
  module.exports = WorkflowUI;
}
