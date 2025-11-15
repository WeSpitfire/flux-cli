<template>
  <aside class="sidebar" id="sidebar">
    <!-- Tabs -->
    <div class="sidebar-tabs">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        class="sidebar-tab" 
        :class="{ active: activeTab === tab.id }"
        :data-tab="tab.id"
        @click="switchTab(tab.id)"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path :d="tab.icon" stroke="currentColor" stroke-width="1.5" :stroke-linecap="tab.id === 'history' ? 'round' : undefined" />
          <template v-if="tab.id === 'codebase'">
            <circle cx="12" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="4" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="12" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/>
          </template>
        </svg>
        {{ tab.label }}
      </button>
    </div>

    <!-- Panels -->
    <HistoryPanel :class="{ active: activeTab === 'history' }" />
    <FilesPanel :class="{ active: activeTab === 'files' }" />
    <CodebasePanel :class="{ active: activeTab === 'codebase' }" />
  </aside>
</template>

<script>
import { ref } from 'vue';
import HistoryPanel from './HistoryPanel.vue';
import FilesPanel from './FilesPanel.vue';
import CodebasePanel from './CodebasePanel.vue';

export default {
  name: 'Sidebar',
  components: {
    HistoryPanel,
    FilesPanel,
    CodebasePanel
  },
  setup() {
    const activeTab = ref('history');
    
    const tabs = [
      {
        id: 'history',
        label: 'History',
        icon: 'M8 2v6l4 2M14 8A6 6 0 112 8a6 6 0 0112 0z'
      },
      {
        id: 'files',
        label: 'Files',
        icon: 'M2 2h5l2 2h5v9H2V2z'
      },
      {
        id: 'codebase',
        label: 'Explorer',
        icon: 'M6 4h4M4 6v4M12 6v4M6 12h4'
      }
    ];
    
    const switchTab = (tabId) => {
      console.log('[Sidebar] Switching to tab:', tabId);
      activeTab.value = tabId;
    };
    
    return {
      activeTab,
      tabs,
      switchTab
    };
  }
};
</script>

<style scoped>
/* Component uses global styles from styles.css */
</style>
