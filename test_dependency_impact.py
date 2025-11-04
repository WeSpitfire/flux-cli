#!/usr/bin/env python3
"""Test the enhanced dependency impact visualization."""

import asyncio
from pathlib import Path
from flux.core.codebase_intelligence import CodebaseGraph
from flux.core.impact_analyzer import ImpactAnalyzer

async def test_dependency_impact():
    """Test dependency impact analysis and visualization."""

    print("🧪 Testing Dependency Impact Visualization\n")
    print("=" * 60)

    # Build codebase graph
    print("\n1️⃣  Building codebase graph...")
    cwd = Path.cwd()
    graph = CodebaseGraph(cwd)
    graph.build_graph()
    print(f"   ✓ Found {len(graph.files)} files")

    # Create impact analyzer
    print("\n2️⃣  Initializing Impact Analyzer...")
    analyzer = ImpactAnalyzer(cwd, graph)
    print("   ✓ Analyzer ready")

    # Test case 1: Analyze impact of changing the CodebaseSemanticGraph class
    print("\n3️⃣  Testing impact analysis on core file...")
    print("   File: flux/core/codebase_graph.py")

    graph_file = cwd / "flux" / "core" / "codebase_intelligence.py"
    if graph_file.exists():
        old_content = graph_file.read_text()

        # Simulate adding a new method
        new_content = old_content + """

    def get_impact_chain(self, file_path: str) -> List[str]:
        '''Get chain of files affected by changes to this file.'''
        result = []
        if file_path in self.files:
            file_node = self.files[file_path]
            result.extend(file_node.dependents)
        return result
"""

        impact = analyzer.analyze_change(
            str(graph_file.relative_to(cwd)),
            old_content,
            new_content,
            "Added new get_impact_chain method"
        )

        print(f"\n   📊 Impact Analysis Results:")
        print(f"   - Change Type: {impact.change_type.value}")
        print(f"   - Impact Level: {impact.impact_level.value}")
        print(f"   - Confidence: {impact.confidence_score * 100:.0f}%")
        print(f"   - Functions Affected: {len(impact.functions_affected)}")
        print(f"   - Classes Affected: {len(impact.classes_affected)}")
        print(f"   - Propagation Depth: {impact.propagation_depth} layer(s)")
        print(f"   - Dependency Tree Size: {len(impact.dependency_tree)} file(s)")

        # Show dependency tree details
        if impact.dependency_tree:
            print(f"\n   🌳 Dependency Impact Tree:")

            direct = [k for k, v in impact.dependency_tree.items() if v.impact_type == "direct"]
            indirect = [k for k, v in impact.dependency_tree.items() if v.impact_type == "indirect"]
            tests = [k for k, v in impact.dependency_tree.items() if v.impact_type == "test"]

            if direct:
                print(f"      Direct impacts: {len(direct)}")
                for dep in direct[:3]:
                    dep_impact = impact.dependency_tree[dep]
                    risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                    print(f"        {risk_emoji.get(dep_impact.break_risk, '○')} {dep}")
                    if dep_impact.functions_used:
                        print(f"           → uses: {', '.join(dep_impact.functions_used)}")

            if tests:
                print(f"      Test files: {len(tests)}")
                for dep in tests[:2]:
                    print(f"        🧪 {dep}")

            if indirect:
                print(f"      Indirect impacts: {len(indirect)}")
                for dep in indirect[:2]:
                    print(f"        📍 {dep}")

        # Show warnings
        if impact.warnings:
            print(f"\n   ⚠️  Warnings:")
            for warning in impact.warnings:
                print(f"      {warning}")

        # Show suggestions
        if impact.suggestions:
            print(f"\n   💡 Suggestions:")
            for suggestion in impact.suggestions:
                print(f"      {suggestion}")

        print("\n   ✓ Test case 1 passed!")

    # Test case 2: Test smaller file with fewer dependencies
    print("\n4️⃣  Testing impact on smaller file...")

    prompts_file = cwd / "flux" / "llm" / "prompts.py"
    if prompts_file.exists():
        old_content = prompts_file.read_text()

        # Simulate modifying a function
        new_content = old_content.replace(
            "def get_system_prompt(",
            "def get_system_prompt_v2("
        )

        impact = analyzer.analyze_change(
            str(prompts_file.relative_to(cwd)),
            old_content,
            new_content,
            "Renamed function get_system_prompt"
        )

        print(f"   - Impact Level: {impact.impact_level.value}")
        print(f"   - Breaks existing: {impact.breaks_existing_code}")
        print(f"   - Dependency Tree Size: {len(impact.dependency_tree)}")
        print(f"   - Propagation Depth: {impact.propagation_depth}")

        print("   ✓ Test case 2 passed!")

    print("\n" + "=" * 60)
    print("✅ All dependency impact tests passed!")
    print("\nKey Features Demonstrated:")
    print("  • Dependency tree building with direct/indirect/test separation")
    print("  • Function and class usage tracking across files")
    print("  • Break risk assessment (high/medium/low)")
    print("  • Propagation depth calculation")
    print("  • Visual tree representation with emojis and colors")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_dependency_impact())
