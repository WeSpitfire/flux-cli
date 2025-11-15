<template>
  <main class="main-content">
    <!-- Sidebar Component -->
    <Sidebar />

    <!-- Terminal and input area -->
    <div class="workspace">
      <div class="tab-bar" id="tab-bar">
        <div class="tab-list" id="tab-list"></div>
        <button class="tab-new-btn" id="new-tab-btn" title="New Tab (Cmd+T)">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
      
      <div class="terminal-wrapper">
        <div id="terminal-container"></div>
        <div class="typing-indicator" id="typing-indicator" style="display: none;">
          <div class="typing-indicator-content">
            <span class="typing-indicator-avatar">🤖</span>
            <div class="typing-indicator-text">
              <span class="typing-indicator-label">Flux is thinking</span>
              <div class="typing-indicator-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="input-area">
        <div class="input-wrapper">
          <div class="input-prefix">$</div>
          <textarea 
            id="command-input" 
            placeholder="Ask Flux anything or type a command..."
            autocomplete="off"
            spellcheck="false"
            rows="1"
            style="resize: none; overflow: hidden;"
          ></textarea>
          <button class="send-btn" id="send-btn" title="Send (Enter)">
            <svg class="send-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M2 10l16-8-8 16-2-6-6-2z" fill="currentColor"/>
            </svg>
            <svg class="stop-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" style="display: none;">
              <rect x="5" y="5" width="10" height="10" rx="1" fill="currentColor"/>
            </svg>
          </button>
        </div>
        <div class="input-hint">
          <span><kbd>↵ Enter</kbd> send</span>
          <span>•</span>
          <span><kbd>⇧ Shift+Enter</kbd> new line</span>
          <span>•</span>
          <span><kbd>⌘ K</kbd> palette</span>
          <span>•</span>
          <span><kbd>↑ ↓</kbd> history</span>
          <span>•</span>
          <span><kbd>Esc</kbd> cancel</span>
        </div>
      </div>
    </div>
  </main>
</template>

<script>
import Sidebar from './Sidebar.vue';

export default {
  name: 'Terminal',
  components: {
    Sidebar
  },
  mounted() {
    // Notify that Vue has mounted the DOM and it's safe to initialize
    console.log('Terminal component mounted - DOM ready');
    
    // Dispatch custom event that renderer.js can listen for
    window.dispatchEvent(new CustomEvent('vue-mounted'));
  }
};
</script>

<style scoped>
/* Component-specific styles can go here */
/* Most styles are already in styles.css */
</style>
