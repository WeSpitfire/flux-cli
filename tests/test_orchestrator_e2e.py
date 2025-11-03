"""End-to-end tests for AI Orchestrator.

Tests complete workflows to ensure orchestration works seamlessly:
- Run tests workflow
- Fix failing tests workflow
- Build feature workflow
- Auto-fix workflow
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from flux.core.orchestrator import AIOrchestrator, WorkflowPlan, ExecutionStep, ToolDefinition


@pytest.fixture
def mock_llm():
    """Create mock LLM provider."""
    llm = Mock()

    async def mock_send_message(*args, **kwargs):
        """Mock streaming response."""
        # Return a simple plan as JSON
        yield {"type": "text", "content": '{"steps": [{"tool_name": "run_tests", "description": "Run all tests", "params": {}}], "estimated_duration": 30, "requires_approval": false}'}

    llm.send_message = mock_send_message
    return llm


@pytest.fixture
def orchestrator(mock_llm, tmp_path):
    """Create orchestrator with mocked LLM."""
    return AIOrchestrator(mock_llm, tmp_path)


class TestOrchestratorBasics:
    """Test basic orchestrator functionality."""

    @pytest.mark.asyncio
    async def test_tool_registration(self, orchestrator):
        """Test registering tools with orchestrator."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            executor=lambda: "result",
            schema={"param": {"type": "string"}}
        )

        orchestrator.register_tool(tool)
        assert "test_tool" in orchestrator.tools
        assert orchestrator.tools["test_tool"].name == "test_tool"

    @pytest.mark.asyncio
    async def test_plan_creation(self, orchestrator):
        """Test creating execution plan from natural language."""
        plan = await orchestrator.create_plan("run the tests")

        assert isinstance(plan, WorkflowPlan)
        assert plan.goal == "run the tests"
        assert len(plan.steps) > 0
        assert isinstance(plan.steps[0], ExecutionStep)

    @pytest.mark.asyncio
    async def test_simple_execution(self, orchestrator):
        """Test executing a simple workflow."""
        # Register a simple tool
        executed = []

        def simple_tool():
            executed.append(True)
            return {"success": True, "message": "Done"}

        tool = ToolDefinition(
            name="simple_tool",
            description="A simple tool",
            executor=simple_tool,
            schema={}
        )
        orchestrator.register_tool(tool)

        # Create and execute plan
        plan = WorkflowPlan(
            goal="test goal",
            steps=[
                ExecutionStep(
                    tool_name="simple_tool",
                    description="Run simple tool",
                    params={}
                )
            ]
        )

        results = await orchestrator.execute_plan(plan)

        assert len(results) == 1
        assert results[0]['success'] is True
        assert len(executed) == 1


class TestWorkflowScenarios:
    """Test real-world workflow scenarios."""

    @pytest.mark.asyncio
    async def test_run_tests_workflow(self, orchestrator):
        """Test: 'run the tests' workflow."""
        test_results = {"passed": True, "total": 5, "output": "All tests passed"}

        async def mock_run_tests(**params):
            return test_results

        tool = ToolDefinition(
            name="run_tests",
            description="Run project tests",
            executor=mock_run_tests,
            schema={}
        )
        orchestrator.register_tool(tool)

        # Execute goal
        result = await orchestrator.execute_goal("run the tests", auto_approve=True)

        assert result['success'] is True
        assert len(result['results']) > 0
        assert 'summary' in result

    @pytest.mark.asyncio
    async def test_fix_formatting_workflow(self, orchestrator):
        """Test: 'fix the formatting' workflow."""
        files_fixed = []

        async def mock_auto_fix(**params):
            files_fixed.append("file.py")
            return {"files_fixed": 3, "total_fixes": 7}

        tool = ToolDefinition(
            name="auto_fix",
            description="Fix code formatting",
            executor=mock_auto_fix,
            schema={}
        )
        orchestrator.register_tool(tool)

        # Create plan manually since mock LLM is too simple
        plan = WorkflowPlan(
            goal="fix the formatting",
            steps=[
                ExecutionStep(
                    tool_name="auto_fix",
                    description="Fix code formatting",
                    params={}
                )
            ]
        )

        results = await orchestrator.execute_plan(plan)

        assert len(results) == 1
        assert results[0]['success'] is True
        assert len(files_fixed) > 0

    @pytest.mark.asyncio
    async def test_multi_step_workflow(self, orchestrator):
        """Test multi-step workflow with dependencies."""
        execution_order = []

        async def step1(**params):
            execution_order.append(1)
            return {"status": "done"}

        async def step2(**params):
            execution_order.append(2)
            return {"status": "done"}

        async def step3(**params):
            execution_order.append(3)
            return {"status": "done"}

        orchestrator.register_tool(ToolDefinition("step1", "First step", step1, {}))
        orchestrator.register_tool(ToolDefinition("step2", "Second step", step2, {}))
        orchestrator.register_tool(ToolDefinition("step3", "Third step", step3, {}))

        plan = WorkflowPlan(
            goal="multi-step test",
            steps=[
                ExecutionStep("step1", "Do step 1", {}),
                ExecutionStep("step2", "Do step 2", {}),
                ExecutionStep("step3", "Do step 3", {}),
            ]
        )

        results = await orchestrator.execute_plan(plan)

        assert len(results) == 3
        assert execution_order == [1, 2, 3]  # Verify order
        assert all(r['success'] for r in results)


