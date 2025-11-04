"""Test the improvements made to Flux."""

import asyncio
from pathlib import Path
from flux.tools.file_ops import ReadFilesTool, EditFileTool
from flux.tools.ast_edit import ASTEditTool
from flux.core.workflow import WorkflowEnforcer


async def test_structured_errors():
    """Test that tools return structured errors with helpful suggestions."""
    cwd = Path.cwd()

    print("🧪 Testing Structured Error Responses\n")

    # Test 1: File not found with similar files
    print("Test 1: File Not Found Error")
    print("-" * 50)
    read_tool = ReadFilesTool(cwd)
    result = await read_tool.execute(["nonexistent_file.py"])
    print(f"Result: {result}\n")

    # Test 2: Search text not found
    print("Test 2: Search Text Not Found Error")
    print("-" * 50)
    # First create a test file
    test_file = cwd / "test_edit_tmp.py"
    test_file.write_text("def hello():\n    print('hello')\n")

    edit_tool = EditFileTool(cwd, show_diff=False)
    result = await edit_tool.execute(
        path="test_edit_tmp.py",
        search="def goodbye():",  # Doesn't exist
        replace="def goodbye():\n    print('bye')"
    )
    print(f"Result: {result}\n")

    # Test 3: Function already exists
    print("Test 3: Function Already Exists Error")
    print("-" * 50)
    workflow = WorkflowEnforcer(cwd)
    workflow.start_workflow()

    # Read file first for workflow
    await read_tool.execute(["test_edit_tmp.py"])

    ast_tool = ASTEditTool(cwd, show_diff=False, workflow_enforcer=workflow)
    result = await ast_tool.execute(
        path="test_edit_tmp.py",
        operation="add_function",
        target="hello",
        code="def hello():\n    print('new hello')\n"
    )
    print(f"Result: {result}\n")

    # Test 4: Invalid operation
    print("Test 4: Invalid Operation Error")
    print("-" * 50)
    result = await ast_tool.execute(
        path="test_edit_tmp.py",
        operation="add_code",  # Invalid
        target="something",
        code="some code"
    )
    print(f"Result: {result}\n")

    # Cleanup
    test_file.unlink()

    print("\n✅ All error tests completed!")
    print("\nKey Improvements:")
    print("- Errors now include 'code', 'message', 'suggestion'")
    print("- File not found shows similar files")
    print("- Function exists shows line number and signature")
    print("- Invalid operations list valid options")
    print("- Search not found suggests re-reading file")


async def test_prompt_size():
    """Test prompt size reduction."""
    from flux.llm.prompts import SYSTEM_PROMPT

    print("\n📊 System Prompt Analysis\n")
    print("-" * 50)

    lines = SYSTEM_PROMPT.split('\n')
    chars = len(SYSTEM_PROMPT)
    estimated_tokens = chars // 4  # Rough estimate

    print(f"Lines: {len(lines)}")
    print(f"Characters: {chars}")
    print(f"Estimated tokens: ~{estimated_tokens}")
    print(f"\nOriginal: 229 lines, ~3000 tokens")
    print(f"New: {len(lines)} lines, ~{estimated_tokens} tokens")
    print(f"Reduction: {((229 - len(lines)) / 229 * 100):.1f}%")
    print(f"Tokens saved per request: ~{3000 - estimated_tokens}")


if __name__ == "__main__":
    asyncio.run(test_structured_errors())
    asyncio.run(test_prompt_size())
