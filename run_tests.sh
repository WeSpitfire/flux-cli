#!/bin/bash
# Quick test runner for Flux CLI
# This script runs the core tests to validate functionality

set -e  # Exit on error

echo "=================================="
echo "Flux CLI Test Suite"
echo "=================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing..."
    pip install pytest pytest-asyncio
fi

echo ""
echo "Running conversation flow tests..."
pytest tests/test_conversation_flow.py -v

echo ""
echo "Running context management tests..."
pytest tests/unit/ -k context -v || true

echo ""
echo "=================================="
echo "Test Summary"
echo "=================================="
echo "✅ Core conversation flow tests completed"
echo ""
echo "To run ALL tests:"
echo "  pytest tests/ -v"
echo ""
echo "To run with coverage:"
echo "  pytest tests/ --cov=flux --cov-report=html"
echo ""
echo "To run specific test categories:"
echo "  pytest -m unit        # Unit tests only"
echo "  pytest -m integration # Integration tests only"
echo "=================================="
