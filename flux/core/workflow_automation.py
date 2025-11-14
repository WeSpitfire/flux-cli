"""Workflow Automation System for Flux-CLI.

This module provides workflow recording, replay, macro support, and
custom tool creation capabilities for automating repetitive tasks.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of recordable actions."""
    TOOL_CALL = "tool_call"
    FILE_OPERATION = "file_operation"
    SEARCH = "search"
    COMMAND = "command"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow."""
    id: str
    type: ActionType
    action: str
    params: Dict[str, Any]
    result: Optional[Any] = None
    timestamp: float = None
    duration: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['type'] = self.type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowStep':
        """Create from dictionary."""
        data['type'] = ActionType(data['type'])
        return cls(**data)


@dataclass
class Workflow:
    """Represents a complete workflow."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: float
    last_run: Optional[float] = None
    run_count: int = 0
    tags: List[str] = None
    variables: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': [step.to_dict() for step in self.steps],
            'created_at': self.created_at,
            'last_run': self.last_run,
            'run_count': self.run_count,
            'tags': self.tags or [],
            'variables': self.variables or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Workflow':
        """Create from dictionary."""
        data['steps'] = [WorkflowStep.from_dict(s) for s in data['steps']]
        return cls(**data)


class WorkflowRecorder:
    """Records user actions to create replayable workflows."""
    
    def __init__(self):
        self.recording = False
        self.current_workflow = None
        self.current_steps = []
        self.start_time = None
    
    def start_recording(self, name: str, description: str = ""):
        """Start recording a new workflow."""
        self.recording = True
        self.current_steps = []
        self.start_time = time.time()
        self.current_workflow = {
            'name': name,
            'description': description,
            'id': hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:12]
        }
        logger.info(f"Started recording workflow: {name}")
    
    def stop_recording(self) -> Optional[Workflow]:
        """Stop recording and return the workflow."""
        if not self.recording:
            return None
        
        self.recording = False
        
        workflow = Workflow(
            id=self.current_workflow['id'],
            name=self.current_workflow['name'],
            description=self.current_workflow['description'],
            steps=self.current_steps,
            created_at=self.start_time,
            tags=[]
        )
        
        logger.info(f"Stopped recording workflow: {workflow.name} with {len(self.current_steps)} steps")
        
        self.current_workflow = None
        self.current_steps = []
        
        return workflow
    
    def record_step(
        self,
        action_type: ActionType,
        action: str,
        params: Dict[str, Any],
        result: Any = None,
        metadata: Dict[str, Any] = None
    ):
        """Record a single workflow step."""
        if not self.recording:
            return
        
        step_id = f"step_{len(self.current_steps) + 1}"
        step = WorkflowStep(
            id=step_id,
            type=action_type,
            action=action,
            params=params,
            result=result,
            metadata=metadata or {}
        )
        
        self.current_steps.append(step)
        logger.debug(f"Recorded step: {action_type.value} - {action}")


