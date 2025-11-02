// Workflow Engine
// Parses YAML workflows and executes them step-by-step

class WorkflowEngine {
  constructor() {
    this.workflows = new Map();
    this.currentExecution = null;
    this.eventListeners = new Map();
  }
  
  /**
   * Parse YAML workflow to JavaScript object
   * Note: In production, use js-yaml library. For now, we'll use JSON-like objects.
   */
  parseWorkflow(yamlString) {
    try {
      // For MVP, we'll use JSON format instead of YAML
      // In production: const workflow = jsyaml.load(yamlString);
      const workflow = typeof yamlString === 'string' ? JSON.parse(yamlString) : yamlString;
      
      // Validate workflow structure
      this.validateWorkflow(workflow);
      
      return workflow;
    } catch (error) {
      throw new Error(`Workflow parse error: ${error.message}`);
    }
  }
  
  /**
   * Validate workflow structure
   */
  validateWorkflow(workflow) {
    if (!workflow.name) {
      throw new Error('Workflow must have a name');
    }
    
    if (!workflow.steps || !Array.isArray(workflow.steps) || workflow.steps.length === 0) {
      throw new Error('Workflow must have at least one step');
    }
    
    // Validate each step
    workflow.steps.forEach((step, index) => {
      if (!step.type) {
        throw new Error(`Step ${index + 1} missing type`);
      }
      
      // Type-specific validation
      if (step.type === 'command' && !step.command) {
        throw new Error(`Command step ${index + 1} missing command`);
      }
      
      if (step.type === 'input' && !step.variable) {
        throw new Error(`Input step ${index + 1} missing variable name`);
      }
    });
    
    return true;
  }
  
  /**
   * Register a workflow
   */
  registerWorkflow(workflow) {
    const parsed = this.parseWorkflow(workflow);
    this.workflows.set(parsed.name, parsed);
    return parsed;
  }
  
  /**
   * Get workflow by name
   */
  getWorkflow(name) {
    return this.workflows.get(name);
  }
  
  /**
   * List all workflows
   */
  listWorkflows() {
    return Array.from(this.workflows.values());
  }
  
  /**
   * Execute a workflow
   */
  async executeWorkflow(workflowName, variables = {}) {
    const workflow = this.getWorkflow(workflowName);
    if (!workflow) {
      throw new Error(`Workflow "${workflowName}" not found`);
    }
    
    const executor = new WorkflowExecutor(workflow, variables);
    this.currentExecution = executor;
    
    // Forward events
    executor.on('*', (event, data) => {
      this.emit(event, data);
    });
    
    try {
      const results = await executor.execute();
      this.currentExecution = null;
      return results;
    } catch (error) {
      this.currentExecution = null;
      throw error;
    }
  }
  
  /**
   * Cancel current execution
   */
  cancelExecution() {
    if (this.currentExecution) {
      this.currentExecution.cancel();
    }
  }
  
  /**
   * Event emitter methods
   */
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);
  }
  
  emit(event, data) {
    const listeners = this.eventListeners.get(event) || [];
    listeners.forEach(callback => callback(data));
    
    // Also emit to wildcard listeners
    const wildcardListeners = this.eventListeners.get('*') || [];
    wildcardListeners.forEach(callback => callback(event, data));
  }
}

class WorkflowExecutor {
  constructor(workflow, variables = {}) {
    this.workflow = workflow;
    this.variables = this.buildVariables(workflow, variables);
    this.currentStep = 0;
    this.status = 'pending';
    this.results = [];
    this.cancelled = false;
    this.eventListeners = new Map();
  }
  
  /**
   * Build variables with defaults and built-ins
   */
  buildVariables(workflow, userVariables) {
    const vars = {};
    
    // Add workflow defaults
    if (workflow.variables) {
      workflow.variables.forEach(varDef => {
        vars[varDef.name] = varDef.default || '';
      });
    }
    
    // Add user-provided variables
    Object.assign(vars, userVariables);
    
    // Add built-in variables
    vars.cwd = process?.cwd?.() || '/';
    vars.user = process?.env?.USER || 'user';
    vars.date = new Date().toISOString().split('T')[0];
    vars.time = new Date().toTimeString().split(' ')[0];
    vars.timestamp = Date.now();
    
    return vars;
  }
  
  /**
   * Execute workflow
   */
  async execute() {
    this.status = 'running';
    this.emit('start', { workflow: this.workflow });
    
    try {
      for (let i = 0; i < this.workflow.steps.length; i++) {
        if (this.cancelled) {
          this.status = 'cancelled';
          this.emit('cancelled', {});
          return this.results;
        }
        
        this.currentStep = i;
        const step = this.workflow.steps[i];
        
        this.emit('step-start', { step, index: i });
        
        try {
          const result = await this.executeStep(step);
          this.results.push({ step, result, status: 'success' });
          
          this.emit('step-complete', { step, result, index: i });
          this.emit('progress', {
            current: i + 1,
            total: this.workflow.steps.length,
            stepName: step.name || `Step ${i + 1}`,
            percentage: Math.round(((i + 1) / this.workflow.steps.length) * 100)
          });
          
        } catch (error) {
          this.results.push({ step, error: error.message, status: 'failed' });
          this.emit('step-failed', { step, error, index: i });
          
          if (!step.continueOnError) {
            this.status = 'failed';
            this.emit('failed', { error, step, index: i });
            throw error;
          }
        }
      }
      
      this.status = 'completed';
      this.emit('complete', { results: this.results });
      return this.results;
      
    } catch (error) {
      this.status = 'failed';
      throw error;
    }
  }
  
