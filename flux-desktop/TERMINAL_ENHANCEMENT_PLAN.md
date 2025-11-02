# Terminal Enhancement Plan

## Philosophy

**Flux is a terminal-first AI coding assistant, not a chat app.**

The terminal IS the interface. Everything important happens there:
- Commands are executed
- Output is displayed  
- File operations shown
- Code changes previewed
- Status updates appear

Instead of replacing the terminal with chat bubbles, we **enhance the terminal** to make it more powerful, beautiful, and interactive while keeping it as the core experience.

---

## Core Principles

1. **Terminal First** - Never hide or minimize the terminal
2. **Rich Content** - Format markdown, code, links beautifully IN the terminal
3. **Smart Interactions** - Hover actions, inline buttons, clickable elements
4. **Visual Hierarchy** - Clear distinction between user input and AI output
5. **Modern Aesthetics** - Beautiful but functional design
6. **Performance** - Fast, smooth, responsive

---

## Phase 1: Visual Enhancement

### 1.1 Terminal Output Styling

**User Commands**
```
$ create a hello world function in Python
  ↑ Bold, accent color, clear visual marker
```

**Flux Responses**
```
╭─ Flux ─────────────────────────────────╮
│ I'll create a hello world function...  │
│                                         │
│ def hello_world():                      │
│     print("Hello, World!")              │
╰─────────────────────────────────────────╯
  ↑ Subtle background, rounded corners, icon
```

**Section Separators**
```
─────────────────────────────────────────
  ↑ Between different commands/responses
```

### 1.2 Status Indicators

**Inline Status Badges** (appear in terminal)
- 🔍 **Analyzing** - "Reading your codebase..."
- 🤔 **Thinking** - "Planning the changes..."
- ✏️ **Writing** - "Generating code..."
- 🧪 **Testing** - "Running tests..."
- ✅ **Done** - "Complete!"
- ❌ **Error** - "Something went wrong"

**Progress Indicators**
```
▓▓▓▓▓▓░░░░ 60% Analyzing files...
```

### 1.3 Enhanced Color Scheme

```css
/* User commands */
--user-command-color: #7aa2f7; /* Bright blue */
--user-prompt-symbol: #bb9af7; /* Purple $ symbol */

/* Flux responses */
--flux-bg: rgba(28, 33, 40, 0.5); /* Subtle background */
--flux-border: #30363d;
--flux-accent: #7dcfff; /* Cyan */

/* Status badges */
--status-analyzing: #e0af68; /* Yellow */
--status-writing: #9ece6a; /* Green */
--status-error: #f7768e; /* Red */
--status-success: #73daca; /* Teal */

/* Syntax highlighting */
--syntax-keyword: #c678dd; /* Purple */
--syntax-string: #98c379; /* Green */
--syntax-function: #61afef; /* Blue */
--syntax-comment: #5c6370; /* Gray */
```

---

## Phase 2: Rich Content Rendering

### 2.1 Markdown in Terminal

Detect and format markdown in Flux output:

**Headers**
```
# Big Header     →  ═══ BIG HEADER ═══
## Medium Header →  ─── Medium Header ───
```

**Emphasis**
```
**bold text**    →  𝐛𝐨𝐥𝐝 𝐭𝐞𝐱𝐭
*italic text*    →  𝘪𝘵𝘢𝘭𝘪𝘤 𝘵𝘦𝘹𝘵
`inline code`    →  [inline code] (with background)
```

**Lists**
```
* Item 1         →  • Item 1
* Item 2         →  • Item 2
```

### 2.2 Code Blocks in Terminal

Beautiful syntax-highlighted code blocks:

```
╭─ Python ─────────────────── [Copy] ─╮
│ def hello_world():                   │
│     """Greet the world"""            │
│     print("Hello, World!")           │
│                                      │
│     return True                      │
╰──────────────────────────────────────╯
```

Features:
- Language label
- Syntax highlighting
- Copy button (appears on hover)
- Line numbers (optional)
- Diff highlighting for changes

### 2.3 Interactive Elements

**Clickable File Paths**
```
src/main.py    ← Click to open in editor
        ↑ Underline on hover, cursor pointer
```

**Clickable Links**
```
https://docs.python.org  ← Opens in browser
```

**Collapsible Sections**
```
▼ Long output (250 lines) [Click to expand]
  ↓
▲ Long output
  [... 250 lines of content ...]
```

---

## Phase 3: Enhanced Input Area

### 3.1 Visual Improvements

**Current:**
```
┌─────────────────────────────────┐
│ $ [                          ] →│
└─────────────────────────────────┘
```

**Enhanced:**
```
╭─────────────────────────────────────╮
│ $ Ask Flux anything...              │
│                                     │
│   📎 Attach   ⌘K Commands   ↵ Send │
╰─────────────────────────────────────╯
```

### 3.2 Features

- **Auto-expanding** - Grows as you type (multi-line)
- **Syntax highlighting** - Color code as you type
- **Command suggestions** - Dropdown with recent commands
- **File attachment** - Drag & drop or click to attach
- **Keyboard shortcuts** - Visual indicators
- **Smart placeholder** - Changes based on context

