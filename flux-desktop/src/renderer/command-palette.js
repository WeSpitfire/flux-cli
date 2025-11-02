// Command Palette Component
// Handles Cmd+K universal search for commands, files, history, and Flux commands

class CommandPalette {
  constructor() {
    this.isOpen = false;
    this.searchResults = [];
    this.selectedIndex = 0;
    this.searchQuery = '';
    
    // Data sources
    this.commandHistory = [];
    this.fluxCommands = [
      { type: 'flux', name: '/commit', description: 'Smart commit with AI-generated message', icon: '🔧' },
      { type: 'flux', name: '/diff', description: 'Show git diff with explanation', icon: '📊' },
      { type: 'flux', name: '/test', description: 'Run tests with AI analysis', icon: '🧪' },
      { type: 'flux', name: '/fix', description: 'Fix errors in code', icon: '🔨' },
      { type: 'flux', name: '/explain', description: 'Explain code or command', icon: '💡' },
      { type: 'flux', name: '/refactor', description: 'Refactor code with AI', icon: '✨' },
      { type: 'flux', name: '/docs', description: 'Generate documentation', icon: '📝' },
      { type: 'flux', name: '/review', description: 'Code review with suggestions', icon: '👀' }
    ];
    
    this.init();
  }
  
  init() {
    this.createElements();
    this.attachEventListeners();
  }
  
  createElements() {
    // Create overlay
    this.overlay = document.createElement('div');
    this.overlay.className = 'command-palette-overlay';
    this.overlay.style.display = 'none';
    
    // Create modal
    this.modal = document.createElement('div');
    this.modal.className = 'command-palette-modal';
    
    // Create search input
    this.searchInput = document.createElement('input');
    this.searchInput.type = 'text';
    this.searchInput.className = 'command-palette-input';
    this.searchInput.placeholder = '🔍 Search commands, files, history...';
    this.searchInput.autocomplete = 'off';
    this.searchInput.spellcheck = false;
    
    // Create results container
    this.resultsContainer = document.createElement('div');
    this.resultsContainer.className = 'command-palette-results';
    
    // Create hint text
    this.hintText = document.createElement('div');
    this.hintText.className = 'command-palette-hint';
    this.hintText.innerHTML = '<kbd>↑</kbd><kbd>↓</kbd> navigate • <kbd>Enter</kbd> select • <kbd>Esc</kbd> close';
    
    // Assemble
    this.modal.appendChild(this.searchInput);
    this.modal.appendChild(this.resultsContainer);
    this.modal.appendChild(this.hintText);
    this.overlay.appendChild(this.modal);
    document.body.appendChild(this.overlay);
  }
  