class TestErrorHandling:
    """Test error handling and recovery."""

    @pytest.mark.asyncio
    async def test_tool_not_found(self, orchestrator):
        """Test handling of missing tool."""
        plan = WorkflowPlan(
            goal="test",
            steps=[
                ExecutionStep("nonexistent_tool", "Use missing tool", {})
            ]
        )

        results = await orchestrator.execute_plan(plan)

        assert len(results) == 1
        assert results[0]['success'] is False
        assert 'not found' in results[0]['error'].lower()

    @pytest.mark.asyncio
    async def test_tool_execution_failure(self, orchestrator):
        """Test handling of tool execution errors."""
        def failing_tool():
            raise ValueError("Tool failed")

        tool = ToolDefinition(
            name="failing_tool",
            description="A tool that fails",
            executor=failing_tool,
            schema={}
        )
        orchestrator.register_tool(tool)

        plan = WorkflowPlan(
            goal="test failure",
            steps=[
                ExecutionStep("failing_tool", "Run failing tool", {})
            ]
        )

        results = await orchestrator.execute_plan(plan)

        assert len(results) == 1
        assert results[0]['success'] is False
        assert 'Tool failed' in results[0]['error']

    @pytest.mark.asyncio
    async def test_partial_success(self, orchestrator):
        """Test workflow with some failed steps."""
        def success_tool():
            return {"status": "ok"}

        def fail_tool():
            raise RuntimeError("Failed")

        orchestrator.register_tool(ToolDefinition("success1", "Success", success_tool, {}))
        orchestrator.register_tool(ToolDefinition("fail", "Fail", fail_tool, {}))
        orchestrator.register_tool(ToolDefinition("success2", "Success", success_tool, {}))

        plan = WorkflowPlan(
            goal="partial failure test",
            steps=[
                ExecutionStep("success1", "First success", {}),
                ExecutionStep("fail", "Failure", {}),
                ExecutionStep("success2", "Second success", {}),
            ]
        )

        results = await orchestrator.execute_plan(plan)

        # Should execute all 3 (unless failure is critical)
        assert len(results) >= 2  # At least first 2
        assert results[0]['success'] is True
        assert results[1]['success'] is False


class TestIntegration:
    """Integration tests with real-like scenarios."""

    @pytest.mark.asyncio
    async def test_complete_feature_workflow(self, orchestrator):
        """Test: 'add login page with validation' workflow."""
        workflow_steps = []

        async def write_file(**params):
            workflow_steps.append(f"write:{params.get('file_path')}")
            return {"success": True}

        async def run_tests(**params):
            workflow_steps.append("test")
            return {"passed": True, "total": 5}

        async def auto_fix(**params):
            workflow_steps.append("autofix")
            return {"files_fixed": 2}

        orchestrator.register_tool(ToolDefinition("write_file", "Create file", write_file, {"file_path": {}, "content": {}}))
        orchestrator.register_tool(ToolDefinition("run_tests", "Run tests", run_tests, {}))
        orchestrator.register_tool(ToolDefinition("auto_fix", "Fix code", auto_fix, {}))

        plan = WorkflowPlan(
            goal="add login page",
            steps=[
                ExecutionStep("write_file", "Create login.html", {"file_path": "login.html", "content": "<html>"}),
                ExecutionStep("write_file", "Create validation.js", {"file_path": "validation.js", "content": "// code"}),
                ExecutionStep("run_tests", "Run tests", {}),
                ExecutionStep("auto_fix", "Fix formatting", {}),
            ]
        )

        results = await orchestrator.execute_plan(plan)

        assert len(results) == 4
        assert all(r['success'] for r in results)
        assert "write:login.html" in workflow_steps
        assert "write:validation.js" in workflow_steps
        assert "test" in workflow_steps
        assert "autofix" in workflow_steps

    @pytest.mark.asyncio
    async def test_fix_failing_tests_workflow(self, orchestrator):
        """Test: 'fix failing tests' workflow."""
        workflow_steps = []

        async def run_tests(**params):
            workflow_steps.append("test")
            # First run: failures, second run: success
            if len([s for s in workflow_steps if s == "test"]) == 1:
                return {"passed": False, "total": 5, "failures": ["test_login"]}
            else:
                return {"passed": True, "total": 5}

        async def read_files(**params):
            workflow_steps.append("read")
            return {"content": "test code"}

        async def edit_file(**params):
            workflow_steps.append("edit")
            return {"success": True}

        orchestrator.register_tool(ToolDefinition("run_tests", "Run tests", run_tests, {}))
        orchestrator.register_tool(ToolDefinition("read_files", "Read files", read_files, {"paths": {}}))
        orchestrator.register_tool(ToolDefinition("edit_file", "Edit file", edit_file, {"path": {}, "old_str": {}, "new_str": {}}))

        plan = WorkflowPlan(
            goal="fix failing tests",
            steps=[
                ExecutionStep("run_tests", "Identify failures", {}),
                ExecutionStep("read_files", "Read test file", {"paths": ["test_login.py"]}),
                ExecutionStep("edit_file", "Fix test", {"path": "test_login.py", "old_str": "old", "new_str": "new"}),
                ExecutionStep("run_tests", "Verify fix", {}),
            ]
        )

        results = await orchestrator.execute_plan(plan)

        assert len(results) == 4
        assert all(r['success'] for r in results)
        assert workflow_steps.count("test") == 2  # Ran tests twice
        assert "read" in workflow_steps
        assert "edit" in workflow_steps


def test_summary_generation(orchestrator):
    """Test execution summary generation."""
    plan = WorkflowPlan(
        goal="test summary",
        steps=[
            ExecutionStep("tool1", "Step 1", {}),
            ExecutionStep("tool2", "Step 2", {}),
        ]
    )

    results = [
        {"success": True, "step": "Step 1"},
        {"success": True, "step": "Step 2"},
    ]

    # Use asyncio.run for async function
    summary = asyncio.run(orchestrator.generate_summary(plan, results))

    assert "test summary" in summary
    assert "2" in summary  # 2 steps
    assert "✓" in summary or "✓" in summary  # Success indicator


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
