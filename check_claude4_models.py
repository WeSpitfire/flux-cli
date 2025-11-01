#!/usr/bin/env python3
"""Check Claude 4.x model availability."""

import os
from anthropic import Anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ ANTHROPIC_API_KEY not set")
    exit(1)

print(f"✓ API Key found: {api_key[:20]}...")

# Claude 4.x models (newest generation)
models_to_test = [
    "claude-4-0-sonnet-20250514",  # Claude 4 Sonnet
    "claude-4-0-haiku-20250514",   # Claude 4 Haiku
    "claude-3-5-sonnet-20241022",  # Claude 3.5 Sonnet (latest)
    "claude-3-5-sonnet-20240620",  # Claude 3.5 Sonnet (stable)
    "claude-3-haiku-20240307",     # Claude 3 Haiku
]

client = Anthropic(api_key=api_key)

print("\nTesting model availability:\n")

for model in models_to_test:
    try:
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
        else:
            print(f"⚠️  {model} - ERROR: {error_str[:80]}")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("Use the FIRST ✅ Sonnet model from above in your .env file")
print("="*60)
