"""Test script to verify both Anthropic and OpenAI providers work."""

import asyncio
import os
from dotenv import load_dotenv

from flux.core.config import Config
from flux.llm.provider_factory import create_provider

# Load environment variables
load_dotenv()


async def test_anthropic():
    """Test Anthropic provider."""
    print("\n" + "="*60)
    print("Testing Anthropic Provider")
    print("="*60)
    
    # Check if API key exists
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set, skipping test")
        return False
    
    try:
        # Create config for Anthropic
        os.environ["FLUX_PROVIDER"] = "anthropic"
        os.environ["FLUX_MODEL"] = "claude-3-haiku-20240307"
        config = Config()
        
        # Create provider
        provider = create_provider(config)
        
        print(f"✓ Provider: {config.provider}")
        print(f"✓ Model: {config.model}")
        
        # Test simple message
        print("\nSending test message...")
        response_text = ""
        
        async for event in provider.send_message(
            message="What is 2+2? Respond with just the number.",
            system_prompt="You are a helpful assistant.",
            tools=None
        ):
            if event["type"] == "text":
                response_text += event["content"]
                print(event["content"], end="", flush=True)
        
        print("\n")
        
        # Check token usage
        usage = provider.get_token_usage()
        print(f"✓ Tokens: {usage['total_tokens']} (${usage['estimated_cost']:.4f})")
        
        # Verify response
        if "4" in response_text:
            print("✅ Anthropic provider working!")
            return True
        else:
            print(f"⚠️  Unexpected response: {response_text}")
            return False
        
    except Exception as e:
        print(f"❌ Anthropic test failed: {e}")
        return False


async def test_openai():
    """Test OpenAI provider."""
    print("\n" + "="*60)
    print("Testing OpenAI Provider")
    print("="*60)
    
    # Check if API key exists
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set, skipping test")
        return False
    
    try:
        # Create config for OpenAI
        os.environ["FLUX_PROVIDER"] = "openai"
        os.environ["FLUX_MODEL"] = "gpt-4o-mini"  # Use mini for cheaper testing
        config = Config()
        
        # Create provider
        provider = create_provider(config)
        
        print(f"✓ Provider: {config.provider}")
        print(f"✓ Model: {config.model}")
        
        # Test simple message
        print("\nSending test message...")
        response_text = ""
        
        async for event in provider.send_message(
            message="What is 2+2? Respond with just the number.",
            system_prompt="You are a helpful assistant.",
            tools=None
        ):
            if event["type"] == "text":
                response_text += event["content"]
                print(event["content"], end="", flush=True)
        
        print("\n")
        
        # Check token usage
        usage = provider.get_token_usage()
        print(f"✓ Tokens: {usage['total_tokens']} (${usage['estimated_cost']:.4f})")
        
        # Verify response
        if "4" in response_text:
            print("✅ OpenAI provider working!")
            return True
        else:
            print(f"⚠️  Unexpected response: {response_text}")
            return False
        
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n🧪 Testing Multi-Provider Implementation")
    
    results = {}
    
    # Test Anthropic
    results["anthropic"] = await test_anthropic()
    
    # Test OpenAI
    results["openai"] = await test_openai()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for provider, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL/SKIP"
        print(f"{provider.capitalize()}: {status}")
    
    # Overall result
    passed = [p for p, r in results.items() if r]
    
    print("\n" + "="*60)
    if len(passed) >= 1:
        print(f"✅ {len(passed)}/{len(results)} providers working!")
        print("Multi-provider implementation successful! 🎉")
    else:
        print("❌ No providers working")
        print("Check API keys and try again.")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
