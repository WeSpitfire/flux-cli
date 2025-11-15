<template>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z" fill="currentColor"/>
          </svg>
          <span class="logo-text">Flux</span>
        </div>
      </div>
      <div class="header-center">
        <div class="status-indicator">
          <div class="status-dot" id="status-dot"></div>
          <span id="status-text">Ready</span>
        </div>
      </div>
      <div class="header-right">
        <button class="icon-btn" id="clear-btn" title="Clear terminal">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 14h12M8 2v8m-4-4l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
        <button class="icon-btn" id="settings-btn" title="Settings (⚙️)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v10M1 12h6m6 0h10"/>
            <path d="M4.93 4.93l4.24 4.24m5.66 5.66l4.24 4.24M4.93 19.07l4.24-4.24m5.66-5.66l4.24-4.24"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- Main content -->
    <TerminalComponent />
  </div>
</template>

<script>
import TerminalComponent from './components/Terminal.vue';

export default {
  name: 'App',
  components: {
    TerminalComponent
  }
};
</script>

<style>
/* No additional styles needed - using existing styles.css */
</style>