---

## Phase 4: Smart Interactions

### 4.1 Hover Actions

**File Paths**
```
src/main.py
    ↓ (on hover)
╭─ main.py ─────────────────╮
│ def main():               │
│     app.run()             │
│ ...                       │
│ [Open] [Copy Path]        │
╰───────────────────────────╯
```

**Code Blocks**
```
Code Block
    ↓ (on hover)
[Copy] [Apply] [Explain]
```

### 4.2 Context Menu

Right-click in terminal:
```
╭─────────────────────╮
│ Copy                │
│ Copy as Markdown    │
│ ─────────────       │
│ Clear Terminal      │
│ Export History      │
│ ─────────────       │
│ Regenerate Response │
╰─────────────────────╯
```

---

## Phase 5: Modern Aesthetics

### 5.1 Glassmorphism

**Overlay elements** (command palette, dialogs):
```css
background: rgba(13, 17, 23, 0.8);
backdrop-filter: blur(20px);
border: 1px solid rgba(255, 255, 255, 0.1);
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
```

### 5.2 Smooth Animations

- **Fade in** - New terminal output
- **Slide in** - Status indicators
- **Pulse** - Thinking indicator
- **Ripple** - Button clicks
- **Smooth scroll** - Auto-scroll to new content

### 5.3 Typography

```css
/* Terminal font */
font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
font-size: 14px;
line-height: 1.6;
letter-spacing: 0.2px;

/* UI text */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI';
```

### 5.4 Micro-interactions

- Buttons scale slightly on hover
- Subtle glow on focus
- Smooth transitions (200ms)
- Loading spinners
- Success checkmarks

---

## Implementation Strategy

### Step 1: Terminal Output Wrapper (Week 1)
- Create a layer that intercepts xterm output
- Parse and format before displaying
- Detect markdown, code blocks, file paths
- Apply syntax highlighting

### Step 2: Visual Enhancements (Week 1-2)
- Update color scheme
- Add status indicators
- Style user commands vs AI output
- Add section separators

### Step 3: Interactive Elements (Week 2)
- Make file paths clickable
- Add hover tooltips
- Copy buttons on code blocks
- Collapsible sections

### Step 4: Input Area Upgrade (Week 2-3)
- Auto-expanding textarea
- Command suggestions
- File attachment UI
- Better styling

### Step 5: Polish & Animations (Week 3)
- Glassmorphism effects
- Smooth animations
- Micro-interactions
- Performance optimization

---

## Technical Approach

### Rich Terminal Output

Instead of plain xterm, create a hybrid:

```
┌─────────────────────────────────────┐
│  Formatted Output Area              │  ← Parsed & formatted
│  (HTML/React components)            │     (markdown, code blocks)
│                                     │
│  ─────────────────────────────     │
│                                     │
│  Raw Terminal (xterm.js)            │  ← Fallback for raw output
│  (hidden or minimal)                │
└─────────────────────────────────────┘
```

**OR** enhance xterm with overlays:

```
┌─────────────────────────────────────┐
│  xterm.js Terminal                  │
│  ┌─────────────────┐                │
│  │ Overlay: Button │ ← Hover actions│
│  └─────────────────┘                │
└─────────────────────────────────────┘
```

### Key Libraries

- **xterm.js** - Terminal emulator (already using)
- **xterm-addon-webgl** - GPU-accelerated rendering
- **marked** or **markdown-it** - Markdown parsing
- **prism.js** or **shiki** - Syntax highlighting
- **framer-motion** - Smooth animations (optional)

---

## Success Metrics

**Visual Quality**
- [ ] Clear distinction between user/AI
- [ ] Beautiful code blocks with highlighting
- [ ] Smooth animations throughout
- [ ] Modern, polished look

**Functionality**
- [ ] Clickable file paths work
- [ ] Copy buttons on code blocks
- [ ] Status indicators show context
- [ ] Input area auto-expands

**Performance**
- [ ] No lag with large outputs
- [ ] Smooth scrolling
- [ ] Fast rendering
- [ ] Efficient memory usage

**User Experience**
- [ ] Intuitive interactions
- [ ] Helpful hover actions
- [ ] Better visual hierarchy
- [ ] Feels modern and fast

---

## Inspiration

Take the best from:
- **Warp** - Command blocks, workflow cards
- **Fig** - Autocomplete, contextual help
- **Hyper** - Beautiful terminal design
- **iTerm2** - Powerful features, polish
- **GitHub Copilot** - Inline suggestions

But keep Flux unique:
- AI-first, not just a terminal
- Rich content rendering
- Smart interactions
- Beautiful but functional

---

## Next Steps

1. Review and approve this plan
2. Start with Step 1: Output parsing layer
3. Implement visual enhancements
4. Add interactive elements
5. Polish and refine

**Goal: Make Flux the most beautiful and powerful AI coding terminal in existence.**
