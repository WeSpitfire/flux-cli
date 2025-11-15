<template>
  <div class="sidebar-panel" id="history-panel">
    <div class="sidebar-header">
      <h3>Recent Commands</h3>
      <button class="icon-btn" id="toggle-sidebar">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 4L6 8l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
    <div class="history-list" id="history-list">
      <!-- History items will be populated by vanilla JS for now -->
    </div>
  </div>
</template>

<script>
export default {
  name: 'HistoryPanel'
};
</script>
