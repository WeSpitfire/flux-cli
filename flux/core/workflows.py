"""Workflow System - Define and execute custom workflows.

Allows users to define multi-step workflows with conditionals and error handling.
Example: "deploy-staging" runs tests, builds, deploys, verifies, and notifies.
"""

import yaml
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class StepType(Enum):
    """Types of workflow steps."""
    TOOL = "tool"  # Run a Flux tool
    COMMAND = "command"  # Run shell command
    CONDITION = "condition"  # Conditional branch
    PARALLEL = "parallel"  # Run steps in parallel
    NOTIFY = "notify"  # Send notification


class StepStatus(Enum):
    """Status of workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    name: str
    step_type: StepType
    tool_name: Optional[str] = None
    command: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # e.g., "prev_step_success"
    parallel_steps: List['WorkflowStep'] = field(default_factory=list)
    continue_on_error: bool = False
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'step_type': self.step_type.value,
            'tool_name': self.tool_name,
            'command': self.command,
            'params': self.params,
            'condition': self.condition,
            'parallel_steps': [s.to_dict() for s in self.parallel_steps],
            'continue_on_error': self.continue_on_error,
            'status': self.status.value,
            'result': str(self.result) if self.result else None,
            'error': self.error
        }


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    name: str
    description: str
    steps: List[WorkflowStep]
    on_success: Optional[List[WorkflowStep]] = None
    on_failure: Optional[List[WorkflowStep]] = None
    timeout: int = 600  # seconds

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'steps': [s.to_dict() for s in self.steps],
            'on_success': [s.to_dict() for s in self.on_success] if self.on_success else None,
            'on_failure': [s.to_dict() for s in self.on_failure] if self.on_failure else None,
            'timeout': self.timeout
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowDefinition':
        """Create workflow from dict."""
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            steps=[WorkflowStep(**step) for step in data.get('steps', [])],
            on_success=[WorkflowStep(**step) for step in data.get('on_success', [])] if data.get('on_success') else None,
            on_failure=[WorkflowStep(**step) for step in data.get('on_failure', [])] if data.get('on_failure') else None,
            timeout=data.get('timeout', 600)
        )


class WorkflowExecutor:
    """Executes workflows with conditional logic and error handling."""

    def __init__(self, orchestrator=None):
        """Initialize workflow executor.

        Args:
            orchestrator: AIOrchestrator instance for running tools
        """
        self.orchestrator = orchestrator
        self.notification_callbacks: List[Callable[[str], None]] = []
        self.progress_callbacks: List[Callable[[Dict], None]] = []

    def add_notification_callback(self, callback: Callable[[str], None]):
        """Add callback for notifications."""
        self.notification_callbacks.append(callback)

    def add_progress_callback(self, callback: Callable[[Dict], None]):
        """Add callback for progress updates."""
        self.progress_callbacks.append(callback)

    async def execute(self, workflow: WorkflowDefinition, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a workflow.

        Args:
            workflow: Workflow to execute
            context: Optional context variables

        Returns:
            Dict with execution results
        """
        context = context or {}
        start_time = asyncio.get_event_loop().time()

        self._notify_progress({
            'workflow': workflow.name,
            'status': 'starting',
            'total_steps': len(workflow.steps)
        })

        try:
            # Execute main steps
            results = []
            all_success = True

            for i, step in enumerate(workflow.steps):
                # Check condition
                if step.condition and not self._check_condition(step.condition, context):
                    step.status = StepStatus.SKIPPED
                    results.append({'step': step.name, 'status': 'skipped'})
                    continue

                # Execute step
                self._notify_progress({
                    'workflow': workflow.name,
                    'status': 'running',
                    'current_step': i + 1,
                    'total_steps': len(workflow.steps),
                    'step_name': step.name
                })

                result = await self._execute_step(step, context)
                results.append(result)

                if not result.get('success', False):
                    all_success = False
                    if not step.continue_on_error:
                        break

            # Execute success/failure handlers
            if all_success and workflow.on_success:
                for step in workflow.on_success:
                    await self._execute_step(step, context)
            elif not all_success and workflow.on_failure:
                for step in workflow.on_failure:
                    await self._execute_step(step, context)

            elapsed = asyncio.get_event_loop().time() - start_time

            self._notify_progress({
                'workflow': workflow.name,
                'status': 'completed' if all_success else 'failed',
                'success': all_success,
                'elapsed': elapsed
            })

            return {
                'success': all_success,
                'workflow': workflow.name,
                'results': results,
                'elapsed': elapsed
            }

        except asyncio.TimeoutError:
            return {
                'success': False,
                'workflow': workflow.name,
                'error': 'Workflow timeout'
            }

    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step.

        Args:
            step: Step to execute
            context: Execution context

        Returns:
            Dict with step result
        """
        step.status = StepStatus.RUNNING

        try:
            if step.step_type == StepType.TOOL:
                result = await self._execute_tool(step, context)
            elif step.step_type == StepType.COMMAND:
                result = await self._execute_command(step, context)
            elif step.step_type == StepType.PARALLEL:
                result = await self._execute_parallel(step, context)
            elif step.step_type == StepType.NOTIFY:
                result = await self._execute_notify(step, context)
            elif step.step_type == StepType.CONDITION:
                result = await self._execute_condition(step, context)
            else:
                result = {'success': False, 'error': f'Unknown step type: {step.step_type}'}

            if result.get('success', False):
                step.status = StepStatus.COMPLETED
                step.result = result
                context[f'step_{step.name}_result'] = result
            else:
                step.status = StepStatus.FAILED
                step.error = result.get('error', 'Unknown error')

            return {
                'step': step.name,
                'success': result.get('success', False),
                'result': result,
                'error': step.error
            }

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            return {
                'step': step.name,
                'success': False,
                'error': str(e)
            }

    async def _execute_tool(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via orchestrator."""
        if not self.orchestrator:
            return {'success': False, 'error': 'No orchestrator available'}

        tool = self.orchestrator.tools.get(step.tool_name)
        if not tool:
            return {'success': False, 'error': f'Tool not found: {step.tool_name}'}

        try:
            # Resolve params with context
            params = self._resolve_params(step.params, context)

            # Execute tool
            if asyncio.iscoroutinefunction(tool.executor):
                result = await tool.executor(**params)
            else:
                result = tool.executor(**params)

            return {'success': True, 'result': result}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _execute_command(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command."""
        import subprocess

        try:
            # Resolve command with context
            command = self._resolve_string(step.command, context)

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=step.params.get('timeout', 60)
            )

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Command timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _execute_parallel(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute steps in parallel."""
        tasks = [self._execute_step(s, context) for s in step.parallel_steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_success = all(
            isinstance(r, dict) and r.get('success', False)
            for r in results
        )

        return {
            'success': all_success,
            'results': results
        }

    async def _execute_notify(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send a notification."""
        message = self._resolve_string(step.params.get('message', ''), context)

        for callback in self.notification_callbacks:
            try:
                callback(message)
            except Exception:
                pass

        return {'success': True, 'message': message}

    async def _execute_condition(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute conditional branch."""
        condition = step.condition or step.params.get('condition', 'true')

        if self._check_condition(condition, context):
            # Execute 'then' steps
            then_steps = step.params.get('then', [])
            results = []
            for s in then_steps:
                result = await self._execute_step(WorkflowStep(**s), context)
                results.append(result)
            return {'success': True, 'branch': 'then', 'results': results}
        else:
            # Execute 'else' steps
            else_steps = step.params.get('else', [])
            results = []
            for s in else_steps:
                result = await self._execute_step(WorkflowStep(**s), context)
                results.append(result)
            return {'success': True, 'branch': 'else', 'results': results}

    def _check_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Check if condition is true.

        Supports simple conditions like:
        - "prev_step_success"
        - "tests_passed"
        - "build_success"
        """
        # Simple condition evaluation
        if condition == 'true':
            return True
        elif condition == 'false':
            return False
        elif condition in context:
            value = context[condition]
            if isinstance(value, bool):
                return value
            elif isinstance(value, dict):
                return value.get('success', False)

        # Check for variable existence
        return condition in context

    def _resolve_params(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameter values from context."""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_string(value, context)
            else:
                resolved[key] = value
        return resolved

    def _resolve_string(self, text: str, context: Dict[str, Any]) -> str:
        """Resolve string with context variables.

        Supports syntax like: "Result: {prev_step_result}"
        """
        if not text:
            return text

        for key, value in context.items():
            placeholder = f'{{{key}}}'
            if placeholder in text:
                text = text.replace(placeholder, str(value))

        return text

    def _notify_progress(self, progress: Dict[str, Any]):
        """Notify progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception:
                pass


class WorkflowManager:
    """Manages workflow definitions and templates."""

    def __init__(self, project_path: Path):
        """Initialize workflow manager.

        Args:
            project_path: Root directory of project
        """
        self.project_path = project_path
        self.flux_dir = project_path / ".flux"
        self.flux_dir.mkdir(exist_ok=True)

        self.workflows_file = self.flux_dir / "workflows.yaml"
        self.workflows: Dict[str, WorkflowDefinition] = {}

        self._load_workflows()
        self._load_templates()

    def _load_workflows(self):
        """Load user-defined workflows."""
        if self.workflows_file.exists():
            try:
                with open(self.workflows_file) as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        for name, workflow_data in data.items():
                            workflow_data['name'] = name
                            self.workflows[name] = self._parse_workflow(workflow_data)
            except Exception as e:
                print(f"Error loading workflows: {e}")

    def _load_templates(self):
        """Load built-in workflow templates."""
        templates = {
            'deploy-staging': {
                'name': 'deploy-staging',
                'description': 'Deploy to staging environment',
                'steps': [
                    {
                        'name': 'run_tests',
                        'step_type': 'tool',
                        'tool_name': 'run_tests',
                        'params': {}
                    },
                    {
                        'name': 'build',
                        'step_type': 'command',
                        'command': 'npm run build',
                        'condition': 'step_run_tests_result'
                    },
                    {
                        'name': 'deploy',
                        'step_type': 'command',
                        'command': 'deploy.sh staging',
                        'condition': 'step_build_result'
                    },
                    {
                        'name': 'verify',
                        'step_type': 'command',
                        'command': 'curl https://staging.example.com/health'
                    },
                    {
                        'name': 'notify',
                        'step_type': 'notify',
                        'params': {'message': '✅ Deployed to staging successfully!'}
                    }
                ]
            },
            'pr-ready': {
                'name': 'pr-ready',
                'description': 'Prepare code for pull request',
                'steps': [
                    {
                        'name': 'format',
                        'step_type': 'tool',
                        'tool_name': 'auto_fix',
                        'params': {}
                    },
                    {
                        'name': 'lint',
                        'step_type': 'command',
                        'command': 'ruff check .'
                    },
                    {
                        'name': 'typecheck',
                        'step_type': 'command',
                        'command': 'mypy .'
                    },
                    {
                        'name': 'tests',
                        'step_type': 'tool',
                        'tool_name': 'run_tests',
                        'params': {}
                    },
                    {
                        'name': 'commit',
                        'step_type': 'tool',
                        'tool_name': 'git_commit',
                        'params': {}
                    }
                ]
            },
            'quick-check': {
                'name': 'quick-check',
                'description': 'Quick validation before committing',
                'steps': [
                    {
                        'name': 'format',
                        'step_type': 'tool',
                        'tool_name': 'auto_fix',
                        'params': {}
                    },
                    {
                        'name': 'tests',
                        'step_type': 'tool',
                        'tool_name': 'run_tests',
                        'params': {}
                    }
                ]
            }
        }

        for name, template in templates.items():
            if name not in self.workflows:
                self.workflows[name] = self._parse_workflow(template)

    def _parse_workflow(self, data: Dict) -> WorkflowDefinition:
        """Parse workflow from dict."""
        steps = []
        for step_data in data.get('steps', []):
            # Handle both old format (with 'name') and new YAML format
            # In YAML format, steps might have 'tool' and 'description' instead
            step_name = step_data.get('name') or step_data.get('description', 'unnamed_step')

            # Determine step type from the data
            if 'tool' in step_data:
                step_type = StepType.TOOL
                tool_name = step_data['tool']
                command = None
                # 'input' in YAML maps to 'params'
                params = step_data.get('input', step_data.get('params', {}))
            elif 'command' in step_data:
                step_type = StepType.COMMAND
                tool_name = None
                command = step_data['command']
                params = step_data.get('params', {})
            else:
                # Fallback to old format
                step_type = StepType(step_data.get('step_type', 'tool'))
                tool_name = step_data.get('tool_name')
                command = step_data.get('command')
                params = step_data.get('params', {})

            steps.append(WorkflowStep(
                name=step_name,
                step_type=step_type,
                tool_name=tool_name,
                command=command,
                params=params,
                condition=step_data.get('condition'),
                continue_on_error=step_data.get('continue_on_error', False)
            ))

        return WorkflowDefinition(
            name=data['name'],
            description=data.get('description', ''),
            steps=steps,
            timeout=data.get('timeout', 600)
        )

    def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        """Get workflow by name."""
        return self.workflows.get(name)

    def list_workflows(self) -> List[str]:
        """List all available workflows."""
        return list(self.workflows.keys())

    def save_workflow(self, workflow: WorkflowDefinition):
        """Save a workflow to file."""
        self.workflows[workflow.name] = workflow

        # Load existing workflows
        existing = {}
        if self.workflows_file.exists():
            with open(self.workflows_file) as f:
                existing = yaml.safe_load(f) or {}

        # Add new workflow
        existing[workflow.name] = workflow.to_dict()

        # Save
        with open(self.workflows_file, 'w') as f:
            yaml.dump(existing, f, default_flow_style=False, sort_keys=False)
