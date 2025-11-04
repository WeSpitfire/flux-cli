"""Smart Task Planner - Autonomous task decomposition with context awareness.

This replaces the rigid orchestrator with an intelligent planner that:
1. Analyzes task complexity
2. Gathers necessary context BEFORE planning
3. Breaks tasks into validated steps
4. Executes incrementally with self-correction
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json


@dataclass
class TaskStep:
    """A single step in task execution."""
    step_number: int
    description: str
    rationale: str  # Why this step is needed
    requires_context: List[str]  # Files/info needed before execution
    action: str  # What to do (read, create, edit, etc.)
    validation: str  # How to verify success
    completed: bool = False
    result: Optional[Any] = None


@dataclass
class TaskPlan:
    """A complete task execution plan."""
    goal: str
    complexity: str  # "simple", "medium", "complex"
    requires_context: List[str]  # Files to read before starting
    steps: List[TaskStep]
    current_step: int = 0

    def next_step(self) -> Optional[TaskStep]:
        """Get the next incomplete step."""
        for step in self.steps:
            if not step.completed:
                return step
        return None


class TaskPlanner:
    """
    Intelligent task planner that decomposes complex tasks.

    Key differences from orchestrator:
    - Analyzes BEFORE planning (gathers context)
    - Plans incrementally (adapts as it learns)
    - Validates each step (no stub code)
    - Self-corrects on failures
    """

    def __init__(self, llm_provider, codebase_graph=None):
        """Initialize task planner.

        Args:
            llm_provider: LLM for planning and analysis
            codebase_graph: Optional codebase graph for intelligent context
        """
        self.llm = llm_provider
        self.codebase_graph = codebase_graph

    async def should_decompose(self, query: str) -> tuple[bool, str]:
        """Determine if a task should be decomposed.

        Args:
            query: User's query

        Returns:
            (should_decompose, complexity_reason)
        """
        # Simple heuristic-based detection for now
        # In future, can use LLM for smarter detection

        # Indicators of complex tasks
        complex_patterns = [
            "build", "create", "implement", "add feature", "add a",
            "refactor and", "fix and", "update and",
            "make a", "develop", "write a"
        ]

        # Indicators of simple tasks
        simple_patterns = [
            "what is", "why", "how does", "explain",
            "show me", "where", "find"
        ]

        query_lower = query.lower()

        # Check for simple patterns first
        for pattern in simple_patterns:
            if pattern in query_lower:
                return False, f"Query contains '{pattern}' - likely a question"

        # Check for complex patterns
        for pattern in complex_patterns:
            if pattern in query_lower:
                # Additional check: Does it involve multiple components?
                if " and " in query_lower or len(query.split()) > 10:
                    return True, f"Query contains '{pattern}' with multiple requirements"

        # Default: Don't decompose
        return False, "Query appears to be straightforward"

    async def analyze_and_plan(self, goal: str) -> TaskPlan:
        """Analyze a goal and create a validated execution plan.

        This is the SMART version - it gathers context first!

        Args:
            goal: User's goal

        Returns:
            TaskPlan with context-aware steps
        """
        # Step 1: Use LLM to identify what context is needed
        context_prompt = f"""Given this goal: "{goal}"

What files or information do you need to understand BEFORE you can plan the implementation?

Think about:
- What existing code/patterns should be followed?
- What components/classes need to be understood?
- What similar implementations exist?

Respond with ONLY a JSON array of file paths or queries:
["path/to/file.py", "search: how X works"]

Be minimal - only request essential context."""

        # Get context requirements from LLM
        context_items = await self._get_llm_response(context_prompt)

        # Step 2: Parse and gather actual context
        try:
            context_list = json.loads(context_items)
        except json.JSONDecodeError:
            # Fallback: No context
            context_list = []

        # Step 3: Use LLM to create execution plan WITH context
        planning_prompt = f"""Goal: {goal}

Required context has been gathered. Now create a step-by-step execution plan.

CRITICAL RULES:
1. Each step should be SPECIFIC and ACTIONABLE
2. NO stub code - every step must produce working code
3. Read files BEFORE editing them (100% of time)
4. Each step should be independently verifiable
5. Steps should build on each other

Respond with ONLY valid JSON:
{{
  "complexity": "simple|medium|complex",
  "steps": [
    {{
      "step_number": 1,
      "description": "Specific action to take",
      "rationale": "Why this step is needed",
      "requires_context": ["files to read first"],
      "action": "read|create|edit|test",
      "validation": "How to verify success"
    }}
  ]
}}"""

        # Get plan from LLM
        plan_json = await self._get_llm_response(planning_prompt)

        # Step 4: Parse and create TaskPlan
        try:
            plan_data = json.loads(plan_json)
            steps = [
                TaskStep(
                    step_number=s["step_number"],
                    description=s["description"],
                    rationale=s.get("rationale", ""),
                    requires_context=s.get("requires_context", []),
                    action=s.get("action", "unknown"),
                    validation=s.get("validation", "")
                )
                for s in plan_data.get("steps", [])
            ]

            return TaskPlan(
                goal=goal,
                complexity=plan_data.get("complexity", "medium"),
                requires_context=context_list,
                steps=steps
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: Create simple plan
            return TaskPlan(
                goal=goal,
                complexity="simple",
                requires_context=[],
                steps=[
                    TaskStep(
                        step_number=1,
                        description=f"Complete goal: {goal}",
                        rationale="Fallback to single-step execution",
                        requires_context=[],
                        action="execute",
                        validation="Task completed"
                    )
                ]
            )

    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM.

        Args:
            prompt: Prompt to send

        Returns:
            LLM response text
        """
        response_text = ""

        async for event in self.llm.send_message(
            message=prompt,
            system_prompt="You are a task planning assistant. Be concise and respond with JSON when requested.",
            tools=None  # No tools for planning
        ):
            if event["type"] == "text":
                response_text += event["content"]

        return response_text.strip()

    async def replan_on_failure(self, plan: TaskPlan, failed_step: TaskStep, error: str) -> TaskPlan:
        """Adjust plan when a step fails.

        Args:
            plan: Current plan
            failed_step: Step that failed
            error: Error message

        Returns:
            Updated plan with adjusted steps
        """
        replan_prompt = f"""The following step failed:
Step {failed_step.step_number}: {failed_step.description}
Error: {error}

Original goal: {plan.goal}
Completed steps: {[s.description for s in plan.steps if s.completed]}

Create an adjusted plan to recover and complete the goal.

Respond with JSON:
{{
  "steps": [
    {{
      "step_number": N,
      "description": "...",
      "rationale": "...",
      "requires_context": [],
      "action": "...",
      "validation": "..."
    }}
  ]
}}"""

        plan_json = await self._get_llm_response(replan_prompt)

        try:
            plan_data = json.loads(plan_json)
            new_steps = [
                TaskStep(
                    step_number=s["step_number"],
                    description=s["description"],
                    rationale=s.get("rationale", "Recovery step"),
                    requires_context=s.get("requires_context", []),
                    action=s.get("action", "unknown"),
                    validation=s.get("validation", "")
                )
                for s in plan_data.get("steps", [])
            ]

            # Keep completed steps, replace remaining with new plan
            completed = [s for s in plan.steps if s.completed]
            plan.steps = completed + new_steps
            plan.current_step = len(completed)

            return plan
        except (json.JSONDecodeError, KeyError):
            # Fallback: Keep original plan
            return plan
