#!/usr/bin/env python3
"""Test script for codebase intelligence features."""

import asyncio
from pathlib import Path
from flux.ui.cli import CLI
from flux.core.config import Config


async def main():
    print("=" * 60)
    print("Testing Flux Codebase Intelligence")
    print("=" * 60)
    
    # Initialize CLI
    cli = CLI(Config(), Path.cwd())
    
    # Test 1: Build codebase graph
    print("\n📊 Test 1: Building codebase graph...")
    await cli.build_codebase_graph()
    
    # Test 2: Show architecture
    print("\n🏗️  Test 2: Architecture detection...")
    await cli.show_architecture()
    
    # Test 3: Find related files
    print("\n🔍 Test 3: Finding files related to 'config'...")
    await cli.show_related_files("config")
    
    print("\n🔍 Test 4: Finding files related to 'llm'...")
    await cli.show_related_files("llm")
    
    print("\n🔍 Test 5: Finding files related to 'tools'...")
    await cli.show_related_files("tools")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
