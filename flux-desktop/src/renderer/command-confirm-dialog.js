// Command Confirmation Dialog
// Shows before executing potentially dangerous commands

class CommandConfirmDialog {
  constructor() {
    this.isOpen = false;
    this.currentCommand = null;
    this.analysis = null;
    this.onConfirm = null;
    this.onCancel = null;
    this.onEdit = null;
    
    this.init();
  }
  
  init() {
    this.createElements();
    this.attachEventListeners();
  }
  
  createElements() {
    // Create overlay
    this.overlay = document.createElement('div');
    this.overlay.className = 'command-confirm-overlay';
    this.overlay.style.display = 'none';
    
    // Create dialog
    this.dialog = document.createElement('div');
    this.dialog.className = 'command-confirm-dialog';
    
    // Dialog content will be dynamically generated
    this.overlay.appendChild(this.dialog);
    document.body.appendChild(this.overlay);
  }
  
  attachEventListeners() {
    // Overlay click to cancel
    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) {
        this.cancel();
      }
    });
    
    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (!this.isOpen) return;
      
      if (e.key === 'Escape') {
        e.preventDefault();
        this.cancel();
      } else if (e.key === 'Enter' && !e.shiftKey && !this.analysis.shouldBlock) {
        e.preventDefault();
        this.confirm();
      }
    });
  }
  
  /**
   * Show confirmation dialog
   * @param {string} command - The command to confirm
   * @param {Object} analysis - Analysis from CommandIntelligence
   * @param {Function} onConfirm - Callback when confirmed
   * @param {Function} onCancel - Callback when cancelled
   * @param {Function} onEdit - Callback when edit requested
   */
  show(command, analysis, onConfirm, onCancel, onEdit) {
    this.currentCommand = command;
    this.analysis = analysis;
    this.onConfirm = onConfirm;
    this.onCancel = onCancel;
    this.onEdit = onEdit;
    
    this.render();
    this.isOpen = true;
    this.overlay.style.display = 'flex';
    
    // Animation
    this.dialog.style.animation = 'slideDown 0.2s ease-out';
    
    // Focus first button
    setTimeout(() => {
      const firstBtn = this.dialog.querySelector('button');
      if (firstBtn) firstBtn.focus();
    }, 100);
  }
  
  render() {
    const { risk, typoCorrection, shouldBlock, parsed } = this.analysis;
    
    // Header based on risk level
    let header = '';
    if (risk.level === 'critical') {
      header = `<div class="dialog-header critical">
        <div class="dialog-icon">${risk.icon}</div>
        <div class="dialog-title">STOP! Critical Risk Detected</div>
      </div>`;
    } else if (risk.level === 'high') {
      header = `<div class="dialog-header high">
        <div class="dialog-icon">${risk.icon}</div>
        <div class="dialog-title">High Risk Command</div>
      </div>`;
    } else if (risk.level === 'medium') {
      header = `<div class="dialog-header medium">
        <div class="dialog-icon">${risk.icon}</div>
        <div class="dialog-title">Confirm Command</div>
      </div>`;
    } else {
      header = `<div class="dialog-header low">
        <div class="dialog-icon">${risk.icon}</div>
        <div class="dialog-title">Review Command</div>
      </div>`;
    }
    
    // Command display
    const commandDisplay = `
      <div class="dialog-command">
        <div class="dialog-label">You typed:</div>
        <code class="command-code">${this.escapeHtml(this.currentCommand)}</code>
      </div>
    `;
    
    // Typo suggestion
    let typoSection = '';
    if (typoCorrection) {
      typoSection = `
        <div class="dialog-typo">
          <div class="typo-icon">💡</div>
          <div class="typo-content">
            <div class="typo-title">Did you mean "${typoCorrection.correction}"?</div>
            <div class="typo-suggestion">
              <code>${this.escapeHtml(typoCorrection.correctedCommand)}</code>
            </div>
            <button class="btn-typo-fix" data-action="fix-typo">Use This Instead</button>
          </div>
        </div>
      `;
    }
    
    // Risk explanation
    const explanation = `
      <div class="dialog-explanation">
        <div class="dialog-label">This command will:</div>
        <div class="explanation-reason">${risk.reason}</div>
        ${risk.alternative ? `
          <div class="explanation-alternative">
            <strong>💡 Safer alternative:</strong><br>
            ${risk.alternative}
          </div>
        ` : ''}
      </div>
    `;
    
    // Command details
    const details = `
      <div class="dialog-details">
        <div class="detail-item">
          <span class="detail-label">Risk Level:</span>
          <span class="detail-value risk-${risk.level}">${risk.level.toUpperCase()}</span>
        </div>
        ${parsed.hasSudo ? '<div class="detail-badge">🔐 Requires sudo</div>' : ''}
        ${parsed.hasPipe ? '<div class="detail-badge">🔀 Uses pipe</div>' : ''}
        ${parsed.hasRedirect ? '<div class="detail-badge">📝 Has redirect</div>' : ''}
      </div>
    `;
    
    // Action buttons
    let buttons = '';
    if (shouldBlock) {
      buttons = `
        <div class="dialog-actions">
          <button class="btn-secondary" data-action="cancel">Cancel</button>
          <button class="btn-secondary" data-action="edit">Edit Command</button>
          <button class="btn-danger" data-action="force">I Know What I'm Doing</button>
        </div>
      `;
    } else {
      buttons = `
        <div class="dialog-actions">
          <button class="btn-secondary" data-action="cancel">Cancel</button>
          <button class="btn-secondary" data-action="edit">Edit</button>
          <button class="btn-primary" data-action="confirm">Continue</button>
        </div>
        <div class="dialog-hint">
          <kbd>Enter</kbd> continue • <kbd>Esc</kbd> cancel
        </div>
      `;
    }
    
    // Assemble dialog
    this.dialog.innerHTML = `
      ${header}
      <div class="dialog-body">
        ${commandDisplay}
        ${typoSection}
        ${explanation}
        ${details}
      </div>
      ${buttons}
    `;
    
    // Attach button listeners
    this.dialog.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = btn.dataset.action;
        this.handleAction(action);
      });
    });
  }
  
  handleAction(action) {
    switch (action) {
      case 'confirm':
      case 'force':
        this.confirm();
        break;
      case 'cancel':
        this.cancel();
        break;
      case 'edit':
        this.edit();
        break;
      case 'fix-typo':
        this.fixTypo();
        break;
    }
  }
  
  confirm() {
    this.close();
    if (this.onConfirm) {
      this.onConfirm(this.currentCommand);
    }
  }
  
  cancel() {
    this.close();
    if (this.onCancel) {
      this.onCancel();
    }
  }
  
  edit() {
    this.close();
    if (this.onEdit) {
      this.onEdit(this.currentCommand);
    }
  }
  
  fixTypo() {
    if (this.analysis.typoCorrection) {
      this.close();
      if (this.onEdit) {
        this.onEdit(this.analysis.typoCorrection.correctedCommand);
      }
    }
  }
  
  close() {
    this.isOpen = false;
    this.dialog.style.animation = 'slideUp 0.15s ease-in';
    setTimeout(() => {
      this.overlay.style.display = 'none';
      this.currentCommand = null;
      this.analysis = null;
    }, 150);
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize
if (typeof window !== 'undefined') {
  window.CommandConfirmDialog = CommandConfirmDialog;
  window.commandConfirmDialog = new CommandConfirmDialog();
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CommandConfirmDialog;
}
