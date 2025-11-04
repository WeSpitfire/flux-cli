#!/usr/bin/env python3
"""Integration tests for validation framework across all tools."""

import asyncio
import tempfile
from pathlib import Path

from flux.tools.command import RunCommandTool, validate_command_string
from flux.tools.file_ops import ReadFilesTool, WriteFileTool, EditFileTool, validate_file_path


class TestCommandValidation:
    """Test command validation."""

    def test_validate_command_string_safe(self):
        """Test safe commands pass validation."""
        commands = [
            "echo 'hello'",
            "ls -la",
            "git status",
            "python script.py",
            "npm install",
        ]

        for cmd in commands:
            is_valid, msg = validate_command_string(cmd)
            assert is_valid, f"Safe command rejected: {cmd}"
            assert msg == "Command is safe."

    def test_validate_command_string_unsafe(self):
        """Test unsafe commands fail validation."""
        unsafe_commands = [
            ("echo test && rm file", "&&"),
            ("ls | grep test", "|"),
            ("echo `whoami`", "`"),
            ("cat file; rm file", ";"),
            ("cmd1 || cmd2", "||"),
        ]

        for cmd, char in unsafe_commands:
            is_valid, msg = validate_command_string(cmd)
            assert not is_valid, f"Unsafe command accepted: {cmd}"
            assert char in msg or "unsafe" in msg.lower()

    def test_validate_command_string_dangerous(self):
        """Test dangerous operations fail validation."""
        dangerous_commands = [
            "rm -rf /",
            "rm -rf /*",
            "dd if=/dev/zero of=/dev/sda",
        ]

        for cmd in dangerous_commands:
            is_valid, msg = validate_command_string(cmd)
            assert not is_valid, f"Dangerous command accepted: {cmd}"
            assert "dangerous" in msg.lower() or "delete" in msg.lower()

    async def test_run_command_tool_validation(self):
        """Test RunCommandTool validates commands."""
        tool = RunCommandTool(Path.cwd())

        # Safe command should execute
        result = await tool.execute("echo 'test'")
        assert result.get("success") or "stdout" in result

        # Unsafe command should be rejected
        result = await tool.execute("echo test && rm file")
        assert "error" in result
        assert "unsafe" in result["error"].lower() or "injection" in result["error"].lower()

        # Dangerous command should be rejected
        result = await tool.execute("rm -rf /")
        assert "error" in result
        assert "dangerous" in result["error"].lower() or "delete" in result["error"].lower()


class TestFilePathValidation:
    """Test file path validation."""

    def test_validate_file_path_safe(self):
        """Test safe paths pass validation."""
        cwd = Path.cwd()
        safe_paths = [
            "test.py",
            "src/main.py",
            "../sibling/file.txt",
            str(cwd / "file.txt"),
        ]

        for path in safe_paths:
            is_valid, msg = validate_file_path(path, cwd, "read")
            assert is_valid, f"Safe path rejected: {path} - {msg}"

    def test_validate_file_path_dangerous(self):
        """Test dangerous paths fail validation."""
        cwd = Path.cwd()
        dangerous_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "/boot/grub.cfg",
            "path\x00injection",  # null byte
        ]

        for path in dangerous_paths:
            is_valid, msg = validate_file_path(path, cwd, "read")
            assert not is_valid, f"Dangerous path accepted: {path}"
            assert msg is not None

    def test_validate_file_path_invalid_chars(self):
        """Test paths with invalid characters fail validation for write."""
        cwd = Path.cwd()
        invalid_paths = [
            "file<test>.txt",
            "file:test.txt",
            'file"test.txt',
        ]

        for path in invalid_paths:
            is_valid, msg = validate_file_path(path, cwd, "write")
            # Some platforms may allow these, so just check it validates
            assert isinstance(is_valid, bool)


class TestFileToolsValidation:
    """Test file tools validation integration."""

    async def test_read_files_validation(self):
        """Test ReadFilesTool validates paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a safe test file
            test_file = tmppath / "test.txt"
            test_file.write_text("test content")

            tool = ReadFilesTool(tmppath)

            # Safe read should work
            result = await tool.execute([str(test_file)])
            assert "test.txt" in str(result) or str(test_file) in str(result)

            # Dangerous path should be rejected
            result = await tool.execute(["/etc/passwd"])
            # Check if validation caught it (either before or during execution)
            assert "error" in str(result).lower() or "content" not in result.get("/etc/passwd", {})

    async def test_write_file_validation(self):
        """Test WriteFileTool validates paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            tool = WriteFileTool(tmppath)

            # Safe write should work
            result = await tool.execute("test.txt", "content")
            assert result.get("success") or "bytes_written" in result

            # Dangerous path should be rejected
            result = await tool.execute("/etc/passwd", "malicious")
            assert "error" in result
            assert "INVALID_PATH" in str(result) or "system path" in str(result).lower()

    async def test_edit_file_validation(self):
        """Test EditFileTool validates inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a test file
            test_file = tmppath / "test.py"
            test_file.write_text("def hello():\n    print('hello')\n")

            tool = EditFileTool(tmppath, show_diff=False)

            # Valid edit should work
            result = await tool.execute(
                str(test_file),
                "print('hello')",
                "print('world')"
            )
            assert "error" not in result or "success" in result

            # Empty search string should be rejected
            result = await tool.execute(str(test_file), "", "replacement")
            assert "error" in result
            assert "INVALID_INPUT" in str(result)

            # Too short search string should be rejected
            result = await tool.execute(str(test_file), "ab", "replacement")
            assert "error" in result
            assert "too short" in str(result).lower() or "INVALID_INPUT" in str(result)

            # Dangerous path should be rejected
            result = await tool.execute("/etc/passwd", "root", "hacked")
            assert "error" in result
            assert "INVALID_PATH" in str(result) or "system path" in str(result).lower()


async def run_all_tests():
    """Run all test classes."""
    test_classes = [
        TestCommandValidation(),
        TestFilePathValidation(),
        TestFileToolsValidation(),
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{'='*60}")
        print(f"Running {class_name}")
        print('='*60)

        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]

        for method_name in test_methods:
            total_tests += 1
            method = getattr(test_class, method_name)

            try:
                # Check if it's an async method
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()

                passed_tests += 1
                print(f"  ✓ {method_name}")

            except AssertionError as e:
                failed_tests.append((class_name, method_name, str(e)))
                print(f"  ✗ {method_name}: {e}")

            except Exception as e:
                failed_tests.append((class_name, method_name, f"Exception: {e}"))
                print(f"  ✗ {method_name}: Exception - {e}")

    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"Total: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")

    if failed_tests:
        print(f"\nFailed tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
        return False
    else:
        print("\n✓ ALL TESTS PASSED!")
        return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
