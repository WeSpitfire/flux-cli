/**
 * Settings Manager - Secure storage for API keys and preferences
 * Uses electron-store with encryption for sensitive data
 */

const Store = require('electron-store');
const { app } = require('electron');

class SettingsManager {
  constructor() {
    // Create encrypted store for API keys
    this.store = new Store({
      name: 'flux-settings',
      encryptionKey: this._getEncryptionKey(),
      defaults: {
        provider: 'anthropic',
        model: 'claude-3-5-sonnet-20241022',
        maxTokens: 4096,
        temperature: 0.0,
        maxHistory: 8000,
        requireApproval: true,
        apiKeys: {
          anthropic: '',
          openai: ''
        },
        appearance: {
          theme: 'dark',
          fontSize: 14,
          fontFamily: 'Menlo, Monaco, "Courier New", monospace',
          typingSpeed: 3  // 0-5: Instant, Very Fast, Fast, Normal, Slow, Very Slow
        },
        experimental: {
          smartSuggestions: true,
          backgroundProcessing: true,
          contextPruning: true
        }
      }
    });
  }

  /**
   * Get encryption key from machine ID
   * Falls back to app path if machine ID unavailable
   */
  _getEncryptionKey() {
    try {
      const crypto = require('crypto');
      const os = require('os');
      
      // Use machine-specific identifiers for encryption
      const machineId = os.hostname() + os.platform() + os.arch();
      return crypto.createHash('sha256').update(machineId).digest('hex');
    } catch (error) {
      console.warn('Failed to generate encryption key, using fallback');
      return 'flux-default-key-change-in-production';
    }
  }

  /**
   * Get all settings
   */
  getSettings() {
    return {
      provider: this.store.get('provider'),
      model: this.store.get('model'),
      maxTokens: this.store.get('maxTokens'),
      temperature: this.store.get('temperature'),
      maxHistory: this.store.get('maxHistory'),
      requireApproval: this.store.get('requireApproval'),
      hasAnthropicKey: !!this.store.get('apiKeys.anthropic'),
      hasOpenAIKey: !!this.store.get('apiKeys.openai'),
      appearance: this.store.get('appearance'),
      experimental: this.store.get('experimental')
    };
  }

  /**
   * Get API key for provider (masked for display)
   */
  getApiKey(provider, masked = true) {
    const key = this.store.get(`apiKeys.${provider}`) || '';
    
    if (masked && key) {
      // Show first 8 and last 4 characters
      if (key.length > 12) {
        return `${key.substring(0, 8)}...${key.substring(key.length - 4)}`;
      }
      return key.substring(0, 8) + '...';
    }
    
    return key;
  }

  /**
   * Get full API key (unmasked) for CLI use
   */
  getFullApiKey(provider) {
    return this.store.get(`apiKeys.${provider}`) || '';
  }

  /**
   * Set API key for provider
   */
  async setApiKey(provider, key) {
    if (!['anthropic', 'openai'].includes(provider)) {
      throw new Error(`Invalid provider: ${provider}`);
    }
    
    // Validate key format
    if (key && !this._validateKeyFormat(provider, key)) {
      throw new Error(`Invalid API key format for ${provider}`);
    }
    
    // Test the key before saving
    if (key) {
      const testResult = await this._testKey(provider, key);
      if (!testResult.success) {
        return {
          success: false,
          error: testResult.error || 'API key validation failed',
          tested: true
        };
      }
    }
    
    this.store.set(`apiKeys.${provider}`, key);
    
    // Store validation status
    const validationStatus = this.store.get('keyValidation') || {};
    validationStatus[provider] = {
      valid: !!key,
      lastTested: new Date().toISOString()
    };
    this.store.set('keyValidation', validationStatus);
    
    return { success: true, validated: true };
  }

  /**
   * Validate API key format
   */
  _validateKeyFormat(provider, key) {
    if (!key) return true; // Empty is valid (removal)
    
    if (provider === 'anthropic') {
      // Anthropic keys start with "sk-ant-"
      return key.startsWith('sk-ant-') && key.length > 20;
    } else if (provider === 'openai') {
      // OpenAI keys start with "sk-"
      return key.startsWith('sk-') && key.length > 20;
    }
    
    return false;
  }

  /**
   * Update provider settings
   */
  setProvider(provider) {
    if (!['anthropic', 'openai'].includes(provider)) {
      throw new Error(`Invalid provider: ${provider}`);
    }
    
    this.store.set('provider', provider);
    return { success: true };
  }

