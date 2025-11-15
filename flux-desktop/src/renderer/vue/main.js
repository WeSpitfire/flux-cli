import { createApp } from 'vue';
import App from './App.vue';
import { initializeXterm } from './composables/useXterm.js';

// Initialize xterm and expose to window for vanilla JS
initializeXterm();

const app = createApp(App);

app.mount('#app');
