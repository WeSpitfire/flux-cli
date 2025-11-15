<template>
  <div class="sidebar-panel" id="codebase-panel">
    <div class="sidebar-header">
      <h3>Codebase Explorer</h3>
      <button class="icon-btn" id="refresh-graph" title="Refresh Graph">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M14 2v4h-4M2 14v-4h4M2.5 7a6 6 0 0 1 11-3M13.5 9a6 6 0 0 1-11 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
    
    <div class="codebase-stats">
      <div class="stat-card">
        <div class="stat-value" id="total-files">-</div>
        <div class="stat-label">Files</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="total-entities">-</div>
        <div class="stat-label">Entities</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="context-tokens">-</div>
        <div class="stat-label">Tokens</div>
      </div>
    </div>

    <div class="explorer-section">
      <div class="section-header">🔥 Hot Files</div>
      <div class="section-content" id="hot-files-list">
        <div class="loading-text">Loading...</div>
      </div>
    </div>

    <div class="explorer-section">
      <div class="section-header">📦 Dependencies</div>
      <div class="section-content" id="dependencies-list">
        <div class="loading-text">Loading...</div>
      </div>
    </div>

    <div class="explorer-section">
      <div class="section-header">⚡ Key Entities</div>
      <div class="section-content" id="entities-list">
        <div class="loading-text">Loading...</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CodebasePanel'
};
</script>
