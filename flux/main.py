"""Main entry point for Flux CLI."""

import sys
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

from flux.ui.cli import CLI
from flux.core.config import Config


def print_config_info(config: Config):
    """Print configuration information."""
    print("\n⚙️  Flux Configuration")
    print("=" * 50)
    print(f"\n🤖 Model: {config.model}")
    print(f"📊 Max Tokens: {config.max_tokens}")
    print(f"🌡️  Temperature: {config.temperature}")
    print(f"\n📁 Flux Directory: {config.flux_dir}")
    print(f"📂 ChromaDB Directory: {config.chroma_dir}")
    print(f"📝 History: {config.conversation_history_path}")
    print(f"\n✅ Require Approval: {config.require_approval}")
    print(f"⚡ Auto Approve: {config.auto_approve}")
    
    # Check API key (without revealing it)
    if config.anthropic_api_key:
        masked_key = config.anthropic_api_key[:10] + "..." + config.anthropic_api_key[-4:]
        print(f"\n🔑 API Key: {masked_key} ✅")
    else:
        print(f"\n🔑 API Key: ❌ NOT SET")
    
    print("\n" + "=" * 50)
    print("✅ Configuration is valid!\n")


def main():
    """Main entry point for Flux CLI."""
    # Load environment variables
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Flux - AI-powered development assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management"
    )
    config_parser.add_argument(
        "action",
        choices=["check", "show"],
        default="check",
        nargs="?",
        help="Action to perform (default: check)"
    )
    
    # Query command (default)
    parser.add_argument(
        "query",
        nargs="*",
        help="Query to process (interactive mode if omitted)"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-approve all changes without prompting"
    )
    parser.add_argument(
        "--no-approval",
        action="store_true",
        help="Disable approval prompts (same as --yes)"
    )
    
    args = parser.parse_args()
    
    # Handle config command
    if args.command == "config":
        try:
            config = Config()
            print_config_info(config)
        except Exception as e:
            print(f"\n❌ Configuration Error: {e}\n", file=sys.stderr)
            sys.exit(1)
        return
    
    # Initialize configuration
    config = Config()
    
    # Set auto-approve mode if flags are present
    if args.yes or args.no_approval:
        config.auto_approve = True
    
    # Get current working directory
    cwd = Path.cwd()
    
    # Initialize CLI
    cli = CLI(config=config, cwd=cwd)
    
    # Check for command-line query
    if args.query:
        query = " ".join(args.query)
        asyncio.run(cli.run_single_query(query))
    else:
        # Start interactive mode
        asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    main()
