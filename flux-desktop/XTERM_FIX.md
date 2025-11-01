# xterm Loading Fix

## Problem

`Uncaught TypeError: FitAddon is not a constructor`

This error occurred because xterm modules couldn't be loaded in the renderer process with `contextIsolation: true` and `nodeIntegration: false`.

## Root Cause

When using Electron's security features:
- `contextIsolation: true` - Separates renderer from Node.js
- `nodeIntegration: false` - Prevents `require()` in renderer

The renderer process couldn't use `require('xterm')` to load modules from `node_modules`.

## Solution

### Option 1: Enable nodeIntegration (Current Implementation)

**Changes made:**

1. **main.js** - Enable nodeIntegration:
```javascript
webPreferences: {
  preload: path.join(__dirname, '..', 'preload', 'preload.js'),
  nodeIntegration: true,      // Changed from false
  contextIsolation: false     // Changed from true
}
```

2. **preload.js** - Simplified to direct window assignment:
```javascript
window.flux = {
  sendCommand: (command) => { ... },
  onOutput: (callback) => { ... },
  onError: (callback) => { ... }
};
```

3. **index.html** - Updated CSP:
```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; style-src 'self' 'unsafe-inline'; 
               script-src 'self' 'unsafe-inline' 'unsafe-eval';">
```

4. **renderer.js** - Standard require statements:
```javascript
const { Terminal } = require('xterm');
const { FitAddon } = require('xterm-addon-fit');
const { WebLinksAddon } = require('xterm-addon-web-links');
```

**Pros:**
- ✅ Simple and straightforward
- ✅ No bundling needed
- ✅ Direct access to node_modules

**Cons:**
- ⚠️ Less secure (renders process has full Node.js access)
- ⚠️ Not best practice for production apps

### Option 2: Use Webpack/Bundler (Recommended for Production)

For a production app, you should bundle xterm with webpack:

1. Install webpack:
```bash
npm install --save-dev webpack webpack-cli
```

2. Create `webpack.config.js`:
```javascript
module.exports = {
  target: 'electron-renderer',
  entry: './src/renderer/renderer.js',
  output: {
    path: __dirname + '/dist',
    filename: 'renderer.bundle.js'
  }
};
```

3. Keep security features enabled:
```javascript
nodeIntegration: false,
contextIsolation: true
```

4. Load bundled file in HTML:
```html
<script src="renderer.bundle.js"></script>
```

### Option 3: Use CDN (Not Recommended)

Load xterm from CDN in HTML, but this requires internet connection.

## Current Status

✅ **Working** with nodeIntegration enabled
- Terminal loads correctly
- FitAddon works
- WebLinksAddon works
- All functionality operational

⚠️ **Security Trade-off**
- For a desktop app used locally, this is acceptable
- For production/distributed apps, consider bundling

## Testing

To verify the fix works, run:

```bash
cd flux-desktop

# Test basic xterm loading
npx electron test-electron.js

# Test full app
npm run dev
```

You should see:
1. Terminal renders with welcome message
2. No "FitAddon is not a constructor" error
3. Terminal fits properly to window
4. All features work

## Verification

Check in DevTools console:
```javascript
// Should return "function"
typeof Terminal

// Should return "function"  
typeof FitAddon

// Should work
const term = new Terminal();
```

## Future Improvements

For production release:
1. Set up webpack bundling
2. Re-enable security features
3. Use contextBridge properly
4. Minimize renderer process privileges
5. Add code signing

## Related Files

- `src/main/main.js` - Electron main process config
- `src/preload/preload.js` - Preload script  
- `src/renderer/renderer.js` - Renderer with xterm
- `src/renderer/index.html` - HTML with CSP
- `test-electron.js` - Test script for xterm
- `test-xterm.html` - Test page for xterm

## References

- [Electron Security](https://www.electronjs.org/docs/latest/tutorial/security)
- [xterm.js Documentation](https://xtermjs.org/)
- [Electron Context Isolation](https://www.electronjs.org/docs/latest/tutorial/context-isolation)
