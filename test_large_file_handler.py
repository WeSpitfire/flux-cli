#!/usr/bin/env python3
"""Test the large file handler."""

from pathlib import Path
from flux.core.large_file_handler import LargeFileHandler

def test_large_file_handler():
    """Test analyzing a large file (cli.py)."""
    handler = LargeFileHandler()

    # Test with cli.py (the large file that caused issues)
    cli_path = Path("flux/ui/cli.py")

    if not cli_path.exists():
        print("❌ cli.py not found")
        return

    print("📊 Analyzing flux/ui/cli.py...\n")

    # Analyze the file
    analysis = handler.analyze_file(cli_path)

    if "error" in analysis:
        print(f"❌ Error: {analysis['error']}")
        return

    # Print analysis
    print(f"📏 Lines: {analysis['lines']}")
    print(f"🔍 Is large: {analysis['is_large']}")
    print(f"🔍 Is very large: {analysis['is_very_large']}")
    print(f"🔤 Language: {analysis['language']}")
    print(f"💡 Strategy: {analysis['suggested_strategy']}")

    # Print structure
    structure = analysis.get("structure")
    if structure and not structure.get("error"):
        print(f"\n📦 Structure:")
        print(f"   Classes: {structure.get('class_count', 0)}")
        print(f"   Functions: {structure.get('function_count', 0)}")
        print(f"   Imports: {structure.get('import_count', 0)}")

        # Show first few classes
        if structure.get("classes"):
            print(f"\n   Top classes:")
            for cls in structure["classes"][:3]:
                print(f"      • {cls['name']} (line {cls['line']}, {cls['method_count']} methods)")

    # Print chunks
    chunks = analysis.get("chunks", [])
    print(f"\n📑 Suggested chunks: {len(chunks)} total")
    for chunk in chunks[:3]:
        print(f"   • {chunk['description']}")

    # Print summary
    print("\n" + "="*60)
    print("📄 File Summary:")
    print("="*60)
    summary = handler.create_summary(cli_path, analysis)
    print(summary)

    # Print reading guide
    print("\n" + "="*60)
    print("📖 Reading Guide:")
    print("="*60)
    guide = handler.get_reading_guide(cli_path)
    print(guide)

    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_large_file_handler()
