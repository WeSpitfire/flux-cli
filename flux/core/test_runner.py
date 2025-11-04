"""Smart test runner with automatic framework detection and result parsing."""

import subprocess
import re
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    UNKNOWN = "unknown"


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestFailure:
    """Represents a test failure."""
    test_name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    error_message: str = ""
    error_type: str = ""
    traceback: str = ""


@dataclass
class TestResult:
    """Results from a test run."""
    framework: TestFramework
    status: TestStatus
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    failures: List[TestFailure] = field(default_factory=list)
    output: str = ""
    exit_code: int = 0

    @property
    def success(self) -> bool:
        """Check if all tests passed."""
        return self.failed == 0 and self.status == TestStatus.PASSED

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


class TestRunner:
    """Smart test runner with framework detection and result parsing."""

    def __init__(self, cwd: Path):
        """Initialize test runner.

        Args:
            cwd: Current working directory
        """
        self.cwd = cwd
        self.framework = self._detect_framework()
        self.last_result: Optional[TestResult] = None

    def _detect_framework(self) -> TestFramework:
        """Detect the test framework used in the project."""
        # Check for Python test frameworks
        if (self.cwd / "pytest.ini").exists() or (self.cwd / "pyproject.toml").exists():
            # Check if pytest is mentioned in pyproject.toml
            pyproject = self.cwd / "pyproject.toml"
            if pyproject.exists():
                try:
                    content = pyproject.read_text()
                    if "pytest" in content:
                        return TestFramework.PYTEST
                except Exception:
                    pass

        # Check for setup.py with test requirements
        setup_py = self.cwd / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                if "pytest" in content:
                    return TestFramework.PYTEST
            except Exception:
                pass

        # Check for JavaScript/TypeScript test frameworks
        package_json = self.cwd / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                    if "jest" in deps:
                        return TestFramework.JEST
                    elif "mocha" in deps:
                        return TestFramework.MOCHA
                    elif "vitest" in deps:
                        return TestFramework.VITEST
            except Exception:
                pass

        # Look for test directories
        if (self.cwd / "tests").exists() or (self.cwd / "test").exists():
            # Default to pytest for Python projects
            if any((self.cwd / "tests").glob("*.py")) if (self.cwd / "tests").exists() else False:
                return TestFramework.PYTEST
            # Check unittest pattern
            if any((self.cwd / "tests").glob("test_*.py")) if (self.cwd / "tests").exists() else False:
                return TestFramework.UNITTEST

        return TestFramework.UNKNOWN

    def get_test_command(self, file_filter: Optional[str] = None) -> Optional[str]:
        """Get the appropriate test command for the detected framework.

        Args:
            file_filter: Optional file or directory to filter tests

        Returns:
            Test command string or None if framework unknown
        """
        if self.framework == TestFramework.PYTEST:
            cmd = "pytest -v"
            if file_filter:
                cmd += f" {file_filter}"
            return cmd

        elif self.framework == TestFramework.UNITTEST:
            if file_filter:
                return f"python -m unittest {file_filter}"
            return "python -m unittest discover"

        elif self.framework == TestFramework.JEST:
            cmd = "npm test --"
            if file_filter:
                cmd += f" {file_filter}"
            return cmd

        elif self.framework == TestFramework.MOCHA:
            cmd = "npm test"
            if file_filter:
                cmd += f" -- {file_filter}"
            return cmd

        elif self.framework == TestFramework.VITEST:
            cmd = "npm run test"
            if file_filter:
                cmd += f" -- {file_filter}"
            return cmd

        return None

    def run_tests(
        self,
        file_filter: Optional[str] = None,
        timeout: int = 60
    ) -> TestResult:
        """Run tests and parse results.

        Args:
            file_filter: Optional file or directory to filter tests
            timeout: Maximum execution time in seconds

        Returns:
            TestResult with parsed information
        """
        cmd = self.get_test_command(file_filter)

        if not cmd:
            return TestResult(
                framework=self.framework,
                status=TestStatus.ERROR,
                output="No test command available for this framework"
            )

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = result.stdout + result.stderr

            # Parse results based on framework
            test_result = self._parse_output(output, result.returncode)
            test_result.exit_code = result.returncode

            self.last_result = test_result
            return test_result

        except subprocess.TimeoutExpired:
            return TestResult(
                framework=self.framework,
                status=TestStatus.ERROR,
                output=f"Tests timed out after {timeout} seconds"
            )
        except Exception as e:
            return TestResult(
                framework=self.framework,
                status=TestStatus.ERROR,
                output=f"Error running tests: {str(e)}"
            )

    def _parse_output(self, output: str, exit_code: int) -> TestResult:
        """Parse test output based on framework.

        Args:
            output: Raw test output
            exit_code: Process exit code

        Returns:
            Parsed TestResult
        """
        if self.framework == TestFramework.PYTEST:
            return self._parse_pytest_output(output, exit_code)
        elif self.framework == TestFramework.JEST:
            return self._parse_jest_output(output, exit_code)
        elif self.framework == TestFramework.UNITTEST:
            return self._parse_unittest_output(output, exit_code)
        else:
            # Generic parsing for unknown frameworks
            return TestResult(
                framework=self.framework,
                status=TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED,
                output=output,
                exit_code=exit_code
            )

    def _parse_pytest_output(self, output: str, exit_code: int) -> TestResult:
        """Parse pytest output."""
        result = TestResult(
            framework=TestFramework.PYTEST,
            output=output
        )

        # Parse summary line: "5 passed, 2 failed in 1.23s"
        summary_pattern = r'(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?(?: in ([\d.]+)s)?'
        summary_match = re.search(summary_pattern, output)

        if summary_match:
            result.passed = int(summary_match.group(1))
            result.failed = int(summary_match.group(2)) if summary_match.group(2) else 0
            result.skipped = int(summary_match.group(3)) if summary_match.group(3) else 0
            result.duration = float(summary_match.group(4)) if summary_match.group(4) else 0.0
            result.total_tests = result.passed + result.failed + result.skipped

        # Parse failures
        failure_pattern = r'FAILED (.*?)::(.*?) - (.*?)(?:\n|$)'
        for match in re.finditer(failure_pattern, output):
            file_path = match.group(1)
            test_name = match.group(2)
            error_msg = match.group(3)

            result.failures.append(TestFailure(
                test_name=test_name,
                file_path=file_path,
                error_message=error_msg
            ))

        # Determine status
        if result.failed > 0:
            result.status = TestStatus.FAILED
        elif exit_code == 0:
            result.status = TestStatus.PASSED
        else:
            result.status = TestStatus.ERROR

        return result

    def _parse_jest_output(self, output: str, exit_code: int) -> TestResult:
        """Parse Jest output."""
        result = TestResult(
            framework=TestFramework.JEST,
            output=output
        )

        # Parse test summary: "Tests: 2 failed, 5 passed, 7 total"
        summary_pattern = r'Tests:\s+(?:(\d+) failed,?\s*)?(?:(\d+) passed,?\s*)?(\d+) total'
        summary_match = re.search(summary_pattern, output)

        if summary_match:
            result.failed = int(summary_match.group(1)) if summary_match.group(1) else 0
            result.passed = int(summary_match.group(2)) if summary_match.group(2) else 0
            result.total_tests = int(summary_match.group(3))
            result.skipped = result.total_tests - result.passed - result.failed

        # Parse duration
        time_pattern = r'Time:\s+([\d.]+)\s*s'
        time_match = re.search(time_pattern, output)
        if time_match:
            result.duration = float(time_match.group(1))

        # Parse failures
        failure_pattern = r'●\s+(.*?)\n\n\s+(.*?)(?=\n\n|\Z)'
        for match in re.finditer(failure_pattern, output, re.DOTALL):
            test_name = match.group(1).strip()
            error_msg = match.group(2).strip()

            result.failures.append(TestFailure(
                test_name=test_name,
                error_message=error_msg
            ))

        # Determine status
        if result.failed > 0:
            result.status = TestStatus.FAILED
        elif exit_code == 0:
            result.status = TestStatus.PASSED
        else:
            result.status = TestStatus.ERROR

        return result

    def _parse_unittest_output(self, output: str, exit_code: int) -> TestResult:
        """Parse unittest output."""
        result = TestResult(
            framework=TestFramework.UNITTEST,
            output=output
        )

        # Parse summary line: "Ran 10 tests in 0.123s"
        ran_pattern = r'Ran (\d+) test'
        ran_match = re.search(ran_pattern, output)
        if ran_match:
            result.total_tests = int(ran_match.group(1))

        # Parse time
        time_pattern = r'in ([\d.]+)s'
        time_match = re.search(time_pattern, output)
        if time_match:
            result.duration = float(time_match.group(1))

        # Check for OK or FAILED
        if "OK" in output:
            result.status = TestStatus.PASSED
            result.passed = result.total_tests
        elif "FAILED" in output:
            result.status = TestStatus.FAILED
            # Parse failure count
            fail_pattern = r'failures=(\d+)'
            fail_match = re.search(fail_pattern, output)
            if fail_match:
                result.failed = int(fail_match.group(1))
                result.passed = result.total_tests - result.failed
        else:
            result.status = TestStatus.ERROR if exit_code != 0 else TestStatus.PASSED

        return result

    def get_test_files_for_source(self, source_file: Path) -> List[Path]:
        """Find test files related to a source file.

        Args:
            source_file: Path to source file

        Returns:
            List of related test file paths
        """
        test_files = []
        file_name = source_file.stem

        # Common test file patterns
        test_patterns = [
            f"test_{file_name}.py",
            f"{file_name}_test.py",
            f"test_{file_name}.js",
            f"{file_name}.test.js",
            f"{file_name}.spec.js",
        ]

        # Search in common test directories
        test_dirs = [
            self.cwd / "tests",
            self.cwd / "test",
            self.cwd / "__tests__",
            source_file.parent / "__tests__",
        ]

        for test_dir in test_dirs:
            if test_dir.exists():
                for pattern in test_patterns:
                    test_file = test_dir / pattern
                    if test_file.exists():
                        test_files.append(test_file)

        return test_files


class AutoTester(TestRunner):
    """Automatically runs tests to verify fixes.

    Extends TestRunner to add automatic test execution after fixes are applied.
    Useful for self-healing systems that need to validate fixes.
    """

    def __init__(self, cwd: Path):
        """Initialize AutoTester.

        Args:
            cwd: Current working directory
        """
        super().__init__(cwd)

    async def run_auto_tests(self, fix_applied_callback: Optional[callable] = None) -> TestResult:
        """Run tests automatically after a fix is applied.

        Args:
            fix_applied_callback: Optional callback to execute after a fix is applied.
                                 This can be used to apply the fix before running tests.

        Returns:
            TestResult with parsed information about test execution
        """
        # Execute the fix callback if provided
        if fix_applied_callback:
            if asyncio.iscoroutinefunction(fix_applied_callback):
                await fix_applied_callback()
            else:
                fix_applied_callback()

        # Run tests using parent TestRunner
        result = self.run_tests()

        # Log the result to console
        if result.success:
            print(f"✓ All {result.passed} tests passed successfully.")
        else:
            print(f"✗ {result.failed}/{result.total_tests} tests failed:")
            for failure in result.failures:
                print(f"  - {failure.test_name}: {failure.error_message}")

        return result
