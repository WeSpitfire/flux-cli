"""Factory for creating LLM provider instances."""

from flux.core.config import Config
from flux.llm.base_provider import BaseLLMProvider
from flux.llm.anthropic_provider import AnthropicProvider
from flux.llm.openai_provider import OpenAIProvider


def create_provider(config: Config, enable_context_pruning: bool = True) -> BaseLLMProvider:
    """Create an LLM provider based on configuration.
    
    Args:
        config: Flux configuration
        enable_context_pruning: Enable automatic context pruning (Anthropic only)
        
    Returns:
        LLM provider instance
        
    Raises:
        ValueError: If provider is not supported
    """
    provider = config.provider.lower()
    
    if provider == "anthropic":
        return AnthropicProvider(config, enable_context_pruning=enable_context_pruning)
    
    elif provider == "openai":
        # OpenAI doesn't use context pruning (has larger context and better handling)
        return OpenAIProvider(config)
    
    else:
        raise ValueError(
            f"\n❌ Unsupported provider: {provider}\n"
            f"   Supported providers: anthropic, openai\n"
        )
