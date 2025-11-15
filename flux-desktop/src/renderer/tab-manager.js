// Tab Manager - Manages multiple terminal tabs
class TabManager {
  constructor() {
    this.tabs = new Map();
    this.activeTabId = null;
    this.nextTabId = 1;
    
    this.elements = {
      tabList: document.getElementById('tab-list'),
      newTabBtn: document.getElementById('new-tab-btn'),
      terminalContainer: document.getElementById('terminal-container')
    };
    
    this.init();
  }

  async init() {
    // Setup event listeners
    if (this.elements.newTabBtn) {
      this.elements.newTabBtn.addEventListener('click', () => this.createTab());
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => this.handleKeyboard(e));

    // Get the actual project root from main process
    let projectRoot;
    try {
      projectRoot = await window.fileSystem.getCwd();
      // Go up one level from flux-desktop to flux-cli
      projectRoot = await window.fileSystem.joinPath(projectRoot, '..');
    } catch (err) {
      console.error('Failed to get cwd:', err);
      projectRoot = null;
    }

    // Create initial tab with absolute path
    this.createTab('flux-cli', projectRoot);
  }

  createTab(label = null, cwd = null) {
    // Use the current working directory or a placeholder as the label
    const dynamicLabel = cwd ? `Terminal - ${cwd.split('/').pop()}` : 'Terminal';
    const tabId = `tab-${this.nextTabId++}`;
    const defaultLabel = label || dynamicLabel;
    const defaultCwd = cwd || null; // null will use projectRoot in main process

    // Create tab data
    const tabData = {
      id: tabId,
      label: defaultLabel,
      cwd: defaultCwd,
      terminal: null,
      terminalElement: null,
      history: [],
      isProcessing: false
    };

    // Create tab UI element
    const tabElement = this.createTabElement(tabData);
    this.elements.tabList.appendChild(tabElement);

    // Create terminal container
    const terminalWrapper = document.createElement('div');
    terminalWrapper.className = 'terminal-instance';
    terminalWrapper.id = `terminal-${tabId}`;
    terminalWrapper.style.display = 'none';
    this.elements.terminalContainer.appendChild(terminalWrapper);

    // Store tab data
    tabData.element = tabElement;
    tabData.terminalElement = terminalWrapper;
    this.tabs.set(tabId, tabData);

    // Switch to new tab
    this.switchTab(tabId);
    
    // Trigger session save
    if (window.sessionManager) {
      window.sessionManager.scheduleSave();
    }

    return tabId;
  }

  createTabElement(tabData) {
    const tab = document.createElement('button');
    tab.className = 'tab-item';
    tab.dataset.tabId = tabData.id;

    tab.innerHTML = `
      <span class="tab-icon">⚡</span>
      <span class="tab-label" contenteditable="true">${this.escapeHtml(tabData.label)}</span>
      <span class="tab-close" data-action="close">
        <svg viewBox="0 0 16 16" fill="none">
          <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </span>
    `;

    // Tab click handler
    tab.querySelector('.tab-label').addEventListener('dblclick', (e) => {
  e.target.focus();
  e.stopPropagation();
});

tab.querySelector('.tab-label').addEventListener('focus', (e) => {
  console.log('Tab label focused for editing:', tabData.id);
});
tab.querySelector('.tab-label').addEventListener('blur', (e) => {
  console.log('Tab label blur event:', tabData.id);
      if (e.target.isContentEditable) {
        const newLabel = e.target.textContent.replace(/^\s+|\s+$/g, '');
        if (newLabel) {
          this.updateTabLabel(tabData.id, newLabel);
        } else {
          e.target.textContent = tabData.label; // Revert to old label if empty
        }
      }
    });

    tab.addEventListener('click', (e) => {
  if (e.target.classList.contains('tab-label')) {
    // Prevent tab switch if clicking on the label
    e.target.focus();
    e.stopPropagation();
    return;
  }
      if (e.target.closest('.tab-close')) {
        this.closeTab(tabData.id);
      } else {
        this.switchTab(tabData.id);
      }
    });

    return tab;
  }

