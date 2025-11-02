/**
 * Terminal Output Formatter
 * Parses and formats terminal output with markdown, code blocks, and syntax highlighting
 */

class TerminalFormatter {
  constructor() {
    // ANSI color codes for terminal
    this.colors = {
      reset: '\x1b[0m',
      bold: '\x1b[1m',
      dim: '\x1b[2m',
      italic: '\x1b[3m',
      underline: '\x1b[4m',
      
      // Standard colors
      black: '\x1b[30m',
      red: '\x1b[31m',
      green: '\x1b[32m',
      yellow: '\x1b[33m',
      blue: '\x1b[34m',
      magenta: '\x1b[35m',
      cyan: '\x1b[36m',
      white: '\x1b[37m',
      
      // Bright colors
      brightBlack: '\x1b[90m',
      brightRed: '\x1b[91m',
      brightGreen: '\x1b[92m',
      brightYellow: '\x1b[93m',
      brightBlue: '\x1b[94m',
      brightMagenta: '\x1b[95m',
      brightCyan: '\x1b[96m',
      brightWhite: '\x1b[97m',
      
      // 256-color support
      color256: (n) => `\x1b[38;5;${n}m`,
      
      // Syntax highlighting colors
      keyword: '\x1b[38;5;141m',      // Purple
      string: '\x1b[38;5;114m',       // Green
      number: '\x1b[38;5;173m',       // Orange
      comment: '\x1b[38;5;245m',      // Gray
      function: '\x1b[38;5;111m',     // Blue
      operator: '\x1b[38;5;147m',     // Light purple
    };
  }

  /**
   * Format output with markdown and code highlighting
   */
  formatOutput(text) {
    // Check if text contains code blocks
    if (this.hasCodeBlock(text)) {
      return this.formatCodeBlocks(text);
    }
    
    // Format inline markdown
    return this.formatMarkdown(text);
  }

  /**
   * Check if text contains code blocks
   */
  hasCodeBlock(text) {
    return /```[\s\S]*?```/.test(text);
  }

  /**
   * Format code blocks with syntax highlighting
   */
  formatCodeBlocks(text) {
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    
    return text.replace(codeBlockRegex, (match, language, code) => {
      const lang = language || 'text';
      return this.renderCodeBlock(code.trim(), lang);
    });
  }

  /**
   * Render a code block with box and syntax highlighting
   */
  renderCodeBlock(code, language) {
    const width = 60; // Fixed width for code blocks
    const langLabel = language.toUpperCase();
    
    // Header
    const header = `\n${this.colors.color256(110)}╭─ ${this.colors.bold}${langLabel}${this.colors.reset}${this.colors.color256(110)} ${'─'.repeat(width - langLabel.length - 4)}╮${this.colors.reset}\n`;
    
    // Syntax highlight the code
    const highlightedCode = this.highlightCode(code, language);
    
    // Add each line with box borders
    const lines = highlightedCode.split('\n');
    const body = lines.map(line => {
      const paddedLine = line + ' '.repeat(Math.max(0, width - this.getVisibleLength(line)));
      return `${this.colors.color256(110)}│${this.colors.reset} ${paddedLine} ${this.colors.color256(110)}│${this.colors.reset}`;
    }).join('\n');
    
    // Footer
    const footer = `${this.colors.color256(110)}╰${'─'.repeat(width + 2)}╯${this.colors.reset}\n`;
    
    return header + body + '\n' + footer;
  }

