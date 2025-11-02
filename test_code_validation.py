#!/usr/bin/env python3
"""Test suite for code validation infrastructure."""

import tempfile
from pathlib import Path

from flux.core.import_analyzer import ImportAnalyzer
from flux.core.code_validator import CodeValidator, ValidationResult


def test_import_analyzer_detects_missing_import():
    """Test that ImportAnalyzer detects missing imports - the Flux error case."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a file with a missing import (like Flux did)
        test_file = tmppath / "command.py"
        test_file.write_text("""
def execute_command(cmd):
    # This function is used but not imported!
    is_valid, msg = validate_command_string(cmd)
    if not is_valid:
        return {"error": msg}
    return {"success": True}
""")
        
        analyzer = ImportAnalyzer(tmppath)
        result = analyzer.analyze_file(test_file)
        
        print("Test: Missing import detection")
        print(f"  File: {test_file.name}")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Missing imports: {result['missing_imports']}")
        
        assert not result["is_valid"], "Should detect missing import"
        assert len(result["missing_imports"]) > 0, "Should list missing imports"
        
        # Check that validate_command_string is in missing imports
        missing_symbols = [m["symbol"] for m in result["missing_imports"]]
        assert "validate_command_string" in missing_symbols, "Should detect validate_command_string"
        
        print("  ✓ Correctly detected missing import for 'validate_command_string'\n")


def test_import_analyzer_suggests_import():
    """Test that ImportAnalyzer can suggest where to import from."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create the function definition file
        validation_file = tmppath / "validation.py"
        validation_file.write_text("""
def validate_command_string(cmd):
    return True, "OK"
""")
        
        # Create a file that uses it without importing
        test_file = tmppath / "command.py"
        test_file.write_text("""
def execute_command(cmd):
    is_valid, msg = validate_command_string(cmd)
    return {"success": is_valid}
""")
        
        analyzer = ImportAnalyzer(tmppath)
        result = analyzer.analyze_file(test_file)
        
        print("Test: Import suggestion")
        print(f"  Missing imports: {result['missing_imports']}")
        print(f"  Suggestions: {result['suggestions']}")
        
        assert not result["is_valid"], "Should detect missing import"
        
        # Should suggest importing from validation.py
        suggestions = result["suggestions"]
        assert len(suggestions) > 0, "Should provide suggestions"
        assert "validation" in str(suggestions), "Should suggest importing from validation"
        
        print("  ✓ Correctly suggested importing from validation.py\n")


def test_code_validator_detects_syntax_errors():
    """Test that CodeValidator detects syntax errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a file with syntax error
        test_file = tmppath / "broken.py"
        test_file.write_text("""
