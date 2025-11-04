#!/usr/bin/env python3
"""Manual test for FileStructureAnalyzer"""

from pathlib import Path
from flux.core.file_analyzer import FileStructureAnalyzer

def test_analyzer():
    """Test the FileStructureAnalyzer on ast_edit.py"""

    analyzer = FileStructureAnalyzer()

    # Test analyzing ast_edit.py
    print("=" * 60)
    print("Testing FileStructureAnalyzer on ast_edit.py")
    print("=" * 60)

    file_path = Path("flux/tools/ast_edit.py")
    structure = analyzer.analyze(file_path)

    print(f"\n📄 File: {file_path}")
    print(f"   Total lines: {structure.total_lines}")
    print(f"   Classes: {len(structure.classes)}")
    print(f"   Functions: {len(structure.functions)}")
    print(f"   Imports: {len(structure.imports)}")

    # Show classes and their methods
    print("\n🔍 Classes found:")
    for cls in structure.classes:
        print(f"   - {cls.name} (line {cls.line_number}-{cls.end_line})")
        print(f"     Methods: {', '.join(cls.method_names)}")

    # Test duplicate detection
    print("\n" + "=" * 60)
    print("Testing Duplicate Detection")
    print("=" * 60)

    # Try to add existing method
    can_add, msg = analyzer.can_add_function(
        file_path,
        "execute",  # This method already exists in ASTEditTool
        target_class="ASTEditTool"
    )
    print(f"\n❌ Can add 'execute' to ASTEditTool? {can_add}")
    if not can_add:
        print(f"   Error message: {msg}")

    # Try to add new method
    can_add, msg = analyzer.can_add_function(
        file_path,
        "new_method",
        target_class="ASTEditTool"
    )
    print(f"\n✅ Can add 'new_method' to ASTEditTool? {can_add}")
    if can_add:
        print(f"   {msg}")

    # Test insertion point
    print("\n" + "=" * 60)
    print("Testing Insertion Points")
    print("=" * 60)

    insertion_line = analyzer.find_best_insertion_point(
        file_path,
        target_class="ASTEditTool"
    )
    print(f"\n📍 Best insertion point for ASTEditTool: line {insertion_line}")

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_analyzer()
