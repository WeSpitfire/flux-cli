"""Pytest fixtures for Flux tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from flux.core.config import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file for testing."""
    file_path = temp_dir / "sample.py"
    content = '''"""Sample Python module."""

def hello(name):
    """Greet someone."""
    return f"Hello, {name}!"

class Calculator:
    """A simple calculator."""
    
    def add(self, a, b):
        """Add two numbers."""
        return a + b
    
    def subtract(self, a, b):
        """Subtract two numbers."""
        return a - b
'''
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_js_file(temp_dir):
    """Create a sample JavaScript file for testing."""
    file_path = temp_dir / "sample.js"
    content = '''// Sample JavaScript module

function greet(name) {
  return `Hello, ${name}!`;
}

class Calculator {
  add(a, b) {
    return a + b;
  }
  
  subtract(a, b) {
    return a - b;
  }
}

module.exports = { greet, Calculator };
'''
    file_path.write_text(content)
    return file_path


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    # Note: You may need to mock API keys or provide test keys
    return Config()
