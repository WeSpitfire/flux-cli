/**
 * Settings UI Logic
 */

let currentSettings = {};
let currentProvider = 'anthropic';
let selectedModel = '';

// Initialize settings on load
window.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  setupTabSwitching();
  setupSliders();
});

// Load all settings from backend
async function loadSettings() {
  try {
    currentSettings = await window.settings.get();
    
    // Update UI with current settings
    updateAPIKeyStatus('anthropic', currentSettings.hasAnthropicKey);
    updateAPIKeyStatus('openai', currentSettings.hasOpenAIKey);
    
    // Set provider
    currentProvider = currentSettings.provider || 'anthropic';
    document.getElementById('provider').value = currentProvider;
    
    // Load models for current provider
    await loadModels(currentProvider);
    
    // Set LLM parameters
    document.getElementById('max-tokens').value = currentSettings.maxTokens || 4096;
    document.getElementById('max-tokens-value').textContent = currentSettings.maxTokens || 4096;
    
    document.getElementById('temperature').value = currentSettings.temperature || 0.0;
    document.getElementById('temperature-value').textContent = (currentSettings.temperature || 0.0).toFixed(1);
    
    document.getElementById('max-history').value = currentSettings.maxHistory || 8000;
    document.getElementById('max-history-value').textContent = currentSettings.maxHistory || 8000;
    
    document.getElementById('require-approval').checked = currentSettings.requireApproval !== false;
    
    // Set experimental features
    if (currentSettings.experimental) {
      document.getElementById('smart-suggestions').checked = currentSettings.experimental.smartSuggestions !== false;
      document.getElementById('background-processing').checked = currentSettings.experimental.backgroundProcessing !== false;
      document.getElementById('context-pruning').checked = currentSettings.experimental.contextPruning !== false;
    }
    
    // Set appearance settings
    if (currentSettings.appearance) {
      const typingSpeed = currentSettings.appearance.typingSpeed !== undefined ? currentSettings.appearance.typingSpeed : 3;
      document.getElementById('typing-speed').value = typingSpeed;
      updateTypingSpeedLabel(typingSpeed);
      
      const theme = currentSettings.appearance.theme || 'dark';
      document.getElementById('theme').value = theme;
    }
    
    // Load masked API keys
    const anthropicKey = await window.settings.getApiKey('anthropic');
    const openaiKey = await window.settings.getApiKey('openai');
    
    if (anthropicKey) {
      document.getElementById('anthropic-key').placeholder = anthropicKey;
    }
    if (openaiKey) {
      document.getElementById('openai-key').placeholder = openaiKey;
    }
    
  } catch (error) {
    console.error('Failed to load settings:', error);
    showMessage('error', 'Failed to load settings', 'anthropic');
  }
}

// Load available models for provider
async function loadModels(provider) {
  try {
    const models = await window.settings.getAvailableModels(provider);
    const modelsList = document.getElementById('models-list');
    modelsList.innerHTML = '';
    
    selectedModel = currentSettings.model || models[0]?.id;
    
    models.forEach(model => {
      const card = document.createElement('div');
      card.className = `model-card ${model.id === selectedModel ? 'selected' : ''}`;
      card.onclick = () => selectModel(model.id);
      
      card.innerHTML = `
        <div class="model-card-header">
          <span class="model-name">${model.name}</span>
          ${model.recommended ? '<span class="model-badge">RECOMMENDED</span>' : ''}
        </div>
        <div class="model-details">
          ${model.context.toLocaleString()} tokens context | 
          $${model.cost.input}/$${model.cost.output} per 1M tokens
        </div>
      `;
      
      modelsList.appendChild(card);
    });
  } catch (error) {
    console.error('Failed to load models:', error);
  }
}

// Select a model
function selectModel(modelId) {
  selectedModel = modelId;
  
  // Update UI
  document.querySelectorAll('.model-card').forEach(card => {
    card.classList.remove('selected');
  });
  event.currentTarget.classList.add('selected');
  
  // Auto-save model selection
  saveModelSelection();
}

// Save model selection
async function saveModelSelection() {
  try {
    await window.settings.setModel(selectedModel);
    showMessage('success', `Model set to ${selectedModel}`, 'llm');
  } catch (error) {
    showMessage('error', 'Failed to save model', 'llm');
  }
}

// Update API key status indicator
function updateAPIKeyStatus(provider, hasKey) {
  const statusEl = document.getElementById(`${provider}-status`);
  if (hasKey) {
    statusEl.textContent = 'Configured ✓';
    statusEl.className = 'key-status configured';
  } else {
    statusEl.textContent = 'Not Configured';
    statusEl.className = 'key-status missing';
  }
}

// Toggle API key visibility
function toggleKeyVisibility(inputId) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}

// Save API key
async function saveApiKey(provider) {
  const input = document.getElementById(`${provider}-key`);
  const key = input.value.trim();
  
  if (!key) {
    showMessage('error', 'Please enter an API key', provider);
    return;
  }
  
  // Show validating message
  showMessage('info', 'Validating API key...', provider);
  
  try {
    const result = await window.settings.setApiKey(provider, key);
    
    if (result.success) {
      showMessage('success', '✓ API key validated and saved successfully!', provider);
      updateAPIKeyStatus(provider, true);
      input.value = ''; // Clear input
      
      // Reload to show masked key
      const maskedKey = await window.settings.getApiKey(provider);
      input.placeholder = maskedKey;
    } else if (result.tested) {
      // Key was tested but failed validation
      showMessage('error', `✗ Invalid API key: ${result.error}`, provider);
    } else {
      showMessage('error', result.error || 'Failed to save API key', provider);
    }
  } catch (error) {
    showMessage('error', error.message || 'Failed to save API key', provider);
  }
}