  /**
   * Update model
   */
  setModel(model) {
    this.store.set('model', model);
    return { success: true };
  }

  /**
   * Update LLM settings
   */
  setLLMSettings(settings) {
    const validSettings = {};
    
    if (settings.maxTokens !== undefined) {
      validSettings.maxTokens = Math.max(1024, Math.min(16000, settings.maxTokens));
    }
    
    if (settings.temperature !== undefined) {
      validSettings.temperature = Math.max(0, Math.min(2, settings.temperature));
    }
    
    if (settings.maxHistory !== undefined) {
      validSettings.maxHistory = Math.max(2000, Math.min(150000, settings.maxHistory));
    }
    
    if (settings.requireApproval !== undefined) {
      validSettings.requireApproval = !!settings.requireApproval;
    }
    
    // Update all valid settings
    Object.keys(validSettings).forEach(key => {
      this.store.set(key, validSettings[key]);
    });
    
    return { success: true, updated: validSettings };
  }

  /**
   * Update appearance settings
   */
  setAppearance(appearance) {
    const current = this.store.get('appearance');
    this.store.set('appearance', { ...current, ...appearance });
    return { success: true };
  }

  /**
   * Update experimental features
   */
  setExperimental(features) {
    const current = this.store.get('experimental');
    this.store.set('experimental', { ...current, ...features });
    return { success: true };
  }

  /**
   * Test API key connection
   */
  async testConnection(provider) {
    const key = this.getFullApiKey(provider);
    return await this._testKey(provider, key);
  }
  
  /**
   * Test a specific API key
   */
  async _testKey(provider, key) {
    if (!key) {
      return { 
        success: false, 
        error: 'No API key configured' 
      };
    }
    
    try {
      if (provider === 'anthropic') {
        return await this._testAnthropic(key);
      } else if (provider === 'openai') {
        return await this._testOpenAI(key);
      }
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Test Anthropic API key
   */
  async _testAnthropic(apiKey) {
    const https = require('https');
    
    return new Promise((resolve) => {
      const options = {
        hostname: 'api.anthropic.com',
        port: 443,
        path: '/v1/messages',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01'
        }
      };
      
      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          if (res.statusCode === 200) {
            resolve({ success: true, provider: 'anthropic' });
          } else if (res.statusCode === 401) {
            resolve({ success: false, error: 'Invalid API key (401 Unauthorized)' });
          } else if (res.statusCode === 403) {
            resolve({ success: false, error: 'Access forbidden (403)' });
          } else if (res.statusCode === 404) {
            resolve({ success: false, error: 'Endpoint not found (404)' });
          } else if (res.statusCode === 429) {
            resolve({ success: false, error: 'Rate limit exceeded (429)' });
          } else if (res.statusCode >= 500) {
            resolve({ success: false, error: `Server error (${res.statusCode})` });
          } else {
            resolve({ success: false, error: `HTTP error (${res.statusCode})` });
          }
        });
      });
      
      req.on('error', (error) => {
        resolve({ success: false, error: error.message });
      });
      
      // Send minimal test request
      req.write(JSON.stringify({
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 1,
        messages: [{ role: 'user', content: 'Hi' }]
      }));
      
