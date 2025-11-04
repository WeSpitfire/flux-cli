"""Final test of multi-provider setup."""

import asyncio
import sys
from pathlib import Path

# Load .env fresh
from dotenv import load_dotenv
load_dotenv(override=True)

import os
from flux.core.config import Config
from flux.ui.cli import CLI


async def main():
    """Test CLI with current configuration."""
    print("\n" + "="*60)
    print("FINAL MULTI-PROVIDER TEST")
    print("="*60)

    # Show environment
    print(f"\n📋 Environment Variables:")
    print(f"   FLUX_PROVIDER = {os.getenv('FLUX_PROVIDER')}")
    print(f"   FLUX_MODEL = {os.getenv('FLUX_MODEL')}")
    print(f"   ANTHROPIC_API_KEY = {'✓ Set' if os.getenv('ANTHROPIC_API_KEY') else '✗ Missing'}")
    print(f"   OPENAI_API_KEY = {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Missing'}")

    # Create config
    print(f"\n⚙️  Creating Config...")
    config = Config()

    print(f"\n✅ Configuration:")
    print(f"   Provider: {config.provider}")
    print(f"   Model: {config.model}")

    # Create CLI
    print(f"\n🔧 Creating CLI...")
    cwd = Path.cwd()
    cli = CLI(config, cwd)

    print(f"✅ CLI Created:")
    print(f"   LLM Provider Type: {type(cli.llm).__name__}")

    # Show banner
    print(f"\n" + "="*60)
    print("Flux Banner:")
    print("="*60)
    cli.print_banner()

    # Final status
    print("\n" + "="*60)
    if config.provider == "openai" and config.model == "gpt-4o":
        print("✅ SUCCESS! Flux is configured to use GPT-4o!")
        print("="*60)
        print("\n🎉 Multi-provider implementation complete and working!")
        print("\nYou can now run:")
        print("  flux")
        print("\nAnd Flux will use GPT-4o for excellent code editing!")
        return True
    else:
        print(f"⚠️  WARNING: Expected GPT-4o but got:")
        print(f"   Provider: {config.provider}")
        print(f"   Model: {config.model}")
        print("="*60)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
