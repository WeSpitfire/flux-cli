#!/bin/bash

# Flux CLI Setup Script

set -e

echo "🚀 Setting up Flux CLI..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "To use Flux:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Set your ANTHROPIC_API_KEY in .env"
echo "  3. Run: python flux/main.py"
echo ""
echo "Or install as a command:"
echo "  pip install -e ."
echo "  flux"
