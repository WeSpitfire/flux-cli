# Settings Validation & Testing Guide

## Overview

Flux now has **intelligent API key validation** that automatically tests keys before saving, validates them on app startup, and falls back to working keys if the configured provider fails.

## Key Features

### 1. **Automatic Validation on Save**
When you save an API key, Flux immediately tests it against the provider's API:
- ✅ If valid → Key is saved and marked as validated
- ❌ If invalid → Shows specific error (401, 403, 404, etc.) and rejects save

### 2. **Smart Provider Selection**
When starting Flux, it automatically:
1. Checks if configured provider's key is valid (with 1-hour cache)
2. If invalid, tries the fallback provider
3. Uses whichever key works
4. Shows clear messages about which provider is active

### 3. **Validation Caching**
- Valid keys are cached for 1 hour
- Prevents unnecessary API calls on every tab creation
- Automatically re-validates after cache expires

### 4. **Detailed Error Messages**
HTTP status codes are shown for failed validations:
- `401` - Invalid API key (wrong key)
- `403` - Access forbidden (key lacks permissions)
- `404` - Endpoint not found (wrong API URL or key format)
- `429` - Rate limit exceeded
- `500+` - Server errors

## How It Works

### Saving an API Key

```javascript
// User enters key and clicks "Save"
1. UI shows "Validating API key..."
2. Settings manager tests key against provider API
3. If valid:
   - Key is saved encrypted
   - Validation timestamp stored
   - UI shows "✓ API key validated and saved successfully!"
4. If invalid:
   - Key is NOT saved
   - UI shows "✗ Invalid API key: [specific error]"
```

### Starting Flux Process

```javascript
// When creating a new tab
1. settingsManager.getBestWorkingProvider() is called
2. Checks configured provider:
   - If validated within 1 hour → use it (cached)
   - If not recently validated → test it
   - If test passes → use it and cache result
3. If configured provider fails:
   - Test fallback provider
   - If fallback works → use it and log warning
4. If no keys work:
   - Log error
   - Set basic env vars (Flux will show its own error)
```

### Console Messages

You'll see helpful logs:
```
[Tab tab-1] Using provider: anthropic (cached), model: claude-3-5-sonnet-20241022
[Tab tab-2] Using provider: openai (fallback), model: gpt-4o
[Tab tab-3] No valid API keys found: Invalid API key (401 Unauthorized)
```

## Testing Scenarios

### Scenario 1: Valid Anthropic Key
1. Go to Settings → API Keys
2. Enter valid Anthropic key
3. Click "Save Key"
4. **Expected**: "✓ API key validated and saved successfully!"
5. Create new tab
6. **Expected**: `[Tab X] Using provider: anthropic, model: claude-3-5-sonnet-20241022`

### Scenario 2: Invalid Key
1. Enter fake key: `sk-ant-invalid`
2. Click "Save Key"
3. **Expected**: "✗ Invalid API key: Invalid API key (401 Unauthorized)"
4. Key is NOT saved
5. Status remains "Not Configured"

### Scenario 3: Fallback to Working Provider
1. Configure Anthropic as provider
2. But only have valid OpenAI key
3. Create new tab
4. **Expected**: `[Tab X] Using provider: openai (fallback), model: gpt-4o`
5. Flux works with OpenAI despite Anthropic being configured

### Scenario 4: No Valid Keys
1. Remove all API keys or use invalid ones
2. Create new tab
3. **Expected**: `[Tab X] No valid API keys found: No valid API keys found`
4. Flux starts but shows error about missing API key

### Scenario 5: Validation Cache
1. Save valid key → validates (takes 1-2 seconds)
2. Create another tab immediately
3. **Expected**: `[Tab X] Using provider: anthropic (cached), model: ...`
4. No delay - uses cached validation

### Scenario 6: HTTP Status Codes
Test various error conditions:

**404 - Endpoint Not Found**
```
Wrong key format or API endpoint changed
Shows: "Endpoint not found (404)"
```

**429 - Rate Limit**
```
Too many requests
Shows: "Rate limit exceeded (429)"
```

**500 - Server Error**
```
Provider API is down
Shows: "Server error (500)"
```

## Validation Status

Keys are stored with validation metadata:

```json
{
  "keyValidation": {
    "anthropic": {
      "valid": true,
      "lastTested": "2025-11-03T02:52:00.000Z"
    },
    "openai": {
      "valid": false,
      "lastTested": "2025-11-03T01:00:00.000Z"
    }
  }
}
```

## Testing Commands

### Test Anthropic Key Manually
```javascript
// In DevTools console
await window.settings.testConnection('anthropic')
// Returns: { success: true, provider: 'anthropic' }
// or: { success: false, error: 'Invalid API key (401 Unauthorized)' }
```

### Test OpenAI Key
```javascript
await window.settings.testConnection('openai')
```

### Get Best Working Provider
```javascript
await window.settings.getBestWorkingProvider()
// Returns:
// {
//   provider: 'anthropic',
//   key: 'sk-ant-...',
//   model: 'claude-3-5-sonnet-20241022',
//   validated: true,
//   cached: true
// }
```

## Configuration File Location

Settings are stored encrypted at:
- **macOS**: `~/Library/Application Support/flux-settings/config.json`
- **Linux**: `~/.config/flux-settings/config.json`
- **Windows**: `%APPDATA%\flux-settings\config.json`

## Best Practices

1. **Test Connection After Saving**
   - Always click "Test Connection" after saving a key
   - Verifies the key works before you try to use Flux

2. **Configure Both Providers**
   - Have both Anthropic and OpenAI keys configured
   - Automatic fallback if one fails
   - Redundancy for rate limits

3. **Monitor Console Logs**
   - Check which provider is being used
   - Look for fallback warnings
   - Spot validation failures early

4. **Re-validate After Errors**
   - If you get a 401/403, check your key on the provider dashboard
   - Keys can expire or be revoked
   - Re-save a fresh key

## Troubleshooting

### "Invalid API key (401)"
- Key is wrong or expired
- Check provider dashboard
- Generate new key and save again

### "Endpoint not found (404)"
- Wrong key format (doesn't match provider)
- API endpoint changed (unlikely)
- Check you're using the right provider

### "Rate limit exceeded (429)"
- Too many requests
- Wait a few minutes
- Consider upgrading plan
- Switch to fallback provider

### "No valid API keys found"
- Both providers failed validation
- Check both keys on their dashboards
- Verify network connectivity
- Try saving keys again

### Fallback Used Unexpectedly
```
[Tab X] Using provider: openai (fallback), model: gpt-4o
```
- Configured provider failed validation
- Check configured provider's key
- Either fix it or change configured provider to match working key

## Security Notes

- Keys are encrypted on disk
- Keys are validated before storage
- Invalid keys are rejected and not stored
- Validation happens server-side (secure)
- Keys only sent to official provider APIs

## Future Enhancements

- [ ] Show validation status in UI with icons
- [ ] Add "Re-validate All Keys" button
- [ ] Track validation history
- [ ] Show last validation time in UI
- [ ] Warn when validation cache is about to expire
- [ ] Support for multiple keys per provider
- [ ] Key rotation support
