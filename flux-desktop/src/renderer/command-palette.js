// Command Palette Component
// Handles Cmd+K universal search for commands, files, history, and Flux commands

class CommandPalette {
  constructor() {
    this.isOpen = false;
    this.searchResults = [];
    this.selectedIndex = 0;
    this.searchQuery = '';
    this.isLoading = false;
    this.searchDebounceTimer = null;
    
    // Data sources
    this.commandHistory = [];
    this.commandFrequency = this.loadFrequency();
    this.workingDirectory = null;
    this.fileCache = [];
    this.fileCacheTime = 0;
    
    // Get working directory
    this.initWorkingDirectory();
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
  
  async initWorkingDirectory() {
    try {
      this.workingDirectory = await window.fileSystem.getCwd();
    } catch (e) {
      console.error('Failed to get working directory:', e);
    }
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
    
    // Search input events with debouncing
    this.searchInput.addEventListener('input', () => {
      // Clear existing timer
      if (this.searchDebounceTimer) {
        clearTimeout(this.searchDebounceTimer);
      }
      
      // Debounce search by 150ms
      this.searchDebounceTimer = setTimeout(() => {
        this.handleSearch();
      }, 150);
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
    
    // Get top 10 most frequent commands, but prioritize recent ones
    const commandsWithFreq = state.commandHistory.map((item, i) => {
      const frequency = this.commandFrequency[item.command] || 1;
      const recencyScore = Math.max(10 - i, 1); // Recent = higher score
      const totalScore = frequency * 2 + recencyScore; // Frequency weighted more
      
      return {
        type: 'history',
        name: item.command,
        description: this.formatHistoryDescription(item, frequency),
        icon: this.getFrequencyIcon(frequency),
        index: i,
        frequency,
        recencyScore,
        totalScore
      };
    });
    
    // Sort by total score (frequency + recency) and take top 8
    const topCommands = commandsWithFreq
      .sort((a, b) => b.totalScore - a.totalScore)
      .slice(0, 8);
    
    // Combine with Flux commands
    this.searchResults = [...topCommands, ...this.fluxCommands];
    this.renderResults();
  }
  
  async handleSearch() {
    this.searchQuery = this.searchInput.value.trim().toLowerCase();
    this.selectedIndex = 0;
    
    if (this.searchQuery === '') {
      this.showDefaultResults();
      return;
    }
    
    // Show loading state
    this.isLoading = true;
    this.renderLoading();
    
    try {
      // Fuzzy search across all sources (now async)
      this.searchResults = await this.fuzzySearch(this.searchQuery);
      this.isLoading = false;
      this.renderResults();
    } catch (e) {
      console.error('Search error:', e);
      this.isLoading = false;
      this.renderResults();
    }
  }
  
  async fuzzySearch(query) {
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
        const frequency = this.commandFrequency[item.command] || 1;
        const boostedScore = score + (frequency * 2); // Boost by frequency
        
        results.push({
          type: 'history',
          name: item.command,
          description: this.formatHistoryDescription(item, frequency),
          icon: this.getFrequencyIcon(frequency),
          index: i,
          frequency,
          score: boostedScore
        });
      }
    });
    
    // Search files
    if (this.workingDirectory && query.length >= 2) {
      const fileResults = await this.searchFiles(query);
      results.push(...fileResults);
    }
    
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
  
  renderLoading() {
    this.resultsContainer.innerHTML = `
      <div class="command-palette-loading">
        <div class="loading-spinner"></div>
        <div class="loading-text">Searching...</div>
      </div>
    `;
  }
  
  renderResults() {
    if (this.isLoading) return; // Don't render if still loading
    
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
      const typeLabel = result.subtype ? this.getTypeLabel(result.subtype) : this.getTypeLabel(result.type);
      return `
        <div class="command-palette-item ${isSelected ? 'selected' : ''}" data-index="${index}">
          <div class="item-icon">${result.icon}</div>
          <div class="item-content">
            <div class="item-name">${this.highlightMatch(result.name, this.searchQuery)}</div>
            <div class="item-description">${result.description}</div>
          </div>
          <div class="item-type">${typeLabel}</div>
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
      'file': 'File',
      'javascript': 'JS',
      'typescript': 'TS',
      'python': 'PY',
      'stylesheet': 'CSS',
      'markdown': 'MD',
      'json': 'JSON',
      'html': 'HTML',
      'config': 'CFG'
    };
    return labels[type] || type.toUpperCase();
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
      // Track frequency
      this.incrementFrequency(selected.name);
      
      // Insert historical command into input
      const commandInput = document.getElementById('command-input');
      if (commandInput) {
        commandInput.value = selected.name;
        commandInput.focus();
        commandInput.dispatchEvent(new Event('input'));
      }
    } else if (selected.type === 'file') {
      // Insert command to open file
      const commandInput = document.getElementById('command-input');
      if (commandInput) {
        commandInput.value = `Open ${selected.path}`;
        commandInput.focus();
        commandInput.dispatchEvent(new Event('input'));
      }
    }
  }
  
  // Update command history (called from main app)
  updateHistory(history) {
    this.commandHistory = history;
  }
  
  // Frequency tracking helpers
  loadFrequency() {
    try {
      const stored = localStorage.getItem('flux-command-frequency');
      return stored ? JSON.parse(stored) : {};
    } catch (e) {
      return {};
    }
  }
  
  saveFrequency() {
    try {
      localStorage.setItem('flux-command-frequency', JSON.stringify(this.commandFrequency));
    } catch (e) {
      console.error('Failed to save frequency data:', e);
    }
  }
  
  incrementFrequency(command) {
    this.commandFrequency[command] = (this.commandFrequency[command] || 0) + 1;
    this.saveFrequency();
  }
  
  getFrequencyIcon(frequency) {
    if (frequency >= 10) return '⭐'; // Very frequent
    if (frequency >= 5) return '🔥'; // Frequent
    if (frequency >= 3) return '📌'; // Somewhat frequent
    return '📝'; // Normal
  }
  
  formatHistoryDescription(item, frequency) {
    const timeAgo = this.getRelativeTime(item.timestamp);
    const freqText = frequency > 1 ? ` • Used ${frequency}x` : '';
    return `${timeAgo}${freqText}`;
  }
  
  getRelativeTime(timestamp) {
    // If timestamp is already a date string like "3:45 PM", parse it
    // Otherwise assume it's a Date object or string
    const now = new Date();
    let date;
    
    try {
      // Try to parse as time string (e.g., "3:45 PM")
      const timeMatch = timestamp.match(/(\d+):(\d+)\s*(AM|PM)/i);
      if (timeMatch) {
        date = new Date();
        let hours = parseInt(timeMatch[1]);
        const minutes = parseInt(timeMatch[2]);
        const meridiem = timeMatch[3].toUpperCase();
        
        if (meridiem === 'PM' && hours !== 12) hours += 12;
        if (meridiem === 'AM' && hours === 12) hours = 0;
        
        date.setHours(hours, minutes, 0, 0);
        
        // If time is in the future, assume it was yesterday
        if (date > now) {
          date.setDate(date.getDate() - 1);
        }
      } else {
        date = new Date(timestamp);
      }
    } catch (e) {
      return timestamp; // Fallback to original
    }
    
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 120) return '1 min ago';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 7200) return '1 hour ago';
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    if (seconds < 172800) return 'Yesterday';
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
    
    return date.toLocaleDateString();
  }
  
  async searchFiles(query) {
    if (!this.workingDirectory) return [];
    
    try {
      const files = await window.fileSystem.searchFiles(this.workingDirectory, query, 20);
      
      return files.map(file => {
        const score = this.calculateFuzzyScore(query, file.name);
        return {
          type: 'file',
          subtype: file.type,
          name: file.name,
          path: file.path,
          fullPath: file.fullPath,
          description: file.path,
          icon: this.getFileIcon(file.type),
          score: score * 0.8 // Slightly lower priority than commands
        };
      });
    } catch (e) {
      console.error('File search error:', e);
      return [];
    }
  }
  
  getFileIcon(fileType) {
    const icons = {
      'javascript': '🟡',
      'typescript': '🔵',
      'python': '🐍',
      'java': '☕',
      'c': '🆒',
      'cpp': '🆒',
      'stylesheet': '🎨',
      'html': '🌐',
      'json': '📊',
      'markdown': '📖',
      'text': '📄',
      'config': '⚙️',
      'image': '🖼️',
      'file': '📄'
    };
    return icons[fileType] || '📄';
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
