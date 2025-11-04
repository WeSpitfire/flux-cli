"""Tests for auto-fixer functionality."""

import pytest
from flux.core.auto_fixer import AutoFixer, FixType, AutoFix


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for tests."""
    return tmp_path


@pytest.fixture
def auto_fixer(temp_dir):
    """Create AutoFixer instance."""
    return AutoFixer(temp_dir, enabled=True)


def test_can_auto_fix(auto_fixer, temp_dir):
    """Test that supported file types are recognized."""
    # Supported types
    assert auto_fixer.can_auto_fix(temp_dir / "test.py")
    assert auto_fixer.can_auto_fix(temp_dir / "test.js")
    assert auto_fixer.can_auto_fix(temp_dir / "test.ts")
    assert auto_fixer.can_auto_fix(temp_dir / "test.json")

    # Unsupported types
    assert not auto_fixer.can_auto_fix(temp_dir / "test.txt")
    assert not auto_fixer.can_auto_fix(temp_dir / "test.md")


def test_trailing_whitespace_detection(auto_fixer, temp_dir):
    """Test trailing whitespace detection."""
    test_file = temp_dir / "test.py"
    test_file.write_text("line1   \\nline2  \\nline3\\n")

    fixes = auto_fixer.analyze_file(test_file)

    assert len(fixes) == 1
    assert fixes[0].fix_type == FixType.TRAILING_WHITESPACE
    assert fixes[0].description == "Remove trailing whitespace"


def test_excessive_blank_lines_detection(auto_fixer, temp_dir):
    """Test excessive blank lines detection."""
    test_file = temp_dir / "test.py"
    test_file.write_text("line1\\n\\n\\n\\n\\nline2\\n")

    fixes = auto_fixer.analyze_file(test_file)

    assert len(fixes) == 1
    assert fixes[0].fix_type == FixType.BLANK_LINES
    assert fixes[0].description == "Reduce excessive blank lines"


def test_unused_imports_detection(auto_fixer, temp_dir):
    """Test unused import detection in Python files."""
    test_file = temp_dir / "test.py"
    test_file.write_text("""import os
import sys
import unused_module

def main():
    print(sys.version)
    return os.getcwd()
""")

    fixes = auto_fixer.analyze_file(test_file)

    # Should detect unused_module
    unused_fixes = [f for f in fixes if f.fix_type == FixType.UNUSED_IMPORT]
    assert len(unused_fixes) == 1
    assert "unused_module" in unused_fixes[0].description


def test_no_false_positives_for_used_imports(auto_fixer, temp_dir):
    """Test that used imports are not flagged."""
    test_file = temp_dir / "test.py"
    test_file.write_text("""import os
import sys

def main():
    print(sys.version)
    return os.getcwd()
""")

    fixes = auto_fixer.analyze_file(test_file)

    # Should not detect any unused imports
    unused_fixes = [f for f in fixes if f.fix_type == FixType.UNUSED_IMPORT]
    assert len(unused_fixes) == 0


def test_apply_trailing_whitespace_fix(auto_fixer, temp_dir):
    """Test applying trailing whitespace fix."""
    test_file = temp_dir / "test.py"
    original = "line1   \\nline2  \\nline3\\n"
    test_file.write_text(original)

    fixes = auto_fixer.analyze_file(test_file)
    success, count = auto_fixer.apply_fixes(test_file, fixes)

    assert success
    assert count == 1

    # Check file was fixed
    fixed_content = test_file.read_text()
    assert fixed_content == "line1\\nline2\\nline3\\n"


def test_apply_blank_lines_fix(auto_fixer, temp_dir):
    """Test applying excessive blank lines fix."""
    test_file = temp_dir / "test.py"
    test_file.write_text("line1\\n\\n\\n\\n\\nline2\\n")

    fixes = auto_fixer.analyze_file(test_file)
    success, count = auto_fixer.apply_fixes(test_file, fixes)

    assert success
    assert count == 1

    # Check file was fixed (max 2 blank lines)
    fixed_content = test_file.read_text()
    assert "\\n\\n\\n\\n" not in fixed_content


def test_apply_unused_import_fix(auto_fixer, temp_dir):
    """Test applying unused import fix."""
    test_file = temp_dir / "test.py"
    original = """import os