def broken_function():
    print("missing closing quote)
    return True
""")
        
        validator = CodeValidator(tmppath)
        result = validator.validate_before_completion([test_file])
        
        print("Test: Syntax error detection")
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {result.errors}")
        
        assert not result.is_valid, "Should detect syntax error"
        assert len(result.errors) > 0, "Should list errors"
        assert "syntax" in result.errors[0]["message"].lower(), "Should identify as syntax error"
        
        print("  ✓ Correctly detected syntax error\n")


def test_code_validator_validates_correct_file():
    """Test that CodeValidator passes valid files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a correct file
        test_file = tmppath / "correct.py"
        test_file.write_text("""
from typing import Dict

def valid_function(name: str) -> Dict[str, str]:
    return {"name": name, "status": "ok"}
""")
        
        validator = CodeValidator(tmppath)
        result = validator.validate_before_completion([test_file])
        
        print("Test: Valid file validation")
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {result.errors}")
        print(f"  Warnings: {result.warnings}")
        
        assert result.is_valid, "Should pass valid file"
        assert len(result.errors) == 0, "Should have no errors"
        
        print("  ✓ Correctly validated correct file\n")


def test_code_validator_per_operation():
    """Test that CodeValidator can validate after each file operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a file with missing import
        test_file = tmppath / "test.py"
        test_file.write_text("""
def test():
    result = Path("./test")
    return str(result)
""")
        
        validator = CodeValidator(tmppath)
        result = validator.validate_file_operation(test_file, "write")
        
        print("Test: Per-operation validation")
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {result.errors}")
        print(f"  Suggestions: {result.suggestions}")
        
        assert not result.is_valid, "Should detect missing Path import"
        assert len(result.errors) > 0, "Should list errors"
        
        # Check suggestion
        assert len(result.suggestions) > 0, "Should provide suggestions"
        assert "Path" in str(result.suggestions), "Should suggest importing Path"
        
        print("  ✓ Correctly validated after file operation\n")


def test_cross_file_consistency():
    """Test cross-file consistency checks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create two files with duplicate function
        file1 = tmppath / "file1.py"
        file1.write_text("""
def duplicate_function():
    return "from file1"
""")
        
        file2 = tmppath / "file2.py"
        file2.write_text("""
def duplicate_function():
    return "from file2"
""")
        
        validator = CodeValidator(tmppath)
        result = validator.check_cross_file_consistency([file1, file2])
        
        print("Test: Cross-file consistency")
        print(f"  Warnings: {result.warnings}")
        
        assert len(result.warnings) > 0, "Should warn about duplicate definitions"
        assert "duplicate_function" in str(result.warnings), "Should identify the duplicate"
        
        print("  ✓ Correctly detected duplicate definition across files\n")


def test_flux_validation_case():
    """Simulate the exact Flux error case and verify it would be caught."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Simulate Flux's incomplete implementation
        # validation.py has the function
        validation_file = tmppath / "validation.py"
        validation_file.write_text("""
def validate_command_string(command: str):
    if '&&' in command:
        return False, "Unsafe"
    return True, "Safe"
""")
        
        # command.py uses it but doesn't import it (Flux's mistake)
        command_file = tmppath / "command.py"
        command_file.write_text("""
async def execute(command: str):
    # BUG: validate_command_string is used but not imported!
    is_valid, message = validate_command_string(command)
    if not is_valid:
        return {"error": message}
    return {"success": True}
""")
        
        print("Test: Flux validation failure case")
        print("  Simulating Flux's incomplete implementation...")
        
        # Run validation
        validator = CodeValidator(tmppath)
        result = validator.validate_before_completion([command_file])
        
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {len(result.errors)}")
        
        for error in result.errors:
            print(f"    ✗ {error['message']}")
        
        print(f"  Suggestions: {len(result.suggestions)}")
        for suggestion in result.suggestions:
            print(f"    → {suggestion}")
        
        # Verify it caught the error
        assert not result.is_valid, "MUST detect the missing import"
        assert len(result.errors) > 0, "MUST list the error"
        
        # Check that validate_command_string is identified
        error_messages = [e["message"] for e in result.errors]
        assert any("validate_command_string" in msg for msg in error_messages), \
            "MUST identify validate_command_string as missing"
        
        # Check that a suggestion is provided
        assert len(result.suggestions) > 0, "MUST provide import suggestion"
        suggestion_text = " ".join(result.suggestions)
        assert "validation" in suggestion_text.lower(), "MUST suggest importing from validation"
        
        print("\n  ✓✓✓ VALIDATION WOULD HAVE CAUGHT FLUX'S ERROR ✓✓✓\n")
        print("  This is exactly what Flux missed:")
        print("    - Used validate_command_string() without importing it")
        print("    - Would have caused NameError at runtime")
        print("    - Our validator catches it before completion\n")


def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("CODE VALIDATION INFRASTRUCTURE TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_import_analyzer_detects_missing_import,
        test_import_analyzer_suggests_import,
        test_code_validator_detects_syntax_errors,
        test_code_validator_validates_correct_file,
        test_code_validator_per_operation,
        test_cross_file_consistency,
        test_flux_validation_case,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
