# Workflow System Architecture

## Overview

Workflows are reusable sequences of commands and actions that automate repetitive developer tasks.

## Workflow Schema (YAML)

```yaml
name: "Deploy to Production"
description: "Build, test, and deploy application to production"
version: "1.0.0"
author: "Flux Team"
tags: ["deploy", "production", "ci/cd"]

# Variables that can be customized
variables:
  - name: "branch"
    description: "Git branch to deploy"
    default: "main"
    type: "string"
  
  - name: "environment"
    description: "Deployment environment"
    default: "production"
    type: "select"
    options: ["staging", "production"]

# Workflow steps
steps:
  - type: "command"
    name: "Pull latest code"
    command: "git pull origin {{branch}}"
    
  - type: "command"
    name: "Install dependencies"
    command: "npm install"
    
  - type: "command"
    name: "Run tests"
    command: "npm test"
    continueOnError: false
    
  - type: "confirm"
    name: "Confirm deployment"
    message: "Deploy to {{environment}}?"
    default: true
    
  - type: "command"
    name: "Build application"
    command: "npm run build"
    
  - type: "command"
    name: "Deploy"
    command: "npm run deploy:{{environment}}"
    
  - type: "success"
    message: "🎉 Deployment to {{environment}} complete!"
```

## Step Types

### 1. Command Step
Executes a shell command.

```yaml
- type: "command"
  name: "Build project"
  command: "npm run build"
  continueOnError: false  # Stop workflow if fails
  timeout: 300000         # 5 minute timeout (optional)
```

### 2. Confirm Step
Asks user for confirmation before continuing.

```yaml
- type: "confirm"
  name: "Confirm action"
  message: "Are you sure you want to proceed?"
  default: true           # Default selection
```

### 3. Input Step
Prompts user for input value.

```yaml
- type: "input"
  name: "Get commit message"
  prompt: "Enter commit message:"
  variable: "commitMessage"  # Stores in {{commitMessage}}
  required: true
```

### 4. Select Step
Prompts user to select from options.

```yaml
- type: "select"
  name: "Choose environment"
  prompt: "Select deployment environment:"
  options: ["development", "staging", "production"]
  variable: "env"
```

### 5. Conditional Step
Execute steps based on condition.

```yaml
- type: "conditional"
  name: "Production checks"
  condition: "{{environment}} == 'production'"
  steps:
    - type: "command"
      name: "Extra security scan"
      command: "npm audit"
```

### 6. Parallel Step
Execute multiple commands in parallel.

```yaml
- type: "parallel"
  name: "Run linting and tests"
  steps:
    - type: "command"
      command: "npm run lint"
    - type: "command"
      command: "npm test"
```

### 7. Success/Error Steps
Show messages on completion.

```yaml
- type: "success"
  message: "✅ Workflow completed successfully!"

- type: "error"
  message: "❌ Workflow failed. Check logs above."
```

## Variable Substitution

Variables use `{{variableName}}` syntax:

```yaml
command: "git checkout {{branch}}"
message: "Deploying to {{environment}}"
```

Built-in variables:
- `{{cwd}}` - Current working directory
- `{{user}}` - Current user
- `{{date}}` - Current date (YYYY-MM-DD)
- `{{time}}` - Current time (HH:MM:SS)
- `{{timestamp}}` - Unix timestamp

## Workflow Executor

```javascript
class WorkflowExecutor {
  constructor(workflow, variables = {}) {
    this.workflow = workflow;
    this.variables = { ...workflow.defaults, ...variables };
    this.currentStep = 0;
    this.status = 'pending'; // pending, running, completed, failed, cancelled
    this.results = [];
  }
  
  async execute() {
    this.status = 'running';
    
    for (let i = 0; i < this.workflow.steps.length; i++) {
      this.currentStep = i;
      const step = this.workflow.steps[i];
      
      try {
        const result = await this.executeStep(step);
        this.results.push({ step, result, status: 'success' });
        
        // Emit progress event
        this.emit('progress', {
          step: i + 1,
          total: this.workflow.steps.length,
          stepName: step.name
        });
        
      } catch (error) {
        this.results.push({ step, error, status: 'failed' });
        
        if (!step.continueOnError) {
          this.status = 'failed';
          throw error;
        }
      }
    }
    
    this.status = 'completed';
    return this.results;
  }
  
  async executeStep(step) {
    // Replace variables in step
    const resolved = this.resolveVariables(step);
    
    switch (step.type) {
      case 'command':
        return await this.executeCommand(resolved);
      case 'confirm':
        return await this.executeConfirm(resolved);
      case 'input':
        return await this.executeInput(resolved);
      // ... etc
    }
  }
  
  resolveVariables(obj) {
    // Replace {{var}} with actual values
    const str = JSON.stringify(obj);
    const resolved = str.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
      return this.variables[varName] || match;
    });
    return JSON.parse(resolved);
  }
}
```