      req.end();
    });
  }

  /**
   * Test OpenAI API key
   */
  async _testOpenAI(apiKey) {
    const https = require('https');
    
    return new Promise((resolve) => {
      const options = {
        hostname: 'api.openai.com',
        port: 443,
        path: '/v1/models',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      };
      
      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          if (res.statusCode === 200) {
            resolve({ success: true, provider: 'openai' });
          } else if (res.statusCode === 401) {
            resolve({ success: false, error: 'Invalid API key (401 Unauthorized)' });
          } else if (res.statusCode === 403) {
            resolve({ success: false, error: 'Access forbidden (403)' });
          } else if (res.statusCode === 404) {
            resolve({ success: false, error: 'Endpoint not found (404)' });
          } else if (res.statusCode === 429) {
            resolve({ success: false, error: 'Rate limit exceeded (429)' });
          } else if (res.statusCode >= 500) {
            resolve({ success: false, error: `Server error (${res.statusCode})` });
          } else {
            resolve({ success: false, error: `HTTP error (${res.statusCode})` });
          }
        });
      });
      
      req.on('error', (error) => {
        resolve({ success: false, error: error.message });
      });
      
      req.end();
    });
  }

  /**
   * Get available models for provider
   */
  getAvailableModels(provider) {
    const models = {
      anthropic: [
        { 
          id: 'claude-3-5-sonnet-20241022', 
          name: 'Claude 3.5 Sonnet (New)', 
          recommended: true,
          context: 200000,
          cost: { input: 3, output: 15 }
        },
        { 
          id: 'claude-3-5-sonnet-20240620', 
          name: 'Claude 3.5 Sonnet (Legacy)', 
          recommended: false,
          context: 200000,
          cost: { input: 3, output: 15 }
        },
        { 
          id: 'claude-3-opus-20240229', 
          name: 'Claude 3 Opus', 
          recommended: false,
          context: 200000,
          cost: { input: 15, output: 75 }
        },
        { 
          id: 'claude-3-haiku-20240307', 
          name: 'Claude 3 Haiku', 
          recommended: false,
          context: 200000,
          cost: { input: 0.25, output: 1.25 }
        }
      ],
      openai: [
        { 
          id: 'gpt-4o', 
          name: 'GPT-4o', 
          recommended: true,
          context: 128000,
          cost: { input: 5, output: 15 }
        },
        { 
          id: 'gpt-4-turbo', 
          name: 'GPT-4 Turbo', 
          recommended: false,
          context: 128000,
          cost: { input: 10, output: 30 }
        },
        { 
          id: 'gpt-4', 
          name: 'GPT-4', 
          recommended: false,
          context: 8192,
          cost: { input: 30, output: 60 }
        }
      ]
    };
    
    return models[provider] || [];
  }

  /**
   * Reset all settings to defaults
   */
  resetToDefaults() {
    this.store.clear();
    return { success: true };
  }

  /**
   * Export settings (without API keys for security)
   */
  exportSettings() {
    const settings = this.getSettings();
    delete settings.hasAnthropicKey;
    delete settings.hasOpenAIKey;
    return settings;
  }

  /**
   * Get settings file path for CLI
   */
  getSettingsPath() {
    return this.store.path;
  }
  
  /**
   * Get the best working provider and key
   * Returns the configured provider if valid, otherwise tries fallback
   */
  async getBestWorkingProvider() {
    const settings = this.getSettings();
    const configuredProvider = settings.provider;
    
    // Check if configured provider has a valid key
    const configuredKey = this.getFullApiKey(configuredProvider);
    if (configuredKey) {
      // Use cached validation if recent (within 1 hour)
      const validation = this.store.get('keyValidation') || {};
      const providerValidation = validation[configuredProvider];
      
      if (providerValidation && providerValidation.valid) {
        const lastTested = new Date(providerValidation.lastTested);
        const hoursSinceTest = (Date.now() - lastTested.getTime()) / (1000 * 60 * 60);
        
        if (hoursSinceTest < 1) {
          // Recently validated, trust it
          return {
            provider: configuredProvider,
            key: configuredKey,
            model: settings.model,
            validated: true,
            cached: true
          };
        }
      }
      
      // Test the configured key
      const testResult = await this._testKey(configuredProvider, configuredKey);
      if (testResult.success) {
        // Update validation cache
        validation[configuredProvider] = {
          valid: true,
          lastTested: new Date().toISOString()
        };
        this.store.set('keyValidation', validation);
        
        return {
          provider: configuredProvider,
          key: configuredKey,
          model: settings.model,
          validated: true
        };
      }
    }
    
    // Configured provider failed, try fallback
    const fallbackProvider = configuredProvider === 'anthropic' ? 'openai' : 'anthropic';
    const fallbackKey = this.getFullApiKey(fallbackProvider);
    
    if (fallbackKey) {
      const testResult = await this._testKey(fallbackProvider, fallbackKey);
      if (testResult.success) {
        console.warn(`[Settings] Configured provider ${configuredProvider} failed, using fallback ${fallbackProvider}`);
        
        // Get default model for fallback provider
        const fallbackModels = this.getAvailableModels(fallbackProvider);
        const fallbackModel = fallbackModels[0]?.id;
        
        return {
          provider: fallbackProvider,
          key: fallbackKey,
          model: fallbackModel,
          validated: true,
          fallback: true
        };
      }
    }
    
    // No working keys
    return {
      provider: configuredProvider,
      key: null,
      model: settings.model,
      validated: false,
      error: 'No valid API keys found'
    };
  }
}

module.exports = SettingsManager;
