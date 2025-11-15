<template>
  <div class="terminal" ref="terminalContainer">
    <!-- Terminal content will be rendered here -->
  </div>
</template>

<script>
import { Terminal } from 'xterm';
import 'xterm/css/xterm.css';

export default {
  name: 'Terminal',
  data() {
    return {
      terminal: null,
    };
  },
  mounted() {
    this.initializeTerminal();
  },
  methods: {
    initializeTerminal() {
      this.terminal = new Terminal({
        cursorBlink: true,
        theme: {
          background: '#1e1e1e',
          foreground: '#dcdcdc',
        }
      });
      this.terminal.open(this.$refs.terminalContainer);
      this.terminal.write('Welcome to Flux CLI\r\n');
    },
  },
};
</script>

<style scoped>
.terminal {
  background-color: #1e1e1e;
  color: #dcdcdc;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', Courier, monospace;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  transition: background-color 0.3s ease, color 0.3s ease;
  height: 100%;
  width: 100%;
}
</style>
