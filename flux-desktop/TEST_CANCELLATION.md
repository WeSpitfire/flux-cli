# Quick Test Guide: Streaming Cancellation

## Prerequisites
```bash
cd /Users/developer/SynologyDrive/flux-cli/flux-desktop
npm install
npm run dev
```

## Test Scenarios

### Test 1: Basic Cancellation via Button
1. Start the Flux Desktop app
2. Type a command that takes time (e.g., "explain all files in this project")
3. Press Enter to send
4. **Verify**: Send button changes to red stop button
5. Click the stop button
6. **Verify**: 
   - Terminal shows "^C Command cancelled" (yellow text)
   - Button reverts to blue send button
   - Status shows "Ready"
   - No more output appears

### Test 2: Cancellation via Ctrl+C
1. Send another long-running command
2. While processing, press **Ctrl+C** (or Cmd+C on macOS)
3. **Verify**: Same behavior as Test 1

### Test 3: Button State Changes
1. **Initial state**: Blue send button with arrow icon
2. **During processing**: Red stop button with square icon
3. **After completion/cancellation**: Reverts to blue send button
4. **Hover states**: 
   - Send mode: lighter blue on hover
   - Stop mode: lighter red on hover

### Test 4: Multiple Cancel/Send Cycles
1. Send command → Cancel → Send command → Cancel → Send command → Let complete
2. **Verify**: Button toggles correctly each time
3. **Verify**: State remains consistent

### Test 5: Output Queue Clearing
1. Send a command that generates lots of output
2. Wait for typewriter effect to start
3. Cancel immediately
4. **Verify**: Remaining output doesn't appear
5. **Verify**: New commands work normally

### Test 6: Error Handling
1. Send an invalid command
2. **Verify**: Button reverts to send mode on error
3. **Verify**: Can send new commands

### Test 7: Keyboard Shortcut During Idle
1. When no command is processing
2. Press Ctrl+C
3. **Verify**: Nothing happens (command not cancelled)
4. **Verify**: Can still type in input field

## Visual Verification Checklist

- [ ] Send icon: Paper plane shape, blue background
- [ ] Stop icon: Square shape, red background
- [ ] Tooltip changes: "Send (Enter)" ↔ "Stop (Ctrl+C)"
- [ ] Cancellation message: Yellow "^C Command cancelled"
- [ ] Status indicator: "Processing..." → "Ready"
- [ ] Button smooth color transition
- [ ] Icons toggle without flicker

## Edge Cases

### Edge Case 1: Rapid Cancel/Send
1. Send → immediately cancel → immediately send → immediately cancel
2. **Verify**: UI doesn't get stuck

### Edge Case 2: Cancel at End of Output
1. Send command with moderate output
2. Cancel just as output finishes
3. **Verify**: State resolves correctly

### Edge Case 3: Empty Input with Stop Button
1. While processing, clear the input field
2. Try to send again (should cancel instead)
3. **Verify**: Cancels, not sends

## Expected Console Output

### Backend (main.js console):
```
[Flux stdout]: <command output>
[Flux process error]: Process interrupted (if cancelled)
```

### Frontend (DevTools console):
```
Received flux output: <length> chars
(No errors should appear)
```

## Common Issues & Solutions

### Issue: Button doesn't change color
**Check**: 
- CSS file loaded correctly
- `.stop-mode` class applied
- Browser cache cleared

### Issue: Ctrl+C doesn't work
**Check**:
- Input field has focus
- `state.isProcessing` is true
- Event listener registered

### Issue: Process doesn't stop
**Check**:
- Backend receives `flux-cancel` event
- SIGINT sent to process
- Flux CLI supports interruption

### Issue: UI state stuck in processing
**Check**:
- `updateSendButton(false)` called in all completion paths
- Error handlers reset state
- No uncaught exceptions

## Success Criteria

✅ All test scenarios pass without errors
✅ Button visual states correct
✅ Keyboard shortcuts work as expected
✅ No console errors
✅ State resets properly after cancellation
✅ Can send new commands after cancellation
✅ Output queue clears immediately
✅ Terminal feedback is clear

## Performance Notes

- Cancellation should be **immediate** (< 100ms UI response)
- Process termination may take longer (depends on Flux CLI)
- UI remains responsive during cancellation
- No memory leaks from cancelled operations

## Next Steps After Testing

1. If all tests pass: Ready for user testing
2. If issues found: Review STREAMING_CANCELLATION.md for implementation details
3. Consider adding automated tests using Spectron or similar
4. Gather user feedback on cancellation UX

## Automated Test Ideas (Future)

```javascript
// Example Spectron test
it('should cancel command on stop button click', async () => {
  await app.client.setValue('#command-input', 'test command');
  await app.client.click('#send-btn');
  await app.client.waitUntil(() => 
    app.client.getAttribute('#send-btn', 'class').includes('stop-mode')
  );
  await app.client.click('#send-btn');
  const terminalText = await app.client.getText('#terminal');
  expect(terminalText).toContain('Command cancelled');
});
```

## Debugging Tips

1. **Enable DevTools**: Run with `npm run dev` (includes --dev flag)
2. **Backend logs**: Check main.js console for IPC events
3. **Frontend logs**: Check browser DevTools console
4. **State inspection**: Add `console.log(state)` in key functions
5. **IPC tracing**: Log all IPC send/receive calls

## Manual Code Review Points

- ✅ SIGINT sent to process (not SIGKILL)
- ✅ State machine has no deadlocks
- ✅ All error paths reset state
- ✅ Memory cleaned up (outputQueue cleared)
- ✅ Event listeners don't leak
- ✅ Keyboard shortcuts don't conflict
- ✅ Accessibility: button state announced to screen readers
- ✅ Cross-platform: Works on macOS, Linux, Windows