class WorkflowPlayer:
    """Replays recorded workflows."""
    
    def __init__(self, tool_registry: Dict[str, Callable] = None):
        """Initialize workflow player.
        
        Args:
            tool_registry: Registry of available tools for execution
        """
        self.tool_registry = tool_registry or {}
        self.current_workflow = None
        self.execution_history = []
        self.variables = {}
    
    async def play(
        self,
        workflow: Workflow,
        variables: Dict[str, Any] = None,
        interactive: bool = False
    ) -> Dict[str, Any]:
        """Play a workflow.
        
        Args:
            workflow: Workflow to execute
            variables: Variable substitutions
            interactive: Whether to prompt for confirmation
            
        Returns:
            Execution results
        """
        self.current_workflow = workflow
        self.variables = variables or {}
        results = []
        
        logger.info(f"Playing workflow: {workflow.name}")
        
        for i, step in enumerate(workflow.steps):
            if interactive:
                response = await self._prompt_step(step)
                if response == 'skip':
                    continue
                elif response == 'stop':
                    break
            
            try:
                result = await self._execute_step(step)
                results.append({
                    'step_id': step.id,
                    'success': True,
                    'result': result
                })
            except Exception as e:
                logger.error(f"Error executing step {step.id}: {e}")
                results.append({
                    'step_id': step.id,
                    'success': False,
                    'error': str(e)
                })
                
                if interactive:
                    if not await self._prompt_continue():
                        break
        
        # Update workflow metadata
        workflow.last_run = time.time()
        workflow.run_count += 1
        
        return {
            'workflow_id': workflow.id,
            'steps_executed': len(results),
            'results': results,
            'success': all(r['success'] for r in results)
        }
    
    async def _execute_step(self, step: WorkflowStep) -> Any:
        """Execute a single workflow step."""
        # Substitute variables in parameters
        params = self._substitute_variables(step.params)
        
        if step.type == ActionType.TOOL_CALL:
            if step.action in self.tool_registry:
                tool = self.tool_registry[step.action]
                return await tool(**params)
            else:
                raise ValueError(f"Unknown tool: {step.action}")
        
        elif step.type == ActionType.COMMAND:
            # Execute shell command
            import subprocess
            result = subprocess.run(
                params['command'],
                shell=True,
                capture_output=True,
                text=True
            )
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        
        else:
            # Custom action - would need specific handler
            logger.warning(f"Unhandled action type: {step.type}")
            return None
    
    def _substitute_variables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute variables in parameters."""
        result = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                var_name = value[2:-1]
                result[key] = self.variables.get(var_name, value)
            else:
                result[key] = value
        return result
    
    async def _prompt_step(self, step: WorkflowStep) -> str:
        """Prompt user about step execution."""
        print(f"\nAbout to execute: {step.action}")
        print(f"Parameters: {step.params}")
        response = input("Execute? (y/n/skip/stop): ").lower()
        
        if response == 'n':
            return 'skip'
        elif response == 'stop':
            return 'stop'
        return 'execute'
    
    async def _prompt_continue(self) -> bool:
        """Prompt whether to continue after error."""
        response = input("Error occurred. Continue? (y/n): ").lower()
        return response == 'y'


class MacroSystem:
    """System for creating and managing macros."""
    
    def __init__(self, storage_dir: Path = None):
        """Initialize macro system.
        
        Args:
            storage_dir: Directory to store macro definitions
        """
        self.storage_dir = storage_dir or Path.home() / ".flux" / "macros"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.macros = self._load_macros()
    
    def _load_macros(self) -> Dict[str, Dict]:
        """Load all macros from storage."""
        macros = {}
        for macro_file in self.storage_dir.glob("*.json"):
            try:
                with open(macro_file, 'r') as f:
                    macro = json.load(f)
                    macros[macro['name']] = macro
            except Exception as e:
                logger.error(f"Error loading macro {macro_file}: {e}")
        return macros
    
    def create_macro(
        self,
        name: str,
        description: str,
        template: str,
        variables: List[str],
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Create a new macro.
        
        Args:
            name: Macro name
            description: Macro description
            template: Command template with ${var} placeholders
            variables: List of variable names
            tags: Optional tags for categorization
            
        Returns:
            Macro definition
        """
        macro = {
            'name': name,
            'description': description,
            'template': template,
            'variables': variables,
            'tags': tags or [],
            'created_at': time.time()
        }
        
        # Save to disk
        macro_file = self.storage_dir / f"{name}.json"
        with open(macro_file, 'w') as f:
            json.dump(macro, f, indent=2)
        
        self.macros[name] = macro
        logger.info(f"Created macro: {name}")
        
        return macro
    
    def execute_macro(self, name: str, **kwargs) -> str:
        """Execute a macro with variable substitution.
        
        Args:
            name: Macro name
            **kwargs: Variable values
            
        Returns:
            Expanded command
        """
        if name not in self.macros:
            raise ValueError(f"Unknown macro: {name}")
        
        macro = self.macros[name]
        template = macro['template']
        
        # Substitute variables
        for var in macro['variables']:
            if var in kwargs:
                placeholder = f"${{{var}}}"
                template = template.replace(placeholder, str(kwargs[var]))
        
        return template
    
    def list_macros(self, tags: List[str] = None) -> List[Dict]:
        """List available macros.
        
        Args:
            tags: Filter by tags
            
        Returns:
            List of macro definitions
        """
        macros = list(self.macros.values())
        
        if tags:
            macros = [
                m for m in macros
                if any(tag in m.get('tags', []) for tag in tags)
            ]
        
        return macros


class CustomToolBuilder:
    """Builder for creating custom tools."""
    
    def __init__(self):
        self.custom_tools = {}
    
    def create_tool(
        self,
        name: str,
        description: str,
        parameters: List[Dict[str, Any]],
        implementation: Union[str, Callable]
    ) -> Dict[str, Any]:
        """Create a custom tool.
        
        Args:
            name: Tool name
            description: Tool description
            parameters: List of parameter definitions
            implementation: Python code or callable
            
        Returns:
            Tool definition
        """
        tool = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'implementation': implementation,
            'created_at': time.time()
        }
        
        # Create executable
        if isinstance(implementation, str):
            # Compile Python code
            exec_globals = {}
            exec(implementation, exec_globals)
            tool['executor'] = exec_globals.get('execute', None)
        else:
            tool['executor'] = implementation
        
        self.custom_tools[name] = tool
        logger.info(f"Created custom tool: {name}")
        
        return tool
    
    async def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a custom tool.
        
        Args:
            name: Tool name
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        if name not in self.custom_tools:
            raise ValueError(f"Unknown custom tool: {name}")
        
        tool = self.custom_tools[name]
        executor = tool.get('executor')
        
        if not executor:
            raise ValueError(f"Tool {name} has no executor")
        
        if asyncio.iscoroutinefunction(executor):
            return await executor(**kwargs)
        else:
            return executor(**kwargs)


