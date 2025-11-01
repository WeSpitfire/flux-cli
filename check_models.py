#!/usr/bin/env python3
"""Check which Anthropic models are available with your API key."""

import os
from anthropic import Anthropic

# Get API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ ANTHROPIC_API_KEY not set")
    exit(1)

print(f"✓ API Key found: {api_key[:20]}...")

# Try different models
models_to_test = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

client = Anthropic(api_key=api_key)

print("\nTesting model availability:\n")

for model in models_to_test:
    try:
        # Try to make a minimal request
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✅ {model} - AVAILABLE")
    except Exception as e:
        error_str = str(e)
        if "404" in error_str or "not_found" in error_str:
            print(f"❌ {model} - NOT AVAILABLE (404)")
        elif "401" in error_str or "authentication" in error_str:
            print(f"❌ {model} - AUTH ERROR")
        else:
            print(f"⚠️  {model} - ERROR: {error_str[:50]}")

print("\nRecommendation:")
print("Use the first ✅ model from the list above in your .env file")
