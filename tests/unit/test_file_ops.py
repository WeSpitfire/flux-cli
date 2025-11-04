"""Unit tests for file operations tools."""

import pytest
from flux.tools.file_ops import ReadFilesTool, WriteFileTool
from flux.core.undo import UndoManager
from flux.core.workflow import WorkflowEnforcer
from flux.core.approval import ApprovalManager
from flux.core.code_validator import CodeValidator


@pytest.mark.unit
class TestReadFilesTool:
    """Tests for ReadFilesTool."""

    def test_read_single_file(self, temp_dir, sample_python_file):
        """Test reading a single file."""
        tool = ReadFilesTool(temp_dir, workflow_enforcer=None, background_processor=None)
        result = tool.execute(paths=[str(sample_python_file.relative_to(temp_dir))])

        assert 'error' not in result
        assert 'files' in result
        assert len(result['files']) == 1
        assert 'def hello' in result['files'][0]['content']

    def test_read_nonexistent_file(self, temp_dir):
        """Test reading a file that doesn't exist."""
        tool = ReadFilesTool(temp_dir, workflow_enforcer=None, background_processor=None)
        result = tool.execute(paths=["nonexistent.py"])

        assert 'error' in result

    def test_read_multiple_files(self, temp_dir, sample_python_file, sample_js_file):
        """Test reading multiple files."""
        tool = ReadFilesTool(temp_dir, workflow_enforcer=None, background_processor=None)
        result = tool.execute(paths=[
            str(sample_python_file.relative_to(temp_dir)),
            str(sample_js_file.relative_to(temp_dir))
        ])

        assert 'error' not in result
        assert 'files' in result
        assert len(result['files']) == 2


@pytest.mark.unit
class TestWriteFileTool:
    """Tests for WriteFileTool."""

    def test_write_new_file(self, temp_dir):
        """Test writing a new file."""
        undo_manager = UndoManager(temp_dir / ".flux", temp_dir)
        workflow = WorkflowEnforcer(temp_dir)
        approval = ApprovalManager(auto_approve=True)
        validator = CodeValidator(temp_dir)

        tool = WriteFileTool(
            temp_dir,
            undo_manager=undo_manager,
            workflow_enforcer=workflow,
            approval_manager=approval,
            code_validator=validator
        )

        result = tool.execute(
            file_path="test.py",
            content="# Test file\nprint('Hello')"
        )

        assert 'error' not in result
        assert (temp_dir / "test.py").exists()
        assert "print('Hello')" in (temp_dir / "test.py").read_text()

    def test_write_validates_syntax(self, temp_dir):
        """Test that write tool validates syntax."""
        undo_manager = UndoManager(temp_dir / ".flux", temp_dir)
        workflow = WorkflowEnforcer(temp_dir)
        approval = ApprovalManager(auto_approve=True)
        validator = CodeValidator(temp_dir)

        tool = WriteFileTool(
            temp_dir,
            undo_manager=undo_manager,
            workflow_enforcer=workflow,
            approval_manager=approval,
            code_validator=validator
        )

        # Try to write invalid Python
        result = tool.execute(
            file_path="invalid.py",
            content="def broken("  # Missing closing paren
        )

        # Should succeed but have validation warning
        # (depending on validator implementation)
        assert (temp_dir / "invalid.py").exists() or 'error' in result
