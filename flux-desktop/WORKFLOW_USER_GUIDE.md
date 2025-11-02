# Flux Workflow System - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Workflow Basics](#workflow-basics)
4. [Creating Workflows](#creating-workflows)
5. [Running Workflows](#running-workflows)
6. [Managing Workflows](#managing-workflows)
7. [Advanced Features](#advanced-features)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

The Flux Workflow System is a powerful automation tool that lets you create, manage, and execute sequences of commands and actions. Think of workflows as programmable scripts with a beautiful UI, variable support, and error handling.

### Key Features
- ✅ **Visual Editor** - Create workflows without writing code
- ✅ **7 Step Types** - Command, confirm, input, select, conditional, parallel, success/error
- ✅ **Variable Substitution** - Use `{{variables}}` in commands
- ✅ **Import/Export** - Share workflows as JSON files
- ✅ **Auto-Save** - All workflows saved to localStorage
- ✅ **Real-Time Progress** - Watch workflows execute step-by-step
- ✅ **Keyboard Driven** - Power user shortcuts throughout

---

## Getting Started

### Opening the Workflow Manager

There are 3 ways to open the workflow manager:

1. **Keyboard Shortcut**: Press `Cmd+Shift+M` (Mac) or `Ctrl+Shift+M` (Windows/Linux)
2. **Button**: Click the "Open Workflow Library" button in the demo
3. **API**: Call `manager.showManager()` programmatically

### First Time Use

When you first open Flux, you'll see:
- 5 built-in example workflows (Git, Deploy, Docker, NPM, Database)
- Empty workflow library (if no workflows saved)
- Create your first workflow button

---

## Workflow Basics

### What is a Workflow?

A workflow is a sequence of steps that execute in order. Each step can be:
- **Command** - Run a shell command
- **Confirm** - Ask user for confirmation
- **Input** - Prompt user for text input
- **Select** - Let user choose from options
- **Conditional** - Execute steps based on condition
- **Parallel** - Run multiple steps at once
- **Success/Error** - Display messages at completion

### Workflow Structure

```json
{
  "name": "Workflow Name",
  "description": "What this workflow does",
  "tags": ["tag1", "tag2"],
  "author": "Your Name",
  "variables": [
    {
      "name": "environment",
      "description": "Deployment target",
      "type": "select",
      "options": ["staging", "production"],
      "default": "staging"
    }
  ],
  "steps": [
    {
      "type": "command",
      "name": "Build app",
      "command": "npm run build"
    },
    {
      "type": "confirm",
      "message": "Deploy to {{environment}}?",
      "default": true
    },
    {
      "type": "command",
      "name": "Deploy",
      "command": "deploy.sh {{environment}}"
    },
    {
      "type": "success",
      "message": "✅ Deployed successfully!"
    }
  ]
}
```

---

## Creating Workflows

### Using the Visual Editor

1. **Open the manager** (`Cmd+Shift+M`)
2. **Click "New Workflow"** button
3. **Fill in metadata**:
   - Name (required)
   - Description
   - Tags (comma-separated)
   - Author

4. **Add steps**:
   - Click "Add Step" button
   - Select step type from dropdown
   - Fill in step-specific fields
   - Repeat for each step

5. **Save** - Click "Save Workflow" button

### Step Types Explained

#### 1. Command Step
Executes a shell command.

**Fields:**
- Name (optional): Display name for the step
- Command (required): Shell command to run

**Example:**
```
Name: Install dependencies
Command: npm install
```

#### 2. Confirm Step
Asks user yes/no before continuing.

**Fields:**
- Message (required): Question to ask user

**Example:**
```
Message: Deploy to production?
```

#### 3. Input Step
Prompts user for text input.

**Fields:**
- Prompt (required): Question/label for input
- Variable (required): Variable name to store value

**Example:**
```
Prompt: Enter commit message:
Variable: commitMessage
```

Use in later steps: `git commit -m "{{commitMessage}}"`

#### 4. Select Step
Let user choose from dropdown.

**Fields:**
- Prompt (required): Question/label
- Options (required): Comma-separated choices
- Variable (required): Variable name

**Example:**
```
Prompt: Choose environment:
Options: dev, staging, production
Variable: env
```

#### 5. Conditional Step
Execute steps only if condition is true.

**Fields:**
- Condition (required): JavaScript expression
- Steps (required): Nested steps to run

**Example:**
```
Condition: {{environment}} == 'production'
Steps:
  - type: command
    command: npm audit
```

#### 6. Parallel Step
Run multiple commands simultaneously.

**Fields:**
- Steps (required): Array of steps to run in parallel

**Example:**
```
Steps:
  - type: command
    command: npm run lint
  - type: command
    command: npm test
```

#### 7. Success/Error Steps
Display messages at workflow completion.

**Fields:**
- Message (required): Text to show user

**Example:**
```
Success: ✅ Deployment complete!
Error: ❌ Deployment failed!
```

### Variable Substitution

Use `{{variableName}}` syntax to insert variables into:
- Commands
- Messages
- Prompts
- Conditions

**Built-in Variables:**
- `{{cwd}}` - Current working directory
- `{{user}}` - Current username
- `{{date}}` - Today's date (YYYY-MM-DD)
- `{{time}}` - Current time (HH:MM:SS)
- `{{timestamp}}` - Unix timestamp

**Custom Variables:**
Define in workflow metadata or collect via input/select steps.

---

## Running Workflows

### Method 1: Workflow Selector

1. Press `Cmd+Shift+W`
2. Search or browse workflows
3. Press `Enter` or click to run

### Method 2: Workflow Library

1. Press `Cmd+Shift+M` to open manager
2. Click any workflow card to run
3. Or use context menu → Run

### Method 3: Quick Run

From the library card context menu (⋮ button):
1. Click workflow card's ⋮ menu
2. Select "▶️ Run"

### Execution Flow

Once started:
1. **Variable Input** - If workflow has variables, form appears
2. **Progress Dialog** - Shows real-time step progress
3. **Step Execution** - Each step runs in sequence
4. **Confirmation Prompts** - For confirm/input/select steps
5. **Completion** - Success or error message displays

### Progress Indicators

During execution you'll see:
- **Progress Bar** - Shows % complete with gradient
- **Step List** - Each step with status icon:
  - ⏳ Running (blue, pulsing)
  - ✅ Success (green)
  - ❌ Error (red background)
  - ⏸️ Pending (orange)
- **Step Count** - "Step 3 of 7"
- **Cancel Button** - Stop anytime

### Canceling Workflows

- Click "Cancel" button in progress dialog
- Confirm cancellation
- Workflow stops immediately
- No rollback (steps already run stay run)

---

## Managing Workflows

### Library Browser

The workflow library shows all saved workflows in a grid:

**Card Contents:**
- Workflow name
- Description
- Tags (color-coded badges)
- Step count
- Author
- Context menu (⋮)

**Search & Filter:**
- **Search Box** - Filter by name/description
- **Sort Dropdown** - By name, steps, or recent
- **Tag Filter** - Show only workflows with specific tag

### Context Menu Actions

Click the ⋮ button on any workflow card:

1. **▶️ Run** - Execute workflow immediately
2. **✏️ Edit** - Open in visual editor
3. **📋 Duplicate** - Create a copy
4. **📤 Export** - Download as JSON file
5. **🗑️ Delete** - Remove workflow (with confirmation)

### Editing Workflows

1. Open context menu → Edit
2. Or create new → modify
3. Editor shows:
   - **Sidebar**: Metadata (name, description, tags, author)
   - **Main Panel**: Steps list with add/delete/reorder
4. Click "Save Workflow" when done

### Importing Workflows

**From JSON File:**
1. Open manager (`Cmd+Shift+M`)
2. Click "📥 Import" button
3. Select `.json` file
4. Workflow added to library

**From Text:**
1. Copy JSON workflow definition
2. Save as `.json` file
3. Import via button

### Exporting Workflows

**Single Workflow:**
1. Context menu → Export
2. Saves as `workflow-name.json`

**All Workflows:**
1. Use demo's "Export All" button
2. Or call `manager.saveToLocalStorage()`
3. Copy from localStorage manually

### Duplicating Workflows

1. Context menu → Duplicate
2. Opens editor with copy named "Name (Copy)"
3. Modify and save as new workflow

### Deleting Workflows

1. Context menu → Delete
2. Confirm deletion
3. Workflow removed from:
   - Engine registry
   - localStorage
   - UI immediately

---

## Advanced Features

### Conditional Execution

Use JavaScript expressions in conditional steps:

```json
{
  "type": "conditional",
  "condition": "{{env}} == 'production' && {{confirmed}} == true",
  "steps": [...]
}
```

**Supported Operators:**
- `==` Equal
- `!=` Not equal
- `<`, `>`, `<=`, `>=` Comparison
- `&&` And
- `||` Or
- `!` Not

### Parallel Execution

Run multiple commands simultaneously:

```json
{
  "type": "parallel",
  "steps": [
    { "type": "command", "command": "npm run build:css" },
    { "type": "command", "command": "npm run build:js" },
    { "type": "command", "command": "npm run build:images" }
  ]
}
```

**Use Cases:**
- Linting + testing
- Multi-target builds
- Parallel API calls
- Independent operations

### Error Handling

Each command step can have:

```json
{
  "type": "command",
  "command": "npm test",
  "continueOnError": false
}
```

- `false` (default): Stop workflow on error
- `true`: Continue to next step even if fails

### Step Timeouts

```json
{
  "type": "command",
  "command": "npm test",
  "timeout": 300000
}
```

Timeout in milliseconds (5 minutes = 300000ms)

### Success/Error Messages

Always end workflows with status messages:

```json
{
  "steps": [
    /* ... */,
    {
      "type": "success",
      "message": "🎉 All done! Check output above."
    },
    {
      "type": "error",
      "message": "❌ Something went wrong. Check logs."
    }
  ]
}
```

---

## Keyboard Shortcuts

### Global Shortcuts
- `Cmd/Ctrl + Shift + M` - Open workflow manager
- `Cmd/Ctrl + Shift + W` - Open workflow selector
- `Esc` - Close any dialog

### In Workflow Selector
- `↑` / `↓` - Navigate workflow list
- `Enter` - Run selected workflow
- `Type to search` - Filter workflows

### In Workflow Editor
- `Tab` - Navigate form fields
- `Cmd/Ctrl + S` - Save workflow (if implemented)
- `Cmd/Ctrl + Enter` - Save and close

### In Progress Dialog
- `Esc` - Cancel workflow (with confirmation)

---

## Troubleshooting

### Workflow Won't Run

**Problem**: Click run but nothing happens

**Solutions:**
1. Check browser console for errors (F12)
2. Verify workflow has at least one step
3. Check if workflow is properly registered
4. Try re-importing the workflow

### Variables Not Substituting

**Problem**: `{{variable}}` shows literally in output

**Solutions:**
1. Ensure variable is defined in metadata or input step
2. Check spelling matches exactly (case-sensitive)
3. Verify variable was set before use
4. Check quotes: `"{{var}}"` not `'{{var}}'`

### Step Always Failing

**Problem**: Step shows ❌ immediately

**Solutions:**
1. Check command syntax
2. Verify command exists in PATH
3. Test command in terminal first
4. Check file permissions
5. Look for typos in command

### Can't Save Workflow

**Problem**: "Save Workflow" button does nothing

**Solutions:**
1. Ensure workflow name is filled in (required)
2. Check all required step fields are complete
3. Try refreshing page
4. Check localStorage quota (Settings → Clear Site Data)

### Workflows Not Persisting

**Problem**: Workflows disappear after page reload

**Solutions:**
1. Check if localStorage is enabled
2. Verify no browser extensions blocking storage
3. Check browser's private/incognito mode (doesn't persist)
4. Export workflows as backup
5. Try different browser

### Progress Dialog Stuck

**Problem**: Workflow executing but UI frozen

**Solutions:**
1. Wait for long-running command to complete
2. Check if command is interactive (shouldn't be)
3. Set timeout on problematic steps
4. Cancel and restart workflow
5. Check system resources

### Import Fails

**Problem**: JSON import shows "Invalid workflow file"

**Solutions:**
1. Validate JSON syntax (use jsonlint.com)
2. Check required fields: `name`, `steps`
3. Verify step types are valid
4. Check for extra commas/quotes
5. Use export from working workflow as template

---

## Best Practices

### Naming Workflows
- ✅ "Deploy to Production"
- ✅ "Git Commit & Push"
- ❌ "workflow1"
- ❌ "test"

Use descriptive, action-oriented names.

### Writing Descriptions
- Explain what the workflow does
- List any prerequisites
- Note any side effects
- Mention required permissions

**Example:**
```
"description": "Builds and deploys app to production. 
Requires: AWS credentials, production access.
Side effects: Triggers rollout, notifies team."
```

### Using Tags
- Use consistent naming
- Keep tags short
- Tag by: purpose, tech, team, environment

**Good Tags:**
- `git`, `deploy`, `docker`, `ci/cd`, `backup`
- `frontend`, `backend`, `devops`
- `quick`, `long-running`, `interactive`

### Organizing Steps
1. **Setup** - Install, configure, prepare
2. **Build** - Compile, bundle, optimize
3. **Test** - Run tests, lint, audit
4. **Confirm** - Get user approval for risky operations
5. **Execute** - Deploy, publish, migrate
6. **Verify** - Health checks, smoke tests
7. **Notify** - Success/error messages

### Variable Naming
- Use camelCase: `commitMessage`, `envName`
- Be descriptive: `targetBranch` not `branch`
- Avoid conflicts with built-ins: don't use `date`, `user`

### Error Messages
Make error messages actionable:

✅ **Good:**
```
"❌ Deployment failed. Check that:
1. AWS credentials are set
2. Target environment exists
3. Build succeeded
Then try again."
```

❌ **Bad:**
```
"Error occurred"
```

---

## Examples

### Simple Git Workflow

```json
{
  "name": "Quick Git Push",
  "description": "Add, commit, and push in one go",
  "tags": ["git", "quick"],
  "steps": [
    {
      "type": "command",
      "name": "Stage changes",
      "command": "git add ."
    },
    {
      "type": "input",
      "prompt": "Commit message:",
      "variable": "message",
      "required": true
    },
    {
      "type": "command",
      "name": "Commit",
      "command": "git commit -m '{{message}}'"
    },
    {
      "type": "command",
      "name": "Push",
      "command": "git push"
    },
    {
      "type": "success",
      "message": "✅ Pushed to remote!"
    }
  ]
}
```

### CI/CD Pipeline

```json
{
  "name": "Full CI/CD",
  "description": "Complete build, test, and deploy pipeline",
  "tags": ["ci/cd", "deploy", "production"],
  "variables": [
    {
      "name": "environment",
      "type": "select",
      "options": ["staging", "production"],
      "default": "staging"
    }
  ],
  "steps": [
    {
      "type": "command",
      "name": "Install deps",
      "command": "npm ci"
    },
    {
      "type": "parallel",
      "steps": [
        { "type": "command", "command": "npm run lint" },
        { "type": "command", "command": "npm test" }
      ]
    },
    {
      "type": "command",
      "name": "Build",
      "command": "npm run build"
    },
    {
      "type": "conditional",
      "condition": "{{environment}} == 'production'",
      "steps": [
        {
          "type": "confirm",
          "message": "⚠️ Deploy to PRODUCTION?",
          "default": false
        }
      ]
    },
    {
      "type": "command",
      "name": "Deploy",
      "command": "./deploy.sh {{environment}}"
    },
    {
      "type": "command",
      "name": "Health check",
      "command": "curl https://{{environment}}.myapp.com/health"
    },
    {
      "type": "success",
      "message": "🎉 Deployed to {{environment}}!"
    }
  ]
}
```

### Database Migration

```json
{
  "name": "Database Migration",
  "description": "Safely migrate database with backup",
  "tags": ["database", "migration", "backup"],
  "variables": [
    {
      "name": "direction",
      "type": "select",
      "options": ["up", "down"],
      "default": "up"
    }
  ],
  "steps": [
    {
      "type": "command",
      "name": "Backup database",
      "command": "pg_dump mydb > backup_{{timestamp}}.sql"
    },
    {
      "type": "confirm",
      "message": "Run migration {{direction}}?",
      "default": true
    },
    {
      "type": "command",
      "name": "Run migration",
      "command": "npm run migrate:{{direction}}",
      "timeout": 300000
    },
    {
      "type": "command",
      "name": "Verify",
      "command": "npm run migrate:status"
    },
    {
      "type": "success",
      "message": "✅ Migration complete! Backup saved."
    },
    {
      "type": "error",
      "message": "❌ Migration failed. Restore with: psql mydb < backup_{{timestamp}}.sql"
    }
  ]
}
```

---

## Tips & Tricks

### 1. Test Commands First
Always test commands in terminal before adding to workflow.

### 2. Use Descriptive Step Names
Helps when watching progress and debugging.

### 3. Add Confirmations for Risky Operations
`rm -rf`, `DROP TABLE`, `deploy production` should always confirm.

### 4. Use Tags Generously
Makes searching and filtering easier.

### 5. Export Frequently
Backup your workflows regularly.

### 6. Version Your Workflows
Add version in name or description: "Deploy v2.0"

### 7. Document Prerequisites
In description, list what needs to be installed/configured.

### 8. Use Variables for Reusability
Don't hardcode paths, environments, names - use variables.

### 9. Group Related Workflows
Use consistent tag naming: `deploy:staging`, `deploy:prod`

### 10. Share with Team
Export workflows and check into git repo for team access.

---

## Support & Feedback

### Getting Help
- Check this guide first
- Review example workflows
- Run test suite (`test-workflow-system.html`)
- Check browser console for errors

### Reporting Bugs
Include:
1. Workflow JSON
2. Steps to reproduce
3. Expected vs actual behavior
4. Browser/OS version
5. Console errors

### Feature Requests
We're always improving! Suggest:
- New step types
- UI improvements
- Integration ideas
- Automation scenarios

---

## What's Next?

Now that you know the basics:

1. **Try the Examples** - Run built-in workflows
2. **Create Your First Workflow** - Start simple
3. **Explore Advanced Features** - Conditionals, parallel steps
4. **Share with Team** - Export and distribute
5. **Automate Everything** - Find repetitive tasks to automate

Happy automating! 🚀