  /**
   * Get visible length of string (ignoring ANSI codes)
   */
  getVisibleLength(str) {
    return str.replace(/\x1b\[[0-9;]*m/g, '').length;
  }

  /**
   * Syntax highlight code based on language
   */
  highlightCode(code, language) {
    switch (language.toLowerCase()) {
      case 'javascript':
      case 'js':
      case 'typescript':
      case 'ts':
        return this.highlightJavaScript(code);
      case 'python':
      case 'py':
        return this.highlightPython(code);
      case 'bash':
      case 'sh':
        return this.highlightBash(code);
      default:
        return code;
    }
  }

  /**
   * Highlight JavaScript/TypeScript
   */
  highlightJavaScript(code) {
    const keywords = ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 
                     'class', 'import', 'export', 'async', 'await', 'try', 'catch', 'throw',
                     'new', 'this', 'super', 'extends', 'static', 'get', 'set'];
    
    // Highlight keywords
    let highlighted = code;
    keywords.forEach(keyword => {
      const regex = new RegExp(`\\b(${keyword})\\b`, 'g');
      highlighted = highlighted.replace(regex, `${this.colors.keyword}$1${this.colors.reset}`);
    });
    
    // Highlight strings
    highlighted = highlighted.replace(/(["'`])(?:(?=(\\?))\2.)*?\1/g, 
      `${this.colors.string}$&${this.colors.reset}`);
    
    // Highlight numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, 
      `${this.colors.number}$1${this.colors.reset}`);
    
    // Highlight comments
    highlighted = highlighted.replace(/(\/\/.*$|\/\*[\s\S]*?\*\/)/gm, 
      `${this.colors.comment}$&${this.colors.reset}`);
    
    // Highlight function names
    highlighted = highlighted.replace(/\b(\w+)(?=\s*\()/g, 
      `${this.colors.function}$1${this.colors.reset}`);
    
    return highlighted;
  }

  /**
   * Highlight Python
   */
  highlightPython(code) {
    const keywords = ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 
                     'for', 'while', 'try', 'except', 'with', 'as', 'pass', 'break',
                     'continue', 'lambda', 'yield', 'async', 'await', 'raise'];
    
    // Highlight keywords
    let highlighted = code;
    keywords.forEach(keyword => {
      const regex = new RegExp(`\\b(${keyword})\\b`, 'g');
      highlighted = highlighted.replace(regex, `${this.colors.keyword}$1${this.colors.reset}`);
    });
    
    // Highlight strings
    highlighted = highlighted.replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, 
      `${this.colors.string}$&${this.colors.reset}`);
    highlighted = highlighted.replace(/("""|''')[\s\S]*?\1/g, 
      `${this.colors.string}$&${this.colors.reset}`);
    
    // Highlight numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, 
      `${this.colors.number}$1${this.colors.reset}`);
    
    // Highlight comments
    highlighted = highlighted.replace(/(#.*$)/gm, 
      `${this.colors.comment}$&${this.colors.reset}`);
    
    // Highlight function/class names
    highlighted = highlighted.replace(/\b(def|class)\s+(\w+)/g, 
      `${this.colors.keyword}$1${this.colors.reset} ${this.colors.function}$2${this.colors.reset}`);
    
    return highlighted;
  }

  /**
   * Highlight Bash
   */
  highlightBash(code) {
    const keywords = ['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done',
                     'case', 'esac', 'function', 'return', 'exit'];
    
    // Highlight keywords
    let highlighted = code;
    keywords.forEach(keyword => {
      const regex = new RegExp(`\\b(${keyword})\\b`, 'g');
      highlighted = highlighted.replace(regex, `${this.colors.keyword}$1${this.colors.reset}`);
    });
    
    // Highlight strings
    highlighted = highlighted.replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, 
      `${this.colors.string}$&${this.colors.reset}`);
    
    // Highlight comments
    highlighted = highlighted.replace(/(#.*$)/gm, 
      `${this.colors.comment}$&${this.colors.reset}`);
    
    // Highlight variables
    highlighted = highlighted.replace(/(\$\w+|\$\{[^}]+\})/g, 
      `${this.colors.cyan}$&${this.colors.reset}`);
    
    return highlighted;
  }

  /**
   * Format inline markdown (headers, bold, italic, inline code)
   */
  formatMarkdown(text) {
    let formatted = text;
    
    // Headers
    formatted = formatted.replace(/^### (.+)$/gm, 
      `\n${this.colors.bold}${this.colors.color256(153)}▌ $1${this.colors.reset}\n`);
    formatted = formatted.replace(/^## (.+)$/gm, 
      `\n${this.colors.bold}${this.colors.color256(153)}█ $1${this.colors.reset}\n`);
    formatted = formatted.replace(/^# (.+)$/gm, 
      `\n${this.colors.bold}${this.colors.color256(153)}█▌ $1${this.colors.reset}\n`);
    
    // Bold
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, 
      `${this.colors.bold}$1${this.colors.reset}`);
    
    // Italic
    formatted = formatted.replace(/\*([^*]+)\*/g, 
      `${this.colors.italic}$1${this.colors.reset}`);
    
    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, 
      `${this.colors.color256(180)}$1${this.colors.reset}`);
    
    // Lists
    formatted = formatted.replace(/^(\s*)[\*\-] (.+)$/gm, 
      `$1${this.colors.color256(83)}•${this.colors.reset} $2`);
    
    // File paths (simple detection)
    formatted = formatted.replace(/(\/?[\w\-\.]+\/[\w\-\.\/]+\.\w+)/g, 
      `${this.colors.underline}${this.colors.color256(111)}$1${this.colors.reset}`);
    
    return formatted;
  }

  /**
   * Format status indicators
   */
  formatStatus(status, message) {
    const icons = {
      analyzing: '🔍',
      thinking: '🤔',
      writing: '✏️',
      testing: '🧪',
      complete: '✅',
      error: '❌'
    };
    
    const colors = {
      analyzing: this.colors.yellow,
      thinking: this.colors.blue,
      writing: this.colors.green,
      testing: this.colors.cyan,
      complete: this.colors.brightGreen,
      error: this.colors.red
    };
    
    const icon = icons[status] || '•';
    const color = colors[status] || this.colors.white;
    
    return `${color}${icon} ${this.colors.bold}${message}${this.colors.reset}`;
  }

  /**
   * Create a separator line
   */
  createSeparator(width = 60, style = 'light') {
    const char = style === 'light' ? '─' : '═';
    return `${this.colors.dim}${char.repeat(width)}${this.colors.reset}`;
  }

  /**
   * Format a section header
   */
  formatSectionHeader(title) {
    return `\n${this.colors.color256(110)}╭─ ${this.colors.bold}${title}${this.colors.reset}\n`;
  }
}

// Export for use in renderer
window.TerminalFormatter = TerminalFormatter;
