# Flux Desktop Troubleshooting Guide

This guide helps you debug and fix common issues with Flux Desktop.

## Quick Diagnostics

### 1. Check Flux CLI is working

```bash
cd /Users/developer/SynologyDrive/flux-cli
source venv/bin/activate
flux --help
```

If this fails, reinstall Flux:
```bash
pip install -e .
```

### 2. Check Node dependencies

```bash
cd flux-desktop
npm install
```

### 3. Test the app with console output

```bash
cd flux-desktop
npm run dev
```

Check the terminal for:
- `[Flux stdout]:` - Output from Flux CLI
- `[Flux stderr]:` - Errors from Flux CLI  
- `[Flux process error]:` - Process spawn errors

## Common Issues

### Terminal Not Showing Content

**Symptom**: Terminal area is blank or shows only the welcome message

**Possible causes**:
1. Flux process failed to start
2. xterm.js not loading correctly
3. CSS/JavaScript errors

**Solutions**:

1. **Open DevTools** (automatically opens in dev mode)
   - Check Console for JavaScript errors
   - Check Network tab for failed resource loads

2. **Verify Flux process**:
   ```bash
   # In another terminal
   ps aux | grep flux
   ```

3. **Check xterm.js loading**:
   - Open DevTools Console
   - Type: `typeof Terminal`
   - Should return `"function"`, not `"undefined"`

### "Process error: spawn flux ENOENT"

**Symptom**: Error message about flux command not found

**Cause**: Flux CLI not in PATH or venv not activated

**Solution**:
```bash
cd /Users/developer/SynologyDrive/flux-cli
pip install -e .
# Verify installation
which flux
```

### Commands Not Sending to Flux

**Symptom**: Typing commands and pressing Enter does nothing

**Solutions**:

1. **Check IPC handlers**:
   - Open DevTools Console
   - Type: `window.flux`
   - Should show object with `sendCommand`, `onOutput`, `onError`

2. **Check process status**:
   - Look at status indicator in header
   - Should show "Ready" (green dot)
   - If "Error" (red), check main process console

3. **Verify preload script**:
   ```javascript
   // In DevTools Console
   console.log(window.flux);
   ```

### No Output from Flux

**Symptom**: Commands send but no response appears

**Possible causes**:
1. Flux process crashed
2. Output not being piped correctly
3. Terminal not receiving data

**Debugging**:

1. **Check main process logs**:
   - Terminal where you ran `npm run dev`
   - Look for `[Flux stdout]:` or `[Flux stderr]:`

2. **Test Flux directly**:
   ```bash
   cd /Users/developer/SynologyDrive/flux-cli
   source venv/bin/activate
   flux
   ```
   Try a simple command like "list files"

3. **Check event listeners**:
   ```javascript
   // In DevTools Console
   // This should increment when flux outputs
   let count = 0;
   window.flux.onOutput(() => count++);
   // Send command, then check: console.log(count);
   ```

### Electron Window Won't Open

**Symptom**: `npm run dev` starts but no window appears

**Solutions**:

1. **Check for errors**:
   ```bash
   npm run dev 2>&1 | tee flux-desktop-debug.log
   ```

2. **Try without dev flag**:
   ```bash
   npm start
   ```

3. **Clear Electron cache**:
   ```bash
   rm -rf ~/Library/Application\ Support/flux-desktop
   ```

### Styling Issues / Blank Screen

**Symptom**: App opens but UI is broken or blank

**Solutions**:

1. **Verify CSS loading**:
   - Open DevTools
   - Check Network tab
   - Ensure `styles.css` loads (200 status)

2. **Check CSP errors**:
   - Look in Console for Content Security Policy errors
   - If present, adjust CSP in `index.html`

3. **Hard refresh**:
   - Close app
   - Delete Electron cache (see above)
   - Restart

## Development Tips

### Enable Verbose Logging

Edit `src/main/main.js`, add after spawn:

```javascript
fluxProcess.stdout.on('data', (data) => {
  const output = data.toString();
  console.log('[VERBOSE Flux stdout]:', output);
  console.log('[VERBOSE Flux stdout HEX]:', Buffer.from(output).toString('hex'));
  win.webContents.send('flux-output', output);
});
```

### Test Flux Communication

Create a test button in `index.html`:

```html
<button onclick="window.flux.sendCommand('list files')">Test Command</button>
```

### Check Process State

In main process (add to `main.js`):

```javascript
setInterval(() => {
  console.log('Flux process alive:', fluxProcess && !fluxProcess.killed);
}, 5000);
```

## Getting More Help

If you're still stuck:

1. **Collect diagnostic info**:
   ```bash
   # System info
   node --version
   npm --version
   python3 --version
   
   # Flux info
   cd /Users/developer/SynologyDrive/flux-cli
   source venv/bin/activate
   flux --version  # If this command exists
   pip list | grep flux
   
   # Process info
   ps aux | grep flux
   ps aux | grep electron
   ```

2. **Check logs**:
   - Main process: Terminal where you ran `npm run dev`
   - Renderer process: Electron DevTools Console
   - Flux CLI: `~/.flux/logs/` (if exists)

3. **Create a minimal test**:
   ```bash
   # Test Flux CLI works
   echo "list files" | flux
   ```

## Environment Variables

Add to `~/.zshrc` or `~/.bashrc` if needed:

```bash
# Ensure Python venv is accessible
export PATH="/Users/developer/SynologyDrive/flux-cli/venv/bin:$PATH"

# Enable Electron debugging
export ELECTRON_ENABLE_LOGGING=1
```

## Known Limitations

1. **No pseudo-TTY**: Flux runs without a full PTY, so some interactive features may not work
2. **ANSI codes**: Some complex ANSI escape sequences might not render perfectly
3. **Input modes**: Multi-line input not yet implemented

## Clean Reinstall

If all else fails:

```bash
# Clean Node
cd flux-desktop
rm -rf node_modules package-lock.json
npm install

# Clean Python
cd ..
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Clean Electron cache
rm -rf ~/Library/Application\ Support/flux-desktop
rm -rf ~/Library/Caches/flux-desktop

# Restart
cd flux-desktop
npm run dev
```