class WorkflowAutomation:
    """Main workflow automation system."""
    
    def __init__(self, storage_dir: Path = None):
        """Initialize workflow automation.
        
        Args:
            storage_dir: Directory to store workflows
        """
        self.storage_dir = storage_dir or Path.home() / ".flux" / "workflows"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.recorder = WorkflowRecorder()
        self.player = WorkflowPlayer()
        self.macro_system = MacroSystem()
        self.tool_builder = CustomToolBuilder()
        
        self.workflows = self._load_workflows()
    
    def _load_workflows(self) -> Dict[str, Workflow]:
        """Load all workflows from storage."""
        workflows = {}
        for wf_file in self.storage_dir.glob("*.json"):
            try:
                with open(wf_file, 'r') as f:
                    data = json.load(f)
                    workflow = Workflow.from_dict(data)
                    workflows[workflow.id] = workflow
            except Exception as e:
                logger.error(f"Error loading workflow {wf_file}: {e}")
        return workflows
    
    def save_workflow(self, workflow: Workflow):
        """Save workflow to disk."""
        wf_file = self.storage_dir / f"{workflow.id}.json"
        with open(wf_file, 'w') as f:
            json.dump(workflow.to_dict(), f, indent=2)
        
        self.workflows[workflow.id] = workflow
        logger.info(f"Saved workflow: {workflow.name}")
    
    async def run_workflow(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Run a saved workflow.
        
        Args:
            workflow_id: ID of workflow to run
            variables: Variable substitutions
            
        Returns:
            Execution results
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        return await self.player.play(workflow, variables)
    
    def list_workflows(self, tags: List[str] = None) -> List[Workflow]:
        """List available workflows.
        
        Args:
            tags: Filter by tags
            
        Returns:
            List of workflows
        """
        workflows = list(self.workflows.values())
        
        if tags:
            workflows = [
                w for w in workflows
                if any(tag in w.tags for tag in tags)
            ]
        
        return workflows


# Example usage
async def demo_workflow_automation():
    """Demonstrate workflow automation capabilities."""
    print("🤖 Workflow Automation Demo")
    print("=" * 60)
    
    automation = WorkflowAutomation()
    
    # Demo 1: Record a workflow
    print("\n📹 Recording a workflow:")
    automation.recorder.start_recording(
        "code_review",
        "Automated code review workflow"
    )
    
    # Simulate recording steps
    automation.recorder.record_step(
        ActionType.FILE_OPERATION,
        "read_files",
        {"paths": ["main.py", "utils.py"]},
        result="Files read successfully"
    )
    
    automation.recorder.record_step(
        ActionType.TOOL_CALL,
        "analyze_code",
        {"files": ["main.py", "utils.py"]},
        result="No issues found"
    )
    
    automation.recorder.record_step(
        ActionType.COMMAND,
        "run_tests",
        {"command": "pytest tests/"},
        result="All tests passed"
    )
    
    workflow = automation.recorder.stop_recording()
    print(f"  ✅ Recorded workflow: {workflow.name}")
    print(f"     Steps: {len(workflow.steps)}")
    
    # Save workflow
    automation.save_workflow(workflow)
    
    # Demo 2: Create a macro
    print("\n🎯 Creating a macro:")
    macro = automation.macro_system.create_macro(
        name="git_commit",
        description="Git commit with formatted message",
        template="git commit -m '${type}: ${message}'",
        variables=["type", "message"],
        tags=["git", "version-control"]
    )
    print(f"  ✅ Created macro: {macro['name']}")
    
    # Execute macro
    command = automation.macro_system.execute_macro(
        "git_commit",
        type="feat",
        message="Add workflow automation"
    )
    print(f"     Expanded: {command}")
    
    # Demo 3: Create custom tool
    print("\n🔧 Creating custom tool:")
    
    implementation = """
def execute(file_path, pattern):
    # Count occurrences of pattern in file
    with open(file_path, 'r') as f:
        content = f.read()
        return content.count(pattern)
"""
    
    tool = automation.tool_builder.create_tool(
        name="count_pattern",
        description="Count occurrences of pattern in file",
        parameters=[
            {"name": "file_path", "type": "string"},
            {"name": "pattern", "type": "string"}
        ],
        implementation=implementation
    )
    print(f"  ✅ Created custom tool: {tool['name']}")
    
    # Demo 4: List workflows
    print("\n📋 Available workflows:")
    workflows = automation.list_workflows()
    for wf in workflows:
        print(f"  • {wf.name} ({wf.id[:8]}...)")
        print(f"    Steps: {len(wf.steps)}, Runs: {wf.run_count}")
    
    print("\n✨ Workflow automation ready!")
    print("   Record → Save → Replay → Automate")


if __name__ == "__main__":
    asyncio.run(demo_workflow_automation())