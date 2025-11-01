#!/bin/bash

# Flux Desktop Launch Script
# This script ensures proper environment setup before launching

echo "🚀 Starting Flux Desktop..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must be run from flux-desktop directory"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Check if Flux CLI is available
if [ ! -f "../venv/bin/flux" ]; then
    echo "⚠️  Warning: Flux CLI not found in venv"
    echo "   Please install Flux CLI first: cd .. && pip install -e ."
    exit 1
fi

# Launch in development mode
echo "✅ Launching Flux Desktop..."
npm run dev
