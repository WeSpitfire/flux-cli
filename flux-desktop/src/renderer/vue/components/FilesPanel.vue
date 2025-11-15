<template>
  <div class="sidebar-panel" id="files-panel">
    <div class="sidebar-header">
      <h3>Working Directory</h3>
      <div style="display: flex; gap: 4px;">
        <button class="icon-btn" @click="manualRefresh" title="Refresh (Debug)">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M14 2v4h-4M2 14v-4h4M2.5 7a6 6 0 0 1 11-3M13.5 9a6 6 0 0 1-11 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
        <button class="icon-btn" @click="changeDirectory" title="Select Directory">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 2h5l2 2h5v9H2V2z" stroke="currentColor" stroke-width="1.5"/>
            <path d="M6 9l2-2 2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>
    <div class="current-directory" id="current-directory">
      <div class="directory-path" id="directory-path">Loading...</div>
    </div>
    <div class="file-tree" id="file-tree-container">
      <!-- File tree will be populated by vanilla JS for now -->
    </div>
  </div>
</template>

<script>
export default {
  name: 'FilesPanel',
  methods: {
    async manualRefresh() {
      console.log('[FilesPanel] Manual refresh clicked');
      console.log('[FilesPanel] window.fileSystem:', window.fileSystem);
      
      if (!window.fileSystem) {
        alert('fileSystem API not available!');
        return;
      }
      
      try {
        const cwd = await window.fileSystem.getCwd();
        console.log('[FilesPanel] Got CWD:', cwd);
        
        const dirPathEl = document.getElementById('directory-path');
        if (dirPathEl) {
          dirPathEl.textContent = cwd;
        }
        
        const files = await window.fileSystem.readDir(cwd);
        console.log('[FilesPanel] Got files:', files);
        alert(`Found ${files.length} files in ${cwd}`);
      } catch (err) {
        console.error('[FilesPanel] Error:', err);
        alert('Error: ' + err.message);
      }
    },
    
    async changeDirectory() {
      console.log('[FilesPanel] Change directory clicked');
      
      if (!window.fileSystem) {
        alert('fileSystem API not available!');
        return;
      }
      
      try {
        const newDir = await window.fileSystem.selectDirectory();
        console.log('[FilesPanel] Selected directory:', newDir);
        
        if (newDir) {
          // Clear and reload file tree
          const fileTreeContainer = document.getElementById('file-tree-container');
          const dirPathEl = document.getElementById('directory-path');
          
          if (fileTreeContainer && dirPathEl) {
            fileTreeContainer.innerHTML = '';
            dirPathEl.textContent = newDir;
            
            // Reload file explorer with new directory
            if (window.loadDirectory) {
              await window.loadDirectory(newDir, fileTreeContainer);
              console.log('[FilesPanel] Directory changed successfully');
            } else {
              console.error('[FilesPanel] window.loadDirectory not available');
            }
          }
        }
      } catch (err) {
        console.error('[FilesPanel] Error changing directory:', err);
        alert('Error: ' + err.message);
      }
    }
  }
};
</script>
