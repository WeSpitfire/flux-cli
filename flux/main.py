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
    
    # Graph command
    graph_parser = subparsers.add_parser(
        "graph",
        help="Export codebase graph data"
    )
    graph_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
        help="Output format (default: json)"
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
        "--max-history",
        type=int,
        default=8000,
        help="Maximum number of tokens to keep in conversation history (default: 8000)"
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
    
    # Handle graph export command
    if args.command == "graph":
        try:
            import json
            from flux.core.codebase_intelligence import CodebaseGraph
            
            cwd = Path.cwd()
            graph = CodebaseGraph(cwd)
            graph.build_graph(use_cache=True)
            
            # Export graph data
            export_data = {
                "stats": {
                    "totalFiles": len(graph.files),
                    "totalEntities": len(graph.entities),
                    "contextTokens": len(graph.files) * 500  # Rough estimate
                },
                "files": {},
                "entities": {}
            }
            
            # Export files (limited to prevent huge output)
            for path, file_node in list(graph.files.items())[:100]:
                export_data["files"][path] = {
                    "language": file_node.language,
                    "imports": file_node.imports[:10],  # Limit
                    "exports": file_node.exports[:10],
                    "dependencies": file_node.dependencies[:10],
                    "dependents": file_node.dependents[:10]
                }
            
            # Export entities (limited)
            for name, entity in list(graph.entities.items())[:100]:
                export_data["entities"][name] = {
                    "name": entity.name,
                    "type": entity.type,
                    "file": entity.file_path,
                    "line": entity.line_number
                }
            
            # Print JSON to stdout
            print(json.dumps(export_data, indent=2))
            
        except Exception as e:
            print(f"\n❌ Graph Export Error: {e}\n", file=sys.stderr)
            sys.exit(1)
        return
    
    # Initialize configuration
    config = Config()
    
    # Set max history from CLI argument
    config.max_history = args.max_history
    
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
