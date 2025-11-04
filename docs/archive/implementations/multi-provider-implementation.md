# Multi-Provider Implementation Plan

## Goal
Enable Flux to work with multiple LLM providers (Anthropic, OpenAI, etc.) through a clean abstraction layer.

## Status: 🟡 In Progress

- ✅ Base abstraction created (`flux/llm/base_provider.py`)
- ⬜ Refactor Anthropic to use abstraction
- ⬜ Implement OpenAI provider
- ⬜ Add provider factory
- ⬜ Update config and CLI
- ⬜ Test and document

---

## Architecture

```
flux/llm/
├── base_provider.py          # Abstract base class (✅ DONE)
├── anthropic_provider.py     # Anthropic implementation (TODO)
├── openai_provider.py         # OpenAI implementation (TODO)
├── provider_factory.py        # Factory to create providers (TODO)
└── client.py                  # Legacy, to be deprecated
```

### Base Provider Interface

```python
class BaseLLMProvider(ABC):
    async def send_message(message, system_prompt, tools) -> AsyncIterator
    def add_tool_result(tool_use_id, result)
    def clear_history()
    def get_token_usage() -> Dict
    def set_current_file_context(file_path)  # Optional
```

---

## Implementation Steps

### Step 1: Refactor Anthropic Provider ✅→⬜

**File**: `flux/llm/anthropic_provider.py`

```python
from flux.llm.base_provider import BaseLLMProvider
from anthropic import AsyncAnthropic

class AnthropicProvider(BaseLLMProvider):
    # Move all code from current client.py
    # Keep context pruning, streaming, tool calling
```

**Changes needed**:
- Rename `LLMClient` → `AnthropicProvider`
- Inherit from `BaseLLMProvider`
- Keep all existing functionality
- Update to use `config.anthropic_api_key`

### Step 2: Implement OpenAI Provider ⬜

**File**: `flux/llm/openai_provider.py`

```python
from flux.llm.base_provider import BaseLLMProvider
from openai import AsyncOpenAI

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config, enable_context_pruning=True):
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.enable_context_pruning = enable_context_pruning
        self.current_file_context = None
    
    async def send_message(self, message, system_prompt, tools=None):
        # Build messages in OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": message})
        
        # Convert tools to OpenAI format if provided
        openai_tools = self._convert_tools(tools) if tools else None
        
        # Stream response
        stream = await self.client.chat.completions.create(
            model=self.config.model,  # e.g., "gpt-4o"
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            tools=openai_tools,
            stream=True
        )
        
        # Process stream and yield events
        async for chunk in stream:
            # Handle text chunks
            if chunk.choices[0].delta.content:
                yield {"type": "text", "content": chunk.choices[0].delta.content}
            
            # Handle tool calls
            if chunk.choices[0].delta.tool_calls:
                for tool_call in chunk.choices[0].delta.tool_calls:
                    yield {
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "input": json.loads(tool_call.function.arguments)
                    }
    
    def _convert_tools(self, anthropic_tools):
        """Convert Anthropic tool format to OpenAI format."""
        openai_tools = []
        for tool in anthropic_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })
        return openai_tools
    
    def add_tool_result(self, tool_use_id, result):
        """Add tool result in OpenAI format."""
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": tool_use_id,
            "content": json.dumps(result) if not isinstance(result, str) else result
        })
    
    def get_token_usage(self):
        """Get token usage with OpenAI pricing."""
        # GPT-4o: $2.50/$10.00 per 1M tokens (as of 2024)
        input_cost = (self.total_input_tokens / 1_000_000) * 2.50
        output_cost = (self.total_output_tokens / 1_000_000) * 10.00
        
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost": input_cost + output_cost,
        }
```

### Step 3: Create Provider Factory ⬜

**File**: `flux/llm/provider_factory.py`

```python
from flux.llm.base_provider import BaseLLMProvider
from flux.llm.anthropic_provider import AnthropicProvider
from flux.llm.openai_provider import OpenAIProvider
from flux.core.config import Config


def create_provider(config: Config, enable_context_pruning: bool = True) -> BaseLLMProvider:
    """
    Factory function to create the appropriate LLM provider.
    
    Args:
        config: Flux configuration
        enable_context_pruning: Enable context pruning (if supported)
    
    Returns:
        An instance of BaseLLMProvider (Anthropic or OpenAI)
    
    Raises:
        ValueError: If provider is not supported
    """
    provider = config.provider.lower()
    
    if provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        return AnthropicProvider(config, enable_context_pruning)
    
    elif provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        return OpenAIProvider(config, enable_context_pruning)
    
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: anthropic, openai"
        )
```

### Step 4: Update Config ⬜

**File**: `flux/core/config.py`

Add new fields:

```python
@dataclass
class Config:
    # ... existing fields ...
    
    # Provider selection
    provider: str = field(default_factory=lambda: os.getenv("FLUX_PROVIDER", "anthropic"))
    
    # API Keys (provider-specific)
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    
    # Model (provider-specific)
    # Anthropic: claude-3-haiku-20240307, claude-3-5-sonnet-20240620
    # OpenAI: gpt-4o, gpt-4-turbo, gpt-4
    model: str = field(default_factory=lambda: os.getenv("FLUX_MODEL", "claude-3-haiku-20240307"))
    
    def __post_init__(self):
        # Validate provider
        if self.provider not in ["anthropic", "openai"]:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        # Validate API key for selected provider
        if self.provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider")
        if self.provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI provider")
        
        # ... rest of validation ...
```

### Step 5: Update CLI ⬜

**File**: `flux/ui/cli.py`

Change initialization:

```python
# OLD:
from flux.llm.client import LLMClient
self.llm = LLMClient(self.config)

# NEW:
from flux.llm.provider_factory import create_provider
self.llm = create_provider(self.config)
```

No other changes needed - the interface is identical!

---

## Configuration

### Using Anthropic (Current Default)

```bash
# .env
FLUX_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
FLUX_MODEL=claude-3-haiku-20240307
```

### Using OpenAI

```bash
# .env
FLUX_PROVIDER=openai
OPENAI_API_KEY=sk-...
FLUX_MODEL=gpt-4o  # or gpt-4-turbo, gpt-4
```

---

## Supported Models

### Anthropic
- `claude-3-haiku-20240307` - Fast, cheap, current default
- `claude-3-5-sonnet-20240620` - Best quality (if available)
- `claude-3-opus-20240229` - Most powerful (if available)

### OpenAI
- `gpt-4o` - Fastest GPT-4 level (recommended)
- `gpt-4-turbo` - GPT-4 Turbo
- `gpt-4` - Original GPT-4
- `gpt-3.5-turbo` - Faster, cheaper (not recommended for code)

---

## Tool Format Conversion

### Anthropic Format (Current)
```json
{
  "name": "edit_file",
  "description": "Edit a file",
  "input_schema": {
    "type": "object",
    "properties": {...}
  }
}
```

### OpenAI Format (Target)
```json
{
  "type": "function",
  "function": {
    "name": "edit_file",
    "description": "Edit a file",
    "parameters": {
      "type": "object",
      "properties": {...}
    }
  }
}
```

The provider handles this conversion internally.

---

## Testing Plan

### Test 1: Anthropic Still Works
```bash
FLUX_PROVIDER=anthropic python -m flux
# Test: /stats, /history, edit commands
```

### Test 2: OpenAI Works
```bash
FLUX_PROVIDER=openai python -m flux
# Test: Same commands as above
```

### Test 3: Tool Calling Works
```bash
# Both providers
# Test: File operations (read, edit, write)
```

### Test 4: Streaming Works
```bash
# Both providers
# Verify: Text streams smoothly, no buffering issues
```

---

## Benefits

1. **No Sonnet Access? Use OpenAI!** - GPT-4o is comparable to Sonnet quality
2. **Cost Optimization** - Can use cheaper provider for simpler tasks
3. **Redundancy** - If one provider is down, switch to another
4. **Future-Proof** - Easy to add more providers (Google, Cohere, etc.)

---

## Cost Comparison

| Provider | Model | Input ($/1M) | Output ($/1M) | Quality |
|----------|-------|--------------|---------------|---------|
| Anthropic | Haiku | $0.25 | $1.25 | ⭐⭐⭐ |
| Anthropic | Sonnet 3.5 | $3.00 | $15.00 | ⭐⭐⭐⭐⭐ |
| OpenAI | GPT-4o | $2.50 | $10.00 | ⭐⭐⭐⭐⭐ |
| OpenAI | GPT-4 Turbo | $10.00 | $30.00 | ⭐⭐⭐⭐ |

**Recommendation**: Use `gpt-4o` (OpenAI) - similar cost to Sonnet but actually available!

---

## Migration Path

### Phase 1: Create Abstraction ✅
- [x] Create base_provider.py

### Phase 2: Refactor Anthropic
- [ ] Move to anthropic_provider.py
- [ ] Test thoroughly

### Phase 3: Add OpenAI
- [ ] Create openai_provider.py
- [ ] Test thoroughly

### Phase 4: Add Factory
- [ ] Create provider_factory.py
- [ ] Update config
- [ ] Update CLI

### Phase 5: Test & Document
- [ ] Test both providers
- [ ] Write usage docs
- [ ] Update README

---

## Next Actions

1. Implement `AnthropicProvider` class
2. Implement `OpenAIProvider` class  
3. Create `provider_factory.py`
4. Update `Config` class
5. Update `CLI` to use factory
6. Test with both providers
7. Document usage

**Expected timeline**: 2-3 hours of focused implementation

**Immediate benefit**: Can use GPT-4o today (better than Haiku, available now!)
