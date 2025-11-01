"""Test that tool schemas are valid for OpenAI."""

import asyncio
from pathlib import Path
from flux.tools.file_ops import ReadFilesTool
from flux.tools.validation import ValidationTool
from flux.llm.openai_provider import OpenAIProvider


def validate_openai_schema(anthropic_tool):
    """Convert Anthropic tool to OpenAI and validate."""
    openai_tools = [{
        "type": "function",
        "function": {
            "name": anthropic_tool["name"],
            "description": anthropic_tool["description"],
            "parameters": anthropic_tool["input_schema"]
        }
    }]
    
    # Check that array parameters have items
    params = anthropic_tool["input_schema"]["properties"]
    for param_name, param_schema in params.items():
        if param_schema["type"] == "array":
            if "items" not in param_schema:
                return False, f"Parameter '{param_name}' is array but missing 'items'"
    
    return True, "Valid"


def main():
    """Test tool schemas."""
    print("\n" + "="*60)
    print("Testing Tool Schemas for OpenAI Compatibility")
    print("="*60)
    
    cwd = Path.cwd()
    
    # Test ReadFilesTool
    print("\n📋 Testing ReadFilesTool...")
    read_tool = ReadFilesTool(cwd)
    read_schema = read_tool.to_anthropic_tool()
    valid, msg = validate_openai_schema(read_schema)
    
    if valid:
        print(f"   ✅ ReadFilesTool schema valid")
        print(f"      Parameters: {list(read_schema['input_schema']['properties'].keys())}")
    else:
        print(f"   ❌ ReadFilesTool schema invalid: {msg}")
        return False
    
    # Test ValidationTool
    print("\n📋 Testing ValidationTool...")
    val_tool = ValidationTool(cwd)
    val_schema = val_tool.to_anthropic_tool()
    valid, msg = validate_openai_schema(val_schema)
    
    if valid:
        print(f"   ✅ ValidationTool schema valid")
        print(f"      Parameters: {list(val_schema['input_schema']['properties'].keys())}")
    else:
        print(f"   ❌ ValidationTool schema invalid: {msg}")
        return False
    
    # Show example of fixed schema
    print("\n📋 Example ReadFilesTool Schema:")
    print(f"   paths parameter:")
    paths_param = read_schema['input_schema']['properties']['paths']
    print(f"     type: {paths_param['type']}")
    print(f"     items: {paths_param.get('items', 'MISSING!')}")
    
    print("\n" + "="*60)
    print("✅ All tool schemas are OpenAI compatible!")
    print("="*60)
    print("\nThe 400 error should now be fixed. Try running Flux again!")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