  /**
   * Execute single step
   */
  async executeStep(step) {
    // Resolve variables in step
    const resolved = this.resolveVariables(step);
    
    switch (resolved.type) {
      case 'command':
        return await this.executeCommand(resolved);
      case 'confirm':
        return await this.executeConfirm(resolved);
      case 'input':
        return await this.executeInput(resolved);
      case 'select':
        return await this.executeSelect(resolved);
      case 'success':
        return await this.executeMessage(resolved, 'success');
      case 'error':
        return await this.executeMessage(resolved, 'error');
      case 'conditional':
        return await this.executeConditional(resolved);
      case 'parallel':
        return await this.executeParallel(resolved);
      default:
        throw new Error(`Unknown step type: ${resolved.type}`);
    }
  }
  
  /**
   * Execute command step
   */
  async executeCommand(step) {
    return new Promise((resolve, reject) => {
      // Request command execution from main app
      const event = new CustomEvent('workflow-execute-command', {
        detail: {
          command: step.command,
          name: step.name,
          resolve,
          reject
        }
      });
      window.dispatchEvent(event);
    });
  }
  
  /**
   * Execute confirm step
   */
  async executeConfirm(step) {
    return new Promise((resolve, reject) => {
      const event = new CustomEvent('workflow-confirm', {
        detail: {
          message: step.message,
          default: step.default !== false,
          resolve,
          reject
        }
      });
      window.dispatchEvent(event);
    });
  }
  
  /**
   * Execute input step
   */
  async executeInput(step) {
    return new Promise((resolve, reject) => {
      const event = new CustomEvent('workflow-input', {
        detail: {
          prompt: step.prompt,
          defaultValue: step.default || '',
          required: step.required !== false,
          resolve: (value) => {
            if (step.variable) {
              this.variables[step.variable] = value;
            }
            resolve(value);
          },
          reject
        }
      });
      window.dispatchEvent(event);
    });
  }
  
  /**
   * Execute select step
   */
  async executeSelect(step) {
    return new Promise((resolve, reject) => {
      const event = new CustomEvent('workflow-select', {
        detail: {
          prompt: step.prompt,
          options: step.options,
          defaultValue: step.default,
          resolve: (value) => {
            if (step.variable) {
              this.variables[step.variable] = value;
            }
            resolve(value);
          },
          reject
        }
      });
      window.dispatchEvent(event);
    });
  }
  
  /**
   * Execute message step
   */
  async executeMessage(step, type) {
    return new Promise((resolve) => {
      const event = new CustomEvent('workflow-message', {
        detail: {
          message: step.message,
          type,
          resolve
        }
      });
      window.dispatchEvent(event);
    });
  }
  
  /**
   * Execute conditional step
   */
  async executeConditional(step) {
    // Simple condition evaluation
    const condition = this.evaluateCondition(step.condition);
    
    if (condition && step.steps) {
      const results = [];
      for (const substep of step.steps) {
        const result = await this.executeStep(substep);
        results.push(result);
      }
      return results;
    }
    
    return null;
  }
  
  /**
   * Execute parallel steps
   */
  async executeParallel(step) {
    if (!step.steps || !Array.isArray(step.steps)) {
      throw new Error('Parallel step must have steps array');
    }
    
    const promises = step.steps.map(substep => this.executeStep(substep));
    return await Promise.all(promises);
  }
  
  /**
   * Evaluate simple conditions
   */
  evaluateCondition(condition) {
    // Simple evaluation for MVP
    // In production, use a proper expression parser
    try {
      // Replace variables
      const resolved = this.resolveString(condition);
      
      // Simple equality check
      const match = resolved.match(/^(.+?)\s*(==|!=|>|<|>=|<=)\s*(.+?)$/);
      if (match) {
        const [, left, op, right] = match;
        const leftVal = left.trim().replace(/['"]/g, '');
        const rightVal = right.trim().replace(/['"]/g, '');
        
        switch (op) {
          case '==': return leftVal === rightVal;
          case '!=': return leftVal !== rightVal;
          case '>': return Number(leftVal) > Number(rightVal);
          case '<': return Number(leftVal) < Number(rightVal);
          case '>=': return Number(leftVal) >= Number(rightVal);
          case '<=': return Number(leftVal) <= Number(rightVal);
        }
      }
      
      return Boolean(resolved);
    } catch (error) {
      console.error('Condition evaluation error:', error);
      return false;
    }
  }
  
  /**
   * Resolve variables in object
   */
  resolveVariables(obj) {
    if (typeof obj === 'string') {
      return this.resolveString(obj);
    }
    
    if (Array.isArray(obj)) {
      return obj.map(item => this.resolveVariables(item));
    }
    
    if (obj && typeof obj === 'object') {
      const resolved = {};
      for (const [key, value] of Object.entries(obj)) {
        resolved[key] = this.resolveVariables(value);
      }
      return resolved;
    }
    
    return obj;
  }
  
  /**
   * Resolve variables in string
   */
  resolveString(str) {
    return str.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
      return this.variables[varName] !== undefined ? this.variables[varName] : match;
    });
  }
  
  /**
   * Cancel execution
   */
  cancel() {
    this.cancelled = true;
  }
  
  /**
   * Event emitter
   */
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);
  }
  
  emit(event, data) {
    const listeners = this.eventListeners.get(event) || [];
    listeners.forEach(callback => callback(data));
    
    const wildcardListeners = this.eventListeners.get('*') || [];
    wildcardListeners.forEach(callback => callback(event, data));
  }
}

// Initialize
if (typeof window !== 'undefined') {
  window.WorkflowEngine = WorkflowEngine;
  window.workflowEngine = new WorkflowEngine();
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { WorkflowEngine, WorkflowExecutor };
}
