"""AI Orchestrator - Intelligent workflow orchestration for Flux.

This module enables the AI to orchestrate complete workflows by:
1. Understanding user goals
2. Planning execution steps
3. Executing tools in proper order
4. Handling failures and recovery
5. Returning complete results

The orchestrator makes Flux feel invisible by handling all the complexity
of tool selection, ordering, and execution automatically.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Awaitable
from enum import Enum
from pathlib import Path
import json


class StepStatus(Enum):
    """Status of an execution step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    """A single step in the execution plan."""
    tool_name: str
    description: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            'tool_name': self.tool_name,
            'description': self.description,
            'params': self.params,
            'status': self.status.value,
            'result': str(self.result) if self.result else None,
            'error': self.error
        }


@dataclass
class WorkflowPlan:
    """A complete execution plan for a user goal."""
    goal: str
    steps: List[ExecutionStep]
    estimated_duration: Optional[int] = None  # seconds
    requires_approval: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            'goal': self.goal,
            'steps': [step.to_dict() for step in self.steps],
            'estimated_duration': self.estimated_duration,
            'requires_approval': self.requires_approval
        }


@dataclass
class ToolDefinition:
    """Definition of a tool available to the orchestrator."""
    name: str
    description: str
    executor: Callable
    schema: Dict[str, Any]
    requires_approval: bool = False
    is_destructive: bool = False

    def to_ai_description(self) -> str:
        """Format for LLM understanding."""
        return f"""
Tool: {self.name}
Description: {self.description}
Parameters: {json.dumps(self.schema, indent=2)}
Requires approval: {self.requires_approval}
Destructive: {self.is_destructive}
"""