// Test API connection
async function testConnection(provider) {
  const buttonId = `test-${provider}`;
  const button = document.getElementById(buttonId);
  const originalText = button.textContent;
  
  // Show loading
  button.innerHTML = '<span class="loading"></span>';
  
  try {
    const result = await window.settings.testConnection(provider);
    
    if (result.success) {
      showMessage('success', '✓ Connection successful! API key is valid.', provider);
    } else {
      showMessage('error', `✗ Connection failed: ${result.error}`, provider);
    }
  } catch (error) {
    showMessage('error', `✗ Connection failed: ${error.message}`, provider);
  } finally {
    button.textContent = originalText;
  }
}

// Save LLM settings
async function saveLLMSettings() {
  const settings = {
    maxTokens: parseInt(document.getElementById('max-tokens').value),
    temperature: parseFloat(document.getElementById('temperature').value),
    maxHistory: parseInt(document.getElementById('max-history').value),
    requireApproval: document.getElementById('require-approval').checked
  };
  
  try {
    await window.settings.setLLMSettings(settings);
    showMessage('success', 'LLM settings saved successfully', 'llm');
  } catch (error) {
    showMessage('error', 'Failed to save LLM settings', 'llm');
  }
}

// Save appearance settings
async function saveAppearanceSettings() {
  const typingSpeed = parseInt(document.getElementById('typing-speed').value);
  const theme = document.getElementById('theme').value;
  
  try {
    await window.settings.setAppearance({ typingSpeed, theme });
    showMessage('success', 'Appearance settings saved successfully', 'appearance');
  } catch (error) {
    showMessage('error', 'Failed to save appearance settings', 'appearance');
  }
}

// Update typing speed label
function updateTypingSpeedLabel(value) {
  const speedNames = ['Instant', 'Very Fast', 'Fast', 'Normal', 'Slow', 'Very Slow'];
  const label = document.getElementById('typing-speed-value');
  if (label) {
    label.textContent = speedNames[value] || 'Normal';
  }
}

// Save experimental settings
async function saveExperimentalSettings() {
  const features = {
    smartSuggestions: document.getElementById('smart-suggestions').checked,
    backgroundProcessing: document.getElementById('background-processing').checked,
    contextPruning: document.getElementById('context-pruning').checked
  };
  
  try {
    await window.settings.setExperimental(features);
    showMessage('success', 'Experimental settings saved successfully', 'experimental');
  } catch (error) {
    showMessage('error', 'Failed to save experimental settings', 'experimental');
  }
}

// Reset all settings
async function resetSettings() {
  if (!confirm('Are you sure you want to reset all settings? This will clear your API keys and reset everything to defaults.')) {
    return;
  }
  
  try {
    await window.settings.reset();
    showMessage('success', 'Settings reset successfully. Reloading...', 'experimental');
    
    // Reload settings after a delay
    setTimeout(() => {
      window.location.reload();
    }, 1500);
  } catch (error) {
    showMessage('error', 'Failed to reset settings', 'experimental');
  }
}

// Provider change handler
async function onProviderChange() {
  const provider = document.getElementById('provider').value;
  currentProvider = provider;
  
  try {
    await window.settings.setProvider(provider);
    await loadModels(provider);
    showMessage('success', `Provider changed to ${provider}`, 'llm');
  } catch (error) {
    showMessage('error', 'Failed to change provider', 'llm');
  }
}

// Theme change handler
async function onThemeChange() {
  const theme = document.getElementById('theme').value;
  
  try {
    // Get current appearance settings and merge with new theme
    const currentSettings = await window.settings.get();
    const typingSpeed = currentSettings.appearance?.typingSpeed;
    
    // Save theme preference
    await window.settings.setAppearance({ typingSpeed, theme });
    
    // Apply theme to main window via IPC
    await window.settings.applyTheme(theme);
    
    showMessage('success', `Theme changed to ${theme}`, 'appearance');
  } catch (error) {
    showMessage('error', 'Failed to change theme', 'appearance');
  }
}

// Show status message
function showMessage(type, text, section) {
  const messageEl = document.getElementById(`${section}-message`);
  messageEl.textContent = text;
  messageEl.className = `status-message ${type} show`;
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    messageEl.classList.remove('show');
  }, 5000);
}

// Setup tab switching
function setupTabSwitching() {
  const tabs = document.querySelectorAll('.tab');
  const contents = document.querySelectorAll('.tab-content');
  
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.dataset.tab;
      
      // Update active tab
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      
      // Update active content
      contents.forEach(c => c.classList.remove('active'));
      document.querySelector(`.tab-content[data-tab="${targetTab}"]`).classList.add('active');
    });
  });
}

// Setup slider value updates
function setupSliders() {
  const sliders = [
    { id: 'max-tokens', valueId: 'max-tokens-value' },
    { id: 'temperature', valueId: 'temperature-value', formatter: (v) => parseFloat(v).toFixed(1) },
    { id: 'max-history', valueId: 'max-history-value' },
    { id: 'typing-speed', valueId: 'typing-speed-value', formatter: (v) => {
      const speedNames = ['Instant', 'Very Fast', 'Fast', 'Normal', 'Slow', 'Very Slow'];
      return speedNames[parseInt(v)] || 'Normal';
    }}
  ];
  
  sliders.forEach(slider => {
    const input = document.getElementById(slider.id);
    const valueEl = document.getElementById(slider.valueId);
    
    input.addEventListener('input', (e) => {
      const value = e.target.value;
      valueEl.textContent = slider.formatter ? slider.formatter(value) : value;
    });
  });
}