  switchTab(tabId) {
    if (!this.tabs.has(tabId)) return;

    // Deactivate current tab
    if (this.activeTabId) {
      const currentTab = this.tabs.get(this.activeTabId);
      if (currentTab) {
        currentTab.element.classList.remove('active');
        if (currentTab.terminalElement) {
          currentTab.terminalElement.style.display = 'none';
        }
      }
    }

    // Activate new tab
    const newTab = this.tabs.get(tabId);
    newTab.element.classList.add('active');
    if (newTab.terminalElement) {
      newTab.terminalElement.style.display = 'block';
    }

    this.activeTabId = tabId;

    // Initialize terminal for this tab if not yet created
    if (!newTab.terminal && window.initializeTerminalForTab) {
      window.initializeTerminalForTab(tabId, newTab.terminalElement);
    } else if (newTab.terminal) {
      // Fit the terminal when switching to it
      const terminalData = window.terminals ? window.terminals.get(tabId) : null;
      if (terminalData && terminalData.fitAddon) {
        setTimeout(() => {
          terminalData.fitAddon.fit();
        }, 10);
      }
    }

    // Update history UI for new active tab
    if (window.updateHistoryUI) {
      window.updateHistoryUI();
    }
    
    // Focus on command input
    const commandInput = document.getElementById('command-input');
    if (commandInput) {
      commandInput.focus();
    }

    // Notify listeners that tab changed
    this.onTabChange(tabId);
  }

  closeTab(tabId) {
    if (this.tabs.size <= 1) {
      console.log('Cannot close the last tab');
      return;
    }

    const tab = this.tabs.get(tabId);
    if (!tab) return;

    // Cleanup flux process
    if (window.flux && window.flux.destroyProcess) {
      window.flux.destroyProcess(tabId);
    }
    
    // Cleanup terminal
    if (tab.terminal) {
      tab.terminal.dispose();
    }

    // Remove DOM elements
    if (tab.element) {
      tab.element.remove();
    }
    if (tab.terminalElement) {
      tab.terminalElement.remove();
    }

    // Remove from tabs map
    this.tabs.delete(tabId);

    // If we closed the active tab, switch to another
    if (this.activeTabId === tabId) {
      const remainingTabs = Array.from(this.tabs.keys());
      if (remainingTabs.length > 0) {
        this.switchTab(remainingTabs[remainingTabs.length - 1]);
      }
    }
    
    // Trigger session save
    if (window.sessionManager) {
      window.sessionManager.scheduleSave();
    }
  }

  updateTabLabel(tabId, label) {
    const tab = this.tabs.get(tabId);
    if (!tab) return;

    tab.label = label;
    const labelEl = tab.element.querySelector('.tab-label');
    if (labelEl) {
      labelEl.textContent = this.escapeHtml(label);
    }
    
    // Trigger session save
    if (window.sessionManager) {
      window.sessionManager.scheduleSave();
    }
  }

  getActiveTab() {
    return this.tabs.get(this.activeTabId);
  }

  getAllTabs() {
    return Array.from(this.tabs.values());
  }

  handleKeyboard(e) {
    // Cmd/Ctrl + T: New tab
    if ((e.metaKey || e.ctrlKey) && e.key === 't') {
      e.preventDefault();
      this.createTab();
    }

    // Cmd/Ctrl + W: Close tab
    if ((e.metaKey || e.ctrlKey) && e.key === 'w') {
      e.preventDefault();
      if (this.activeTabId) {
        this.closeTab(this.activeTabId);
      }
    }

    // Cmd/Ctrl + 1-9: Switch to tab by number
    if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '9') {
      e.preventDefault();
      const tabIndex = parseInt(e.key) - 1;
      const tabIds = Array.from(this.tabs.keys());
      if (tabIndex < tabIds.length) {
        this.switchTab(tabIds[tabIndex]);
      }
    }

    // Cmd/Ctrl + Tab: Next tab
    if ((e.metaKey || e.ctrlKey) && e.key === 'Tab') {
      e.preventDefault();
      const tabIds = Array.from(this.tabs.keys());
      const currentIndex = tabIds.indexOf(this.activeTabId);
      const nextIndex = (currentIndex + 1) % tabIds.length;
      this.switchTab(tabIds[nextIndex]);
    }
  }

  onTabChange(tabId) {
    // Hook for when tab changes
    // Can be used to update UI, load tab-specific data, etc.
    const tab = this.tabs.get(tabId);
    if (tab) {
      console.log('Switched to tab:', tab.label);
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Export for use in renderer.js
window.TabManager = TabManager;