  attachEventListeners() {
    // Global keyboard shortcut (Cmd+K / Ctrl+K)
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        // Only open if not already typing in command input and not already open
        const commandInput = document.getElementById('command-input');
        if (document.activeElement !== commandInput && !this.isOpen) {
          e.preventDefault();
          this.open();
        }
      }
    });
    
    // Overlay click to close
    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) {
        this.close();
      }
    });
    
    // Search input events
    this.searchInput.addEventListener('input', () => {
      this.handleSearch();
    });
    
    this.searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        this.close();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.selectNext();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.selectPrevious();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        this.executeSelected();
      }
    });
    
    // Results container click handling
    this.resultsContainer.addEventListener('click', (e) => {
      const resultItem = e.target.closest('.command-palette-item');
      if (resultItem) {
        const index = parseInt(resultItem.dataset.index);
        this.selectedIndex = index;
        this.executeSelected();
      }
    });
  }
  
  open() {
    this.isOpen = true;
    this.overlay.style.display = 'flex';
    this.searchInput.value = '';
    this.searchQuery = '';
    this.selectedIndex = 0;
    
    // Show default results (recent commands + Flux commands)
    this.showDefaultResults();
    
    // Focus input
    setTimeout(() => this.searchInput.focus(), 50);
    
    // Animation
    this.modal.style.animation = 'slideDown 0.2s ease-out';
  }
  
  close() {
    this.isOpen = false;
    this.modal.style.animation = 'slideUp 0.15s ease-in';
    setTimeout(() => {
      this.overlay.style.display = 'none';
    }, 150);
  }
  
  showDefaultResults() {
    // Get recent commands from state
    const state = window.fluxState || { commandHistory: [] };
    const recentCommands = state.commandHistory.slice(0, 5).map((item, i) => ({
      type: 'history',
      name: item.command,
      description: `Recent command (${item.timestamp})`,
      icon: '📝',
      index: i
    }));
    
    // Combine with Flux commands
    this.searchResults = [...recentCommands, ...this.fluxCommands];
    this.renderResults();
  }
  
  handleSearch() {
    this.searchQuery = this.searchInput.value.trim().toLowerCase();
    this.selectedIndex = 0;
    
    if (this.searchQuery === '') {
      this.showDefaultResults();
      return;
    }
    
    // Fuzzy search across all sources
    this.searchResults = this.fuzzySearch(this.searchQuery);
    this.renderResults();
  }
  
  fuzzySearch(query) {
    const results = [];
    
    // Search Flux commands
    this.fluxCommands.forEach(cmd => {
      const score = this.calculateFuzzyScore(query, cmd.name + ' ' + cmd.description);
      if (score > 0) {
        results.push({ ...cmd, score });
      }
    });
    
    // Search command history
    const state = window.fluxState || { commandHistory: [] };
    state.commandHistory.forEach((item, i) => {
      const score = this.calculateFuzzyScore(query, item.command);
      if (score > 0) {
        results.push({
          type: 'history',
          name: item.command,
          description: `Recent command (${item.timestamp})`,
          icon: '📝',
          index: i,
          score
        });
      }
    });
    
    // TODO: Search files (will implement in Day 4)
    
    // Sort by score
    results.sort((a, b) => b.score - a.score);
    
    return results;
  }
  
  calculateFuzzyScore(query, text) {
    text = text.toLowerCase();
    query = query.toLowerCase();
    
    // Exact match = highest score
    if (text.includes(query)) {
      return 100;
    }
    
    // Fuzzy matching - all query characters must appear in order
    let queryIndex = 0;
    let textIndex = 0;
    let score = 0;
    
    while (textIndex < text.length && queryIndex < query.length) {
      if (text[textIndex] === query[queryIndex]) {
        score += 10;
        queryIndex++;
      }
      textIndex++;
    }
    
    // Did we match all query characters?
    if (queryIndex === query.length) {
      return score;
    }
    
    return 0;
  }
  
  renderResults() {
    if (this.searchResults.length === 0) {
      this.resultsContainer.innerHTML = `
        <div class="command-palette-empty">
          <div class="empty-icon">🔍</div>
          <div class="empty-text">No results found</div>
          <div class="empty-hint">Try a different search term</div>
        </div>
      `;
      return;
    }
    
    this.resultsContainer.innerHTML = this.searchResults.map((result, index) => {
      const isSelected = index === this.selectedIndex;
      return `
        <div class="command-palette-item ${isSelected ? 'selected' : ''}" data-index="${index}">
          <div class="item-icon">${result.icon}</div>
          <div class="item-content">
            <div class="item-name">${this.highlightMatch(result.name, this.searchQuery)}</div>
            <div class="item-description">${result.description}</div>
          </div>
          <div class="item-type">${this.getTypeLabel(result.type)}</div>
        </div>
      `;
    }).join('');
  }
  
  highlightMatch(text, query) {
    if (!query) return this.escapeHtml(text);
    
    const escaped = this.escapeHtml(text);
    const index = escaped.toLowerCase().indexOf(query.toLowerCase());
    
    if (index === -1) return escaped;
    
    const before = escaped.substring(0, index);
    const match = escaped.substring(index, index + query.length);
    const after = escaped.substring(index + query.length);
    
    return `${before}<mark>${match}</mark>${after}`;
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  getTypeLabel(type) {
    const labels = {
      'flux': 'Command',
      'history': 'History',
      'file': 'File'
    };
    return labels[type] || type;
  }
  
  selectNext() {
    if (this.searchResults.length === 0) return;
    this.selectedIndex = (this.selectedIndex + 1) % this.searchResults.length;
    this.renderResults();
    this.scrollToSelected();
  }
  
  selectPrevious() {
    if (this.searchResults.length === 0) return;
    this.selectedIndex = this.selectedIndex === 0 
      ? this.searchResults.length - 1 
      : this.selectedIndex - 1;
    this.renderResults();
    this.scrollToSelected();
  }
  
  scrollToSelected() {
    const selectedElement = this.resultsContainer.querySelector('.command-palette-item.selected');
    if (selectedElement) {
      selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }
  
  executeSelected() {
    if (this.searchResults.length === 0) return;
    
    const selected = this.searchResults[this.selectedIndex];
    
    if (!selected) return;
    
    this.close();
    
    // Execute based on type
    if (selected.type === 'flux') {
      // Insert Flux command into input
      const commandInput = document.getElementById('command-input');
      if (commandInput) {
        commandInput.value = selected.name + ' ';
        commandInput.focus();
        // Trigger input event to auto-grow
        commandInput.dispatchEvent(new Event('input'));
      }
    } else if (selected.type === 'history') {
      // Insert historical command into input
      const commandInput = document.getElementById('command-input');
      if (commandInput) {
        commandInput.value = selected.name;
        commandInput.focus();
        commandInput.dispatchEvent(new Event('input'));
      }
    } else if (selected.type === 'file') {
      // TODO: Open file (Day 4)
      console.log('Open file:', selected.name);
    }
  }
  
  // Update command history (called from main app)
  updateHistory(history) {
    this.commandHistory = history;
  }
}

// Initialize command palette when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.commandPalette = new CommandPalette();
  });
} else {
  window.commandPalette = new CommandPalette();
}
