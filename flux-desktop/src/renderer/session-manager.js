// Session Manager - Persists and restores terminal sessions
class SessionManager {
  constructor() {
    this.storageKey = 'flux-terminal-sessions';
    this.autoSaveInterval = null;
    this.saveDebounceTimer = null;
  }

  // Initialize session manager
  init(tabManager) {
    this.tabManager = tabManager;
    
    // Start auto-save every 30 seconds
    this.startAutoSave();
    
    // Save on window unload
    window.addEventListener('beforeunload', () => {
      this.saveSession();
    });
    
    // Restore previous session
    this.restoreSession();
  }

  // Start auto-save with debouncing
  startAutoSave() {
    this.autoSaveInterval = setInterval(() => {
      this.saveSession();
    }, 30000); // Save every 30 seconds
  }

  // Save current session to localStorage
  saveSession() {
    try {
      const session = {
        version: '1.0',
        timestamp: Date.now(),
        activeTabId: this.tabManager.activeTabId,
        tabs: []
      };

      // Save each tab's state
      this.tabManager.getAllTabs().forEach(tab => {
        const terminals = window.terminals || new Map();
        const terminalData = terminals.get(tab.id);
        
        const tabState = {
          id: tab.id,
          label: tab.label,
          cwd: tab.cwd,
          history: terminalData ? terminalData.state.commandHistory : [],
          // Note: We don't save terminal buffer content as it can be very large
          // and may contain sensitive data. Users will see clean terminals on restart.
        };
        
        session.tabs.push(tabState);
      });

      localStorage.setItem(this.storageKey, JSON.stringify(session));
      console.log('Session saved:', session.tabs.length, 'tabs');
    } catch (error) {
      console.error('Failed to save session:', error);
    }
  }

  // Restore session from localStorage
  restoreSession() {
    try {
      const savedSession = localStorage.getItem(this.storageKey);
      
      if (!savedSession) {
        console.log('No previous session found');
        return false;
      }

      const session = JSON.parse(savedSession);
      
      // Check if session is too old (> 7 days)
      const sessionAge = Date.now() - session.timestamp;
      const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
      
      if (sessionAge > maxAge) {
        console.log('Session too old, starting fresh');
        localStorage.removeItem(this.storageKey);
        return false;
      }

      console.log('Restoring session from', new Date(session.timestamp).toLocaleString());
      
      // Close the default tab that was created
      if (this.tabManager.tabs.size === 1) {
        const defaultTab = Array.from(this.tabManager.tabs.keys())[0];
        this.tabManager.closeTab(defaultTab);
      }

      // Restore tabs
      let restoredActiveTab = null;
      session.tabs.forEach((tabState, index) => {
        const newTabId = this.tabManager.createTab(tabState.label, tabState.cwd);
        
        // Restore command history
        if (tabState.history && tabState.history.length > 0) {
          setTimeout(() => {
            const terminals = window.terminals || new Map();
            const terminalData = terminals.get(newTabId);
            if (terminalData) {
              terminalData.state.commandHistory = [...tabState.history];
              
              // Update history UI if this is the active tab
              if (newTabId === this.tabManager.activeTabId) {
                if (window.updateHistoryUI) {
                  window.updateHistoryUI();
                }
              }
            }
          }, 100 * (index + 1)); // Stagger to allow terminal initialization
        }
        
        // Track which tab should be active
        if (tabState.id === session.activeTabId) {
          restoredActiveTab = newTabId;
        }
      });

      // Switch to the previously active tab
      if (restoredActiveTab) {
        setTimeout(() => {
          this.tabManager.switchTab(restoredActiveTab);
        }, 200);
      }

      return true;
    } catch (error) {
      console.error('Failed to restore session:', error);
      localStorage.removeItem(this.storageKey);
      return false;
    }
  }

  // Clear saved session
  clearSession() {
    try {
      localStorage.removeItem(this.storageKey);
      console.log('Session cleared');
    } catch (error) {
      console.error('Failed to clear session:', error);
    }
  }

  // Debounced save for frequent changes
  scheduleSave() {
    if (this.saveDebounceTimer) {
      clearTimeout(this.saveDebounceTimer);
    }
    
    this.saveDebounceTimer = setTimeout(() => {
      this.saveSession();
    }, 2000); // Save 2 seconds after last change
  }

  // Export session to file
  exportSession() {
    try {
      const session = localStorage.getItem(this.storageKey);
      if (!session) {
        console.log('No session to export');
        return null;
      }

      const blob = new Blob([session], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `flux-session-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      console.log('Session exported');
    } catch (error) {
      console.error('Failed to export session:', error);
    }
  }

  // Import session from file
  async importSession(file) {
    try {
      const text = await file.text();
      const session = JSON.parse(text);
      
      // Validate session structure
      if (!session.tabs || !Array.isArray(session.tabs)) {
        throw new Error('Invalid session file format');
      }

      // Save imported session
      localStorage.setItem(this.storageKey, text);
      console.log('Session imported');
      
      // Reload to apply
      window.location.reload();
    } catch (error) {
      console.error('Failed to import session:', error);
      alert('Failed to import session: ' + error.message);
    }
  }

  // Get session info
  getSessionInfo() {
    try {
      const savedSession = localStorage.getItem(this.storageKey);
      if (!savedSession) {
        return null;
      }

      const session = JSON.parse(savedSession);
      return {
        timestamp: new Date(session.timestamp).toLocaleString(),
        tabCount: session.tabs.length,
        age: Math.floor((Date.now() - session.timestamp) / 1000 / 60), // minutes
        size: new Blob([savedSession]).size
      };
    } catch (error) {
      console.error('Failed to get session info:', error);
      return null;
    }
  }

  // Cleanup
  destroy() {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
    }
    if (this.saveDebounceTimer) {
      clearTimeout(this.saveDebounceTimer);
    }
    this.saveSession(); // Final save before cleanup
  }
}

// Export for use in renderer.js
window.SessionManager = SessionManager;