## Built-in Workflows

### 1. Git Commit & Push
```yaml
name: "Git Commit & Push"
steps:
  - type: "command"
    command: "git add ."
  - type: "input"
    prompt: "Commit message:"
    variable: "message"
  - type: "command"
    command: "git commit -m '{{message}}'"
  - type: "command"
    command: "git push"
```

### 2. Deploy to Staging
```yaml
name: "Deploy to Staging"
steps:
  - type: "command"
    command: "npm run build"
  - type: "command"
    command: "npm test"
  - type: "confirm"
    message: "Deploy to staging?"
  - type: "command"
    command: "npm run deploy:staging"
```

### 3. Docker Cleanup
```yaml
name: "Docker Cleanup"
steps:
  - type: "command"
    command: "docker system prune -f"
  - type: "command"
    command: "docker volume prune -f"
  - type: "success"
    message: "Docker cleanup complete!"
```

### 4. Database Migration
```yaml
name: "Database Migration"
steps:
  - type: "select"
    prompt: "Migration direction:"
    options: ["up", "down"]
    variable: "direction"
  - type: "command"
    command: "npm run migrate:{{direction}}"
  - type: "command"
    command: "npm run db:seed"
```

### 5. NPM Publish
```yaml
name: "NPM Publish"
steps:
  - type: "input"
    prompt: "Version (major/minor/patch):"
    variable: "version"
    default: "patch"
  - type: "command"
    command: "npm version {{version}}"
  - type: "command"
    command: "npm test"
  - type: "command"
    command: "npm run build"
  - type: "confirm"
    message: "Publish to npm?"
  - type: "command"
    command: "npm publish"
```

## UI Components

### Workflow Selector
- Grid of workflow cards
- Search and filter by tags
- Recently used workflows
- Custom workflows section

### Workflow Execution
- Step-by-step progress bar
- Real-time output display
- Current step highlighted
- Pause/Resume/Cancel buttons

### Workflow Editor
- YAML editor with syntax highlighting
- Live preview
- Variable editor
- Step templates

## File Storage

Workflows stored in:
```
~/.flux/workflows/
  ├── built-in/
  │   ├── git-commit-push.yml
  │   ├── deploy-staging.yml
  │   └── docker-cleanup.yml
  ├── custom/
  │   ├── my-workflow.yml
  │   └── team-deploy.yml
  └── history/
      └── 2025-11-02-deploy.log
```

## Events

```javascript
workflow.on('start', (workflow) => {});
workflow.on('progress', ({ step, total, stepName }) => {});
workflow.on('step-start', (step) => {});
workflow.on('step-complete', (step, result) => {});
workflow.on('step-failed', (step, error) => {});
workflow.on('complete', (results) => {});
workflow.on('failed', (error) => {});
workflow.on('cancelled', () => {});
```

## Error Handling

1. **Step Failure**: 
   - If `continueOnError: false` (default), stop workflow
   - If `continueOnError: true`, log error and continue

2. **Timeout**:
   - If step exceeds timeout, kill process
   - Mark step as failed
   - Continue based on `continueOnError`

3. **User Cancellation**:
   - Stop current step
   - Run cleanup steps if defined
   - Mark workflow as cancelled

4. **Rollback**:
   - Optional `rollback` steps for each step
   - Execute in reverse order on failure

```yaml
- type: "command"
  command: "kubectl apply -f deployment.yml"
  rollback: "kubectl rollback deployment"
```

## Why This Beats Warp

| Feature | Warp Blocks | Flux Workflows |
|---------|-------------|----------------|
| YAML Definition | ❌ | ✅ |
| Variable Substitution | ❌ | ✅ {{var}} |
| Conditional Steps | ❌ | ✅ |
| Parallel Execution | ❌ | ✅ |
| Error Recovery | ❌ | ✅ Rollback |
| Built-in Templates | Few | ✅ 10+ |
| Custom Workflows | Basic | ✅ Full editor |
| Sharing | ❌ | ✅ Import/Export |
| History | ❌ | ✅ Logs |

## Implementation Plan

**Day 11**: Architecture & Schema ✅  
**Day 12**: Workflow Engine Core  
**Day 13**: UI Components  
**Day 14**: Built-in Templates  
**Day 15**: Management UI  
**Day 16**: Polish & Testing  
**Day 17**: Documentation & Demo  

---

**Next**: Start building the workflow engine core!
