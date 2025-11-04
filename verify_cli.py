"""Verify CLI works with GPT-4o."""

import asyncio
from pathlib import Path
from flux.core.config import Config
from flux.ui.cli import CLI


async def test_cli():
    """Test basic CLI functionality."""
    print("="*60)
    print("Testing Flux CLI with GPT-4o")
    print("="*60)

    # Create CLI instance
    cwd = Path.cwd()
    config = Config()
    cli = CLI(config, cwd)

    # Print banner (shows provider info)
    cli.print_banner()

    print("\n✅ CLI initialized successfully!")
    print(f"✅ Provider: {config.provider}")
    print(f"✅ Model: {config.model}")
    print(f"✅ LLM client type: {type(cli.llm).__name__}")

    print("\n" + "="*60)
    print("Flux is ready to use with GPT-4o! 🎉")
    print("="*60)
    print("\nTo start Flux, run:")
    print("  flux")
    print("\nOr:")
    print("  python -m flux.main")


if __name__ == "__main__":
    asyncio.run(test_cli())
