// Command Intelligence System
// Analyzes commands for safety, parses structure, and provides explanations

class CommandIntelligence {
  constructor() {
    // Dangerous command patterns with risk levels
    this.dangerPatterns = {
      critical: [
        { pattern: /rm\s+-rf\s+\/($|\s)/, reason: 'Deletes entire root filesystem', alternative: 'Specify exact directory: rm -rf /path/to/dir' },
        { pattern: /dd\s+if=\/dev\/zero\s+of=\/dev\//, reason: 'Overwrites disk with zeros', alternative: 'Use with extreme caution or consult documentation' },
        { pattern: /:()\s*{\s*:\|\s*:\s*&\s*}\s*;\s*:/, reason: 'Fork bomb - crashes system', alternative: 'Never run this command' },
        { pattern: /mkfs/, reason: 'Formats filesystem - destroys all data', alternative: 'Double-check device path' },
        { pattern: /dd\s+if=.*\s+of=\/dev\/(sd|hd|nvme)/, reason: 'Overwrites entire disk', alternative: 'Verify device path carefully' },
        { pattern: /chmod\s+-R\s+777\s+\//, reason: 'Makes entire system world-writable', alternative: 'chmod on specific files only' },
        { pattern: /chown\s+-R.*\s+\/($|\s)/, reason: 'Changes ownership of entire filesystem', alternative: 'Target specific directories' },
      ],
      high: [
        { pattern: /rm\s+-rf/, reason: 'Force-deletes files recursively without confirmation', alternative: 'Use trash-cli or rm -ri for confirmation' },
        { pattern: /sudo\s+rm/, reason: 'Deletes files with elevated privileges', alternative: 'Avoid sudo with rm when possible' },
        { pattern: />\s*\/dev\/(sd|hd|nvme)/, reason: 'Writes directly to disk device', alternative: 'Use proper tools for disk operations' },
        { pattern: /curl.*\|\s*(bash|sh|zsh)/, reason: 'Executes remote script without inspection', alternative: 'Download and review script first' },
        { pattern: /wget.*\|\s*(bash|sh|zsh)/, reason: 'Executes remote script without inspection', alternative: 'Download and review script first' },
        { pattern: /chmod\s+-R\s+777/, reason: 'Makes files world-writable recursively', alternative: 'Use specific permissions like 755 or 644' },
        { pattern: /chmod\s+777/, reason: 'Makes files world-writable', alternative: 'Use 755 for directories, 644 for files' },
        { pattern: /sudo\s+chmod/, reason: 'Changes permissions with elevated privileges', alternative: 'Verify you need sudo' },
      ],
      medium: [
        { pattern: /rm\s+-r/, reason: 'Deletes directories recursively', alternative: 'Use trash or rm -ri for confirmation' },
        { pattern: /sudo/, reason: 'Runs command with elevated privileges', alternative: 'Verify command is safe before using sudo' },
        { pattern: /npm\s+install\s+-g/, reason: 'Installs package globally', alternative: 'Install locally unless needed globally' },
        { pattern: /pip\s+install.*--upgrade/, reason: 'Upgrades packages (may break dependencies)', alternative: 'Test upgrades in virtual environment' },
        { pattern: /docker\s+system\s+prune/, reason: 'Deletes unused Docker resources', alternative: 'Use docker system prune -a to see what will be deleted' },
        { pattern: /git\s+push\s+(-f|--force)/, reason: 'Force-pushes (overwrites remote history)', alternative: 'Use --force-with-lease for safety' },
        { pattern: /git\s+reset\s+--hard/, reason: 'Discards all uncommitted changes', alternative: 'git stash to preserve changes' },
        { pattern: /git\s+clean\s+-fd/, reason: 'Deletes untracked files', alternative: 'git clean -fdn to preview first' },
        { pattern: /killall/, reason: 'Kills all processes with given name', alternative: 'kill specific process by PID' },
      ],
      low: [
        { pattern: /mv\s+.*\s+\//, reason: 'Moves files to root directory', alternative: 'Verify destination path' },
        { pattern: /cp\s+-r\s+.*\s+\//, reason: 'Copies files to root directory', alternative: 'Verify destination path' },
        { pattern: /npm\s+install\s+[^-]/, reason: 'Installs npm packages', alternative: 'Review package before installing' },
        { pattern: /brew\s+install/, reason: 'Installs software via Homebrew', alternative: 'Verify package name' },
      ]
    };
    
    // Common command typos
    this.commonTypos = {
      'gti': 'git',
      'gi': 'git',
      'got': 'git',
      'gut': 'git',
      'grp': 'grep',
      'gerp': 'grep',
      'cd..': 'cd ..',
      'cd...': 'cd ../..',
      'claer': 'clear',
      'clar': 'clear',
      'clera': 'clear',
      'suod': 'sudo',
      'sduo': 'sudo',
      'sl': 'ls',
      'ks': 'ls',
      'npm': 'npm',
      'npn': 'npm',
      'npx': 'npx',
      'pnpm': 'pnpm',
      'dokcer': 'docker',
      'dockerr': 'docker',
      'pytohn': 'python',
      'pyton': 'python',
      'tial': 'tail',
      'ehco': 'echo',
      'eho': 'echo'
    };
    
    // Safe commands that don't need explanation
    this.safeCommands = new Set([
      'ls', 'pwd', 'cd', 'cat', 'less', 'more', 'head', 'tail',
      'echo', 'date', 'whoami', 'which', 'whereis', 'man',
      'grep', 'find', 'wc', 'sort', 'uniq', 'diff',
      'git status', 'git log', 'git diff', 'git branch',
      'npm list', 'npm search', 'npm view',
      'docker ps', 'docker images', 'docker logs',
      'history', 'alias', 'env', 'printenv'
    ]);
    
    // Command explanation cache
    this.explanationCache = new Map();
  }
  
  /**
   * Analyze a command and return intelligence data
   * @param {string} command - The command to analyze
   * @returns {Object} Analysis result
   */
  analyzeCommand(command) {
    const trimmed = command.trim();
    
    // Check for typos
    const typoCorrection = this.detectTypo(trimmed);
    
    // Parse command structure
    const parsed = this.parseCommand(trimmed);
    
    // Classify risk level
    const risk = this.classifyRisk(trimmed);
    
    // Check if safe command
    const isSafe = this.isSafeCommand(trimmed);
    
    return {
      original: command,
      parsed,
      risk,
      isSafe,
      typoCorrection,
      needsConfirmation: !isSafe && risk.level !== 'safe',
      shouldBlock: risk.level === 'critical'
    };
  }
  
  /**
   * Parse command into structured parts
   * @param {string} command - The command string
   * @returns {Object} Parsed command structure
   */
  parseCommand(command) {
    const parts = command.trim().split(/\s+/);
    const baseCommand = parts[0] || '';
    const args = parts.slice(1);
    
    // Extract flags and arguments
    const flags = args.filter(arg => arg.startsWith('-'));
    const positionalArgs = args.filter(arg => !arg.startsWith('-'));
    
    // Detect pipes and redirects
    const hasPipe = command.includes('|');
    const hasRedirect = /[><]/.test(command);
    const hasSudo = command.startsWith('sudo');
    
    return {
      baseCommand,
      flags,
      positionalArgs,
      hasPipe,
      hasRedirect,
      hasSudo,
      fullCommand: command
    };
  }
  
  /**
   * Classify command risk level
   * @param {string} command - The command to classify
   * @returns {Object} Risk classification
   */
  classifyRisk(command) {
    // Check critical patterns first
    for (const pattern of this.dangerPatterns.critical) {
      if (pattern.pattern.test(command)) {
        return {
          level: 'critical',
          icon: '🛑',
          color: 'red',
          reason: pattern.reason,
          alternative: pattern.alternative,
          shouldBlock: true
        };
      }
    }
    
    // Check high risk patterns
    for (const pattern of this.dangerPatterns.high) {
      if (pattern.pattern.test(command)) {
        return {
          level: 'high',
          icon: '⚠️',
          color: 'orange',
          reason: pattern.reason,
          alternative: pattern.alternative,
          shouldBlock: false
        };
      }
    }
    
    // Check medium risk patterns
    for (const pattern of this.dangerPatterns.medium) {
      if (pattern.pattern.test(command)) {
        return {
          level: 'medium',
          icon: '🟡',
          color: 'yellow',
          reason: pattern.reason,
          alternative: pattern.alternative,
          shouldBlock: false
        };
      }
    }
    
    // Check low risk patterns
    for (const pattern of this.dangerPatterns.low) {
      if (pattern.pattern.test(command)) {
        return {
          level: 'low',
          icon: '💡',
          color: 'blue',
          reason: pattern.reason,
          alternative: pattern.alternative,
          shouldBlock: false
        };
      }
    }
    
    // Default: safe
    return {
      level: 'safe',
      icon: '✅',
      color: 'green',
      reason: 'Command appears safe',
      alternative: null,
      shouldBlock: false
    };
  }
  
  /**
   * Check if command is known to be safe
   * @param {string} command - The command to check
   * @returns {boolean} True if safe
   */
  isSafeCommand(command) {
    const normalized = command.trim().toLowerCase();
    
    // Check exact matches
    if (this.safeCommands.has(normalized)) {
      return true;
    }
    
    // Check if starts with safe command
    for (const safe of this.safeCommands) {
      if (normalized.startsWith(safe + ' ') || normalized === safe) {
        return true;
      }
    }
    
    return false;
  }
  
  /**
   * Detect typos and suggest corrections
   * @param {string} command - The command to check
   * @returns {Object|null} Correction suggestion or null
   */
  detectTypo(command) {
    const firstWord = command.trim().split(/\s+/)[0];
    
    if (this.commonTypos[firstWord]) {
      const corrected = command.replace(firstWord, this.commonTypos[firstWord]);
      return {
        typo: firstWord,
        correction: this.commonTypos[firstWord],
        correctedCommand: corrected,
        confidence: 'high'
      };
    }
    
    // Fuzzy matching for similar commands
    const similarCommand = this.findSimilarCommand(firstWord);
    if (similarCommand) {
      const corrected = command.replace(firstWord, similarCommand);
      return {
        typo: firstWord,
        correction: similarCommand,
        correctedCommand: corrected,
        confidence: 'medium'
      };
    }
    
    return null;
  }
  
  /**
   * Find similar command using fuzzy matching
   * @param {string} word - The word to match
   * @returns {string|null} Similar command or null
   */
  findSimilarCommand(word) {
    const commonCommands = [
      'git', 'npm', 'docker', 'python', 'node', 'grep', 'find',
      'ls', 'cd', 'rm', 'mv', 'cp', 'cat', 'echo', 'sudo',
      'brew', 'apt', 'yum', 'pip', 'cargo', 'go', 'make'
    ];
    
    let bestMatch = null;
    let bestDistance = Infinity;
    
    for (const cmd of commonCommands) {
      const distance = this.levenshteinDistance(word.toLowerCase(), cmd);
      if (distance <= 2 && distance < bestDistance) {
        bestDistance = distance;
        bestMatch = cmd;
      }
    }
    
    return bestMatch;
  }
  
  /**
   * Calculate Levenshtein distance between two strings
   * @param {string} a - First string
   * @param {string} b - Second string
   * @returns {number} Edit distance
   */
  levenshteinDistance(a, b) {
    const matrix = [];
    
    for (let i = 0; i <= b.length; i++) {
      matrix[i] = [i];
    }
    
    for (let j = 0; j <= a.length; j++) {
      matrix[0][j] = j;
    }
    
    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        if (b.charAt(i - 1) === a.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }
    
    return matrix[b.length][a.length];
  }
  
  /**
   * Get cached explanation or mark for generation
   * @param {string} command - The command
   * @returns {string|null} Cached explanation or null
   */
  getCachedExplanation(command) {
    return this.explanationCache.get(command) || null;
  }
  
  /**
   * Cache command explanation
   * @param {string} command - The command
   * @param {string} explanation - The explanation
   */
  cacheExplanation(command, explanation) {
    this.explanationCache.set(command, explanation);
    
    // Limit cache size
    if (this.explanationCache.size > 100) {
      const firstKey = this.explanationCache.keys().next().value;
      this.explanationCache.delete(firstKey);
    }
  }
}

// Initialize and export
if (typeof window !== 'undefined') {
  window.CommandIntelligence = CommandIntelligence;
  window.commandIntelligence = new CommandIntelligence();
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CommandIntelligence;
}
