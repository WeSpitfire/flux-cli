"""Quick test of GPT-4o provider."""

import asyncio
import os
from dotenv import load_dotenv

from flux.core.config import Config
from flux.llm.provider_factory import create_provider

load_dotenv()


async def test_gpt4o():
    """Test GPT-4o with a simple code generation task."""
    print("\n" + "="*60)
    print("Testing GPT-4o Provider")
    print("="*60)

    # Configure for GPT-4o
    os.environ["FLUX_PROVIDER"] = "openai"
    os.environ["FLUX_MODEL"] = "gpt-4o"

    config = Config()
    provider = create_provider(config)

    print(f"✓ Provider: {config.provider}")
    print(f"✓ Model: {config.model}")

    # Test with a code generation task
    print("\n📝 Task: Write a Python function to reverse a string\n")

    response_text = ""
    async for event in provider.send_message(
        message="Write a short Python function called 'reverse_string' that takes a string and returns it reversed. Just the code, no explanation.",
        system_prompt="You are a helpful coding assistant. Provide concise, correct code.",
        tools=None
    ):
        if event["type"] == "text":
            response_text += event["content"]
            print(event["content"], end="", flush=True)

    print("\n")

    # Check token usage
    usage = provider.get_token_usage()
    print(f"✓ Tokens: {usage['total_tokens']} (${usage['estimated_cost']:.4f})")

    # Verify response contains function
    if "def reverse_string" in response_text and "return" in response_text:
        print("✅ GPT-4o working perfectly!")
        return True
    else:
        print(f"⚠️  Unexpected response")
        return False


if __name__ == "__main__":
    asyncio.run(test_gpt4o())
