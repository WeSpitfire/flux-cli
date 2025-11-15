// Tree Context Menu - Interactive actions for file nodes
class TreeContextMenu {
  constructor() {
    this.menu = null;
    this.currentPath = null;
    this.currentNode = null;
    this.init();
  }

  init() {
    // Create menu element
    this.menu = document.createElement('div');
    this.menu.className = 'tree-context-menu';
    this.menu.style.display = 'none';
    document.body.appendChild(this.menu);

    // Close menu on outside click
    document.addEventListener('click', (e) => {
      if (!this.menu.contains(e.target)) {
        this.hide();
      }
    });

    // Close menu on escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.hide();
      }
    });

    // Prevent default context menu
    document.addEventListener('contextmenu', (e) => {
      if (e.target.closest('.tree-node')) {
        e.preventDefault();
      }
    });
  }

  show(path, x, y, nodeElement) {
    this.currentPath = path;
    this.currentNode = nodeElement;

    // Build menu items
    const items = [
      {
        icon: '📂',
        label: 'Open in Editor',
        shortcut: 'Enter',
        action: () => this.openInEditor(path)
      },
      {
        icon: '👁️',
        label: 'View Content',
        shortcut: 'Space',
        action: () => this.viewContent(path)
      },
      { separator: true },
      {
        icon: '📋',
        label: 'Copy Path',
        shortcut: '⌘C',
        action: () => this.copyPath(path)
      },
      {
        icon: '📄',
        label: 'Copy Filename',
        action: () => this.copyFilename(path)
      },
      { separator: true },
      {
        icon: '🔍',
        label: 'Show in Finder',
        shortcut: '⌘⇧R',
        action: () => this.showInFinder(path)
      },
      {
        icon: '📊',
        label: 'Show Git Blame',
        action: () => this.showGitBlame(path),
        disabled: !this.isGitRepo()
      },
      { separator: true },
      {
        icon: '🔗',
        label: 'Show Dependencies',
        action: () => this.showDependencies(path)
      },
      {
        icon: '📈',
        label: 'Show Dependents',
        action: () => this.showDependents(path)
      },
      { separator: true },
      {
        icon: '✏️',
        label: 'Ask Flux to Edit',
        action: () => this.askFluxToEdit(path)
      },
      {
        icon: '🔄',
        label: 'Ask Flux to Refactor',
        action: () => this.askFluxToRefactor(path)
      }
    ];

    // Render menu
    this.menu.innerHTML = items.map(item => {
      if (item.separator) {
        return '<div class="context-menu-separator"></div>';
      }

      const disabledClass = item.disabled ? ' disabled' : '';
      const shortcut = item.shortcut ? `<span class="context-menu-shortcut">${item.shortcut}</span>` : '';

      return `
        <div class="context-menu-item${disabledClass}" data-action="${items.indexOf(item)}">
          <span class="context-menu-icon">${item.icon}</span>
          <span class="context-menu-label">${item.label}</span>
          ${shortcut}
        </div>
      `;
    }).join('');

    // Add click handlers
    this.menu.querySelectorAll('.context-menu-item:not(.disabled)').forEach(item => {
      const index = parseInt(item.dataset.action);
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        items[index].action();
        this.hide();
      });
    });

    // Position menu
    this.position(x, y);
    this.menu.style.display = 'block';

    // Animate in
    requestAnimationFrame(() => {
      this.menu.classList.add('show');
    });
  }

  hide() {
    this.menu.classList.remove('show');
    setTimeout(() => {
      this.menu.style.display = 'none';
    }, 150);
  }

  position(x, y) {
    // Get menu dimensions
    this.menu.style.display = 'block';
    const menuRect = this.menu.getBoundingClientRect();
    this.menu.style.display = 'none';

    // Get viewport dimensions
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Adjust position to keep menu in viewport
    let left = x;
    let top = y;

    if (left + menuRect.width > viewportWidth) {
      left = viewportWidth - menuRect.width - 10;
    }

    if (top + menuRect.height > viewportHeight) {
      top = viewportHeight - menuRect.height - 10;
    }

    this.menu.style.left = `${left}px`;
    this.menu.style.top = `${top}px`;
  }

  // Action implementations

  async openInEditor(path) {
    console.log('[TreeContextMenu] Opening in editor:', path);
    
    try {
      // Try to use system default editor
      if (window.electron && window.electron.openInEditor) {
        await window.electron.openInEditor(path);
      } else {
        // Fallback: use 'open' command on macOS
        this.showNotification('Opening file...', 'info');
        // This would need to be implemented in main process
        console.warn('openInEditor not available in electron bridge');
      }
    } catch (error) {
      this.showNotification(`Failed to open file: ${error.message}`, 'error');
    }
  }

  async viewContent(path) {
    console.log('[TreeContextMenu] Viewing content:', path);
    
    try {
      // Trigger Flux command to read the file
      if (window.flux && window.flux.sendCommand) {
        const tabId = window.tabManager?.getActiveTabId();
        if (tabId) {
          window.flux.sendCommand(tabId, `read ${path}`);
          this.showNotification('Reading file...', 'info');
        }
      }
    } catch (error) {
      this.showNotification(`Failed to read file: ${error.message}`, 'error');
    }
  }

  copyPath(path) {
    console.log('[TreeContextMenu] Copying path:', path);
    
    try {
      // Use Clipboard API
      navigator.clipboard.writeText(path).then(() => {
        this.showNotification('Path copied to clipboard', 'success');
      }).catch(err => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = path;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        this.showNotification('Path copied to clipboard', 'success');
      });
    } catch (error) {
      this.showNotification(`Failed to copy: ${error.message}`, 'error');
    }
  }

  copyFilename(path) {
    const filename = path.split('/').pop();
    console.log('[TreeContextMenu] Copying filename:', filename);
    
    try {
      navigator.clipboard.writeText(filename).then(() => {
        this.showNotification(`Copied: ${filename}`, 'success');
      });
    } catch (error) {
      this.showNotification(`Failed to copy: ${error.message}`, 'error');
    }
  }

  async showInFinder(path) {
    console.log('[TreeContextMenu] Show in Finder:', path);
    
    try {
      if (window.electron && window.electron.showInFinder) {
        await window.electron.showInFinder(path);
      } else {
        this.showNotification('Show in Finder not available', 'error');
      }
    } catch (error) {
      this.showNotification(`Failed to show in Finder: ${error.message}`, 'error');
    }
  }

  async showGitBlame(path) {
    console.log('[TreeContextMenu] Git blame:', path);
    
    try {
      // Trigger Flux command to show git blame
      if (window.flux && window.flux.sendCommand) {
        const tabId = window.tabManager?.getActiveTabId();
        if (tabId) {
          window.flux.sendCommand(tabId, `run git blame ${path}`);
          this.showNotification('Running git blame...', 'info');
        }
      }
    } catch (error) {
      this.showNotification(`Failed to run git blame: ${error.message}`, 'error');
    }
  }

  showDependencies(path) {
    console.log('[TreeContextMenu] Show dependencies:', path);
    
    // Highlight connected nodes (files this file imports)
    if (window.livingTree) {
      window.livingTree.highlightConnections(path);
      this.showNotification('Dependencies highlighted', 'info');
    }
  }

  showDependents(path) {
    console.log('[TreeContextMenu] Show dependents:', path);
    
    // Highlight nodes that depend on this file
    if (window.livingTree) {
      window.livingTree.highlightDependents(path);
      this.showNotification('Dependents highlighted', 'info');
    }
  }

  askFluxToEdit(path) {
    console.log('[TreeContextMenu] Ask Flux to edit:', path);
    
    // Pre-fill command input
    const commandInput = document.getElementById('command-input');
    if (commandInput) {
      const filename = path.split('/').pop();
      commandInput.value = `edit ${path} and `;
      commandInput.focus();
      // Move cursor to end
      commandInput.setSelectionRange(commandInput.value.length, commandInput.value.length);
    }
  }

  askFluxToRefactor(path) {
    console.log('[TreeContextMenu] Ask Flux to refactor:', path);
    
    // Pre-fill command input
    const commandInput = document.getElementById('command-input');
    if (commandInput) {
      commandInput.value = `refactor ${path} to `;
      commandInput.focus();
      commandInput.setSelectionRange(commandInput.value.length, commandInput.value.length);
    }
  }

  // Helper methods

  isGitRepo() {
    // Check if we're in a git repository
    // This could be cached or checked via IPC
    return true; // Assume yes for now
  }

  showNotification(message, type = 'info') {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `tree-toast tree-toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
      toast.classList.add('show');
    });

    // Remove after 3 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }, 3000);
  }
}

// Initialize context menu
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.treeContextMenu = new TreeContextMenu();
  });
} else {
  window.treeContextMenu = new TreeContextMenu();
}