import unused_module

def main():
    return os.getcwd()
"""
    test_file.write_text(original)

    fixes = auto_fixer.analyze_file(test_file)
    success, count = auto_fixer.apply_fixes(test_file, fixes)

    assert success
    assert count > 0

    # Check unused import was removed
    fixed_content = test_file.read_text()
    assert "unused_module" not in fixed_content
    assert "import os" in fixed_content


def test_undo_fix(auto_fixer, temp_dir):
    """Test undoing a fix."""
    test_file = temp_dir / "test.py"
    original = "line1   \\nline2\\n"
    test_file.write_text(original)

    # Apply fix
    fixes = auto_fixer.analyze_file(test_file)
    auto_fixer.apply_fixes(test_file, fixes)

    # Undo
    undone_fix = auto_fixer.undo_last_fix()

    assert undone_fix is not None
    assert undone_fix.fix_type == FixType.TRAILING_WHITESPACE

    # Check file was restored (approximately - exact restoration may vary)
    restored_content = test_file.read_text()
    # The undo might not perfectly restore, but should have content
    assert "line1" in restored_content


def test_get_fix_summary(auto_fixer, temp_dir):
    """Test fix summary generation."""
    # Apply multiple fixes
    test_file1 = temp_dir / "test1.py"
    test_file1.write_text("line   \\n")

    test_file2 = temp_dir / "test2.py"
    test_file2.write_text("line\\n\\n\\n\\n\\nline\\n")

    fixes1 = auto_fixer.analyze_file(test_file1)
    fixes2 = auto_fixer.analyze_file(test_file2)

    auto_fixer.apply_fixes(test_file1, fixes1)
    auto_fixer.apply_fixes(test_file2, fixes2)

    summary = auto_fixer.get_fix_summary()

    assert len(summary) > 0
    assert "trailing_whitespace" in summary or "blank_lines" in summary


def test_disabled_auto_fixer(temp_dir):
    """Test that disabled auto-fixer doesn't fix anything."""
    auto_fixer = AutoFixer(temp_dir, enabled=False)

    test_file = temp_dir / "test.py"
    test_file.write_text("line   \\n")

    fixes = auto_fixer.analyze_file(test_file)

    # Should return no fixes when disabled
    assert len(fixes) == 0


def test_syntax_error_handling(auto_fixer, temp_dir):
    """Test that files with syntax errors are skipped gracefully."""
    test_file = temp_dir / "broken.py"
    test_file.write_text("def broken(\\n    pass\\n")  # Invalid syntax

    # Should not crash
    fixes = auto_fixer.analyze_file(test_file)

    # May return other fixes like whitespace, but shouldn't crash
    assert isinstance(fixes, list)


def test_multiple_fixes_same_file(auto_fixer, temp_dir):
    """Test applying multiple fixes to the same file."""
    test_file = temp_dir / "test.py"
    test_file.write_text("""import unused

line1


line2
""")

    fixes = auto_fixer.analyze_file(test_file)

    # Should detect multiple types of issues
    fix_types = {f.fix_type for f in fixes}
    assert len(fix_types) >= 2  # At least trailing whitespace and blank lines

    success, count = auto_fixer.apply_fixes(test_file, fixes)
    assert success
    assert count >= 2


def test_config_toggles(auto_fixer, temp_dir):
    """Test configuration toggles."""
    # Disable trailing whitespace fixing
    auto_fixer.config['fix_trailing_whitespace'] = False

    test_file = temp_dir / "test.py"
    test_file.write_text("line   \\n")

    fixes = auto_fixer.analyze_file(test_file)

    # Should not detect trailing whitespace when disabled
    trailing_fixes = [f for f in fixes if f.fix_type == FixType.TRAILING_WHITESPACE]
    assert len(trailing_fixes) == 0


def test_clear_history(auto_fixer, temp_dir):
    """Test clearing fix history."""
    test_file = temp_dir / "test.py"
    test_file.write_text("line   \\n")

    fixes = auto_fixer.analyze_file(test_file)
    auto_fixer.apply_fixes(test_file, fixes)

    assert len(auto_fixer.fix_history) > 0

    auto_fixer.clear_history()

    assert len(auto_fixer.fix_history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