class AIOrchestrator:
    """
    AI-driven orchestration engine.

    Responsibilities:
    - Parse user goals into actionable plans
    - Execute plans using available tools
    - Handle errors and recovery
    - Auto-enable features as needed
    - Provide complete, coherent results
    """

    def __init__(self, llm_provider, cwd: Path):
        """Initialize orchestrator.

        Args:
            llm_provider: LLM provider for planning
            cwd: Current working directory
        """
        self.llm = llm_provider
        self.cwd = cwd
        self.tools: Dict[str, ToolDefinition] = {}
        self.current_plan: Optional[WorkflowPlan] = None
        self.execution_history: List[WorkflowPlan] = []

    def register_tool(self, tool: ToolDefinition):
        """Register a tool for orchestration.

        Args:
            tool: Tool definition to register
        """
        self.tools[tool.name] = tool

    async def execute_goal(self, goal: str, auto_approve: bool = False) -> Dict[str, Any]:
        """Execute a user goal by planning and executing steps.

        Args:
            goal: Natural language description of what to achieve
            auto_approve: Skip approval prompts for non-destructive operations

        Returns:
            Dict with results, summary, and any errors
        """
        # Step 1: Create execution plan
        plan = await self.create_plan(goal)
        self.current_plan = plan

        # Step 2: Show plan to user if needed
        if plan.requires_approval and not auto_approve:
            # This will be handled by CLI - for now just note it
            pass

        # Step 3: Execute plan
        results = await self.execute_plan(plan)

        # Step 4: Generate summary
        summary = await self.generate_summary(plan, results)

        # Step 5: Store in history
        self.execution_history.append(plan)

        return {
            'success': all(r.get('success', False) for r in results),
            'plan': plan.to_dict(),
            'results': results,
            'summary': summary
        }

    async def create_plan(self, goal: str) -> WorkflowPlan:
        """Create an execution plan for a goal using LLM.

        Args:
            goal: User's goal in natural language

        Returns:
            WorkflowPlan with steps to execute
        """
        # Build prompt for LLM
        tools_desc = "\n\n".join([
            tool.to_ai_description()
            for tool in self.tools.values()
        ])

        system_prompt = f"""You are an AI orchestrator that creates execution plans.

Available tools:
{tools_desc}

Your job: Given a user goal, create a JSON plan with steps that use these tools.

IMPORTANT: You MUST respond with ONLY valid JSON. No explanations, no markdown, no text before or after the JSON.

Output format (exactly this structure):
{{
  "steps": [
    {{
      "tool_name": "tool_name",
      "description": "What this step does",
      "params": {{"param": "value"}}
    }}
  ],
  "estimated_duration": 30,
  "requires_approval": false
}}

Rules:
1. Break down complex goals into simple steps
2. Use the right tool for each step
3. Order steps logically (e.g., generate code before testing)
4. Include validation and testing steps
5. Set requires_approval=true if any destructive operations
6. Be thorough but efficient

Examples:

Goal: "Add login page with validation"
Plan:
{{
  "steps": [
    {{"tool_name": "generate_code", "description": "Create login.html with form", "params": {{"file": "login.html"}}}},
    {{"tool_name": "generate_code", "description": "Create validation.js", "params": {{"file": "validation.js"}}}},
    {{"tool_name": "generate_tests", "description": "Create test cases", "params": {{"files": ["login.html", "validation.js"]}}}},
    {{"tool_name": "run_tests", "description": "Run all tests", "params": {{}}}},
    {{"tool_name": "auto_fix", "description": "Fix formatting", "params": {{}}}}
  ],
  "estimated_duration": 60,
  "requires_approval": false
}}

Goal: "Fix failing tests"
Plan:
{{
  "steps": [
    {{"tool_name": "analyze_test_failures", "description": "Identify failing tests", "params": {{}}}},
    {{"tool_name": "read_files", "description": "Read test files", "params": {{}}}},
    {{"tool_name": "fix_code", "description": "Fix test failures", "params": {{}}}},
    {{"tool_name": "run_tests", "description": "Verify fixes", "params": {{}}}}
  ],
  "estimated_duration": 45,
  "requires_approval": false
}}

Now create a plan for the user's goal."""

        # Ask LLM to create plan with JSON mode if supported
        # Try to use response_format for OpenAI models
        if hasattr(self.llm, 'client'):  # OpenAI provider
            # Use OpenAI's JSON mode for guaranteed JSON response
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Goal: {goal}"}
            ]

            try:
                # Use direct OpenAI client with response_format
                # Add timeout to prevent hanging
                completion = await asyncio.wait_for(
                    self.llm.client.chat.completions.create(
                        model=self.llm.config.model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.1,  # Lower temp for more consistent JSON
                        stream=False
                    ),
                    timeout=30.0  # 30 second timeout
                )
                plan_text = completion.choices[0].message.content
            except (Exception, asyncio.TimeoutError) as e:
                # Fallback to regular send_message
                print(f"[DEBUG] OpenAI JSON mode failed ({type(e).__name__}), using fallback")
                response = self.llm.send_message(
                    message=f"Goal: {goal}",
                    system_prompt=system_prompt,
                    tools=[]
                )
                plan_text = ""
                async for event in response:
                    if event["type"] == "text":
                        plan_text += event["content"]
        else:
            # For non-OpenAI providers, use regular method
            response = self.llm.send_message(
                message=f"Goal: {goal}",
                system_prompt=system_prompt,
                tools=[]  # No tool use, just JSON response
            )
            plan_text = ""
            async for event in response:
                if event["type"] == "text":
                    plan_text += event["content"]

        # Parse JSON plan
        # Clean up response - remove markdown code blocks if present
        plan_text = plan_text.strip()
        if plan_text.startswith("```json"):
            plan_text = plan_text[7:]  # Remove ```json
        elif plan_text.startswith("```"):
            plan_text = plan_text[3:]  # Remove ```
        if plan_text.endswith("```"):
            plan_text = plan_text[:-3]  # Remove trailing ```
        plan_text = plan_text.strip()

        try:
            plan_data = json.loads(plan_text)
            steps = [
                ExecutionStep(
                    tool_name=step["tool_name"],
                    description=step["description"],
                    params=step.get("params", {})
                )
                for step in plan_data["steps"]
            ]

            return WorkflowPlan(
                goal=goal,
                steps=steps,
                estimated_duration=plan_data.get("estimated_duration"),
                requires_approval=plan_data.get("requires_approval", False)
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: return error plan indicating parsing failed
            # CLI should handle this by falling back to normal conversation mode
            return WorkflowPlan(
                goal=goal,
                steps=[
                    ExecutionStep(
                        tool_name="_parse_error",
                        description="Failed to parse orchestration plan",
                        params={"error": str(e), "plan_text": plan_text[:200]}
                    )
                ],
                requires_approval=False
            )

    async def execute_plan(self, plan: WorkflowPlan) -> List[Dict[str, Any]]:
        """Execute a workflow plan step by step.

        Args:
            plan: WorkflowPlan to execute

        Returns:
            List of step results
        """
        results = []

        for step in plan.steps:
            step.status = StepStatus.RUNNING

            try:
                # Get tool
                tool = self.tools.get(step.tool_name)
                if not tool:
                    step.status = StepStatus.FAILED
                    step.error = f"Tool '{step.tool_name}' not found"
                    results.append({
                        'success': False,
                        'step': step.description,
                        'error': step.error
                    })
                    continue

                # Execute tool
                if asyncio.iscoroutinefunction(tool.executor):
                    result = await tool.executor(**step.params)
                else:
                    result = tool.executor(**step.params)

                step.result = result
                step.status = StepStatus.COMPLETED

                results.append({
                    'success': True,
                    'step': step.description,
                    'result': result
                })

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)

                results.append({
                    'success': False,
                    'step': step.description,
                    'error': str(e)
                })

                # Decide whether to continue or stop
                should_continue = await self.should_continue_after_failure(
                    plan, step, e
                )
                if not should_continue:
                    break

        return results

    async def should_continue_after_failure(
        self,
        plan: WorkflowPlan,
        failed_step: ExecutionStep,
        error: Exception
    ) -> bool:
        """Decide whether to continue execution after a step fails.

        Args:
            plan: Current workflow plan
            failed_step: The step that failed
            error: The error that occurred

        Returns:
            True if execution should continue, False otherwise
        """
        # For now, simple logic: stop on critical failures
        critical_tools = {'delete_file', 'run_command'}

        if failed_step.tool_name in critical_tools:
            return False

        # Otherwise, try to continue
        return True

    async def generate_summary(
        self,
        plan: WorkflowPlan,
        results: List[Dict[str, Any]]
    ) -> str:
        """Generate a human-readable summary of execution.

        Args:
            plan: The executed plan
            results: Results from execution

        Returns:
            Summary text
        """
        completed = sum(1 for r in results if r['success'])
        failed = len(results) - completed

        summary_parts = [f"Goal: {plan.goal}\n"]

        if failed == 0:
            summary_parts.append(f"✓ All {completed} steps completed successfully\n")
        else:
            summary_parts.append(f"⚠ {completed} completed, {failed} failed\n")

        summary_parts.append("\nSteps:")
        for result in results:
            status = "✓" if result['success'] else "✗"
            summary_parts.append(f"  {status} {result['step']}")
            if not result['success'] and 'error' in result:
                summary_parts.append(f"     Error: {result['error']}")

        return "\n".join(summary_parts)

    def get_execution_context(self) -> Dict[str, Any]:
        """Get current execution context for debugging.

        Returns:
            Dict with current state
        """
        return {
            'current_plan': self.current_plan.to_dict() if self.current_plan else None,
            'registered_tools': list(self.tools.keys()),
            'execution_history': len(self.execution_history)
        }
