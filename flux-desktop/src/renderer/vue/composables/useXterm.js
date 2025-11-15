import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';

// Import xterm CSS
import 'xterm/css/xterm.css';

// Expose xterm classes globally for vanilla JS compatibility
export function initializeXterm() {
  console.log('[Xterm] Initializing and exposing to window...');
  
  // Make xterm available globally for vanilla JS code
  // Match the structure expected by vanilla JS: window.FitAddon.FitAddon
  window.Terminal = Terminal;
  window.FitAddon = { FitAddon };
  window.WebLinksAddon = { WebLinksAddon };
  
  console.log('[Xterm] Exposed to window:', {
    Terminal: !!window.Terminal,
    'FitAddon.FitAddon': !!(window.FitAddon && window.FitAddon.FitAddon),
    'WebLinksAddon.WebLinksAddon': !!(window.WebLinksAddon && window.WebLinksAddon.WebLinksAddon)
  });
}

export { Terminal, FitAddon, WebLinksAddon };
