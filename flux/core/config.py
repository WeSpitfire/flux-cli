"""Configuration management for Flux."""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import warnings


@dataclass
class Config:
    """Flux configuration."""

    # Provider Settings
    provider: str = field(default_factory=lambda: os.getenv("FLUX_PROVIDER", "anthropic"))

    # API Keys
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))

    # LLM Settings
    model: str = field(default_factory=lambda: os.getenv("FLUX_MODEL", "claude-3-5-sonnet-20241022"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("FLUX_MAX_TOKENS", "8192")))
    max_history: int = 50000  # Updated for 200K models - can be overridden by CLI argument
    temperature: float = field(default_factory=lambda: float(os.getenv("FLUX_TEMPERATURE", "0.0")))

    # Paths
    flux_dir: Path = field(default_factory=lambda: Path.home() / ".flux")
    chroma_dir: Path = field(default_factory=lambda: Path(os.getenv("CHROMA_PERSIST_DIR", Path.home() / ".flux" / "chroma")))

    # Token limits
    max_context_tokens: int = 150000  # Leave room for response

    # Interactive settings
    require_approval: bool = field(default_factory=lambda: os.getenv("FLUX_REQUIRE_APPROVAL", "true").lower() == "true")
    auto_approve: bool = False  # Set via CLI flag

    def __post_init__(self):
        """Validate configuration and create directories."""
        # Validate provider
        self._validate_provider()

        # Validate model selection
        self._validate_model()

        # Set model-aware context limits
        self._set_model_aware_limits()

        # Validate token limits
        self._validate_tokens()

        # Create directories
        self.flux_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

    def _set_model_aware_limits(self) -> None:
        """Adjust context limits based on model capabilities.

        Different models have vastly different context windows:
        - Haiku: 8K total (need aggressive limits)
        - Sonnet: 200K total (can be generous)
        - Opus: 200K total (can be generous)
        """
        model_lower = self.model.lower()

        if "haiku" in model_lower:
            # Haiku: 8K context total
            # Reserve: ~1K for system prompt, ~500 for tool schemas, ~2K for response
            # Leaves ~4.5K for conversation history, use 3K to be safe
            if self.max_history > 3000:
                self.max_history = 3000
            self.max_context_tokens = 3000

        elif "sonnet" in model_lower:
            # Sonnet: 200K context, can be much more generous
            # Updated to use more of available context
            if self.max_history < 50000:
                self.max_history = 50000
            self.max_context_tokens = 150000

        elif "opus" in model_lower:
            # Opus: 200K context, very generous
            if self.max_history < 50000:
                self.max_history = 50000
            self.max_context_tokens = 180000

        elif "gpt" in model_lower:
            # OpenAI models - generally have good context
            # gpt-4o: 128K, gpt-4-turbo: 128K, gpt-3.5-turbo: 16K
            if "gpt-3.5" in model_lower:
                # 3.5-turbo has smaller context
                if self.max_history > 8000:
                    self.max_history = 8000
                self.max_context_tokens = 12000
            # else: keep defaults for gpt-4 variants

    def _validate_provider(self) -> None:
        """Validate provider configuration."""
        valid_providers = ["anthropic", "openai"]

        if self.provider not in valid_providers:
            raise ValueError(
                f"\n❌ Invalid FLUX_PROVIDER: {self.provider}\n"
                f"   Supported providers: {', '.join(valid_providers)}\n"
            )

        # Check for required API keys
        if self.provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "\n❌ ANTHROPIC_API_KEY environment variable is required.\n"
                "   Please set it in your .env file or shell environment.\n"
                "   Get your API key from: https://console.anthropic.com/\n"
            )

        if self.provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "\n❌ OPENAI_API_KEY environment variable is required.\n"
                "   Please set it in your .env file or shell environment.\n"
                "   Get your API key from: https://platform.openai.com/api-keys\n"
            )

    def _validate_model(self) -> None:
        """Validate and warn about model selection."""
        # Provider-specific model validation
        if self.provider == "anthropic":
            valid_models = {
                "claude-3-5-sonnet-20240620": {"context": 200000, "recommended": True},
                "claude-3-5-sonnet-20241022": {"context": 200000, "recommended": True},
                "claude-3-opus-20240229": {"context": 200000, "recommended": False},
                "claude-3-sonnet-20240229": {"context": 200000, "recommended": False},
                "claude-3-haiku-20240307": {"context": 200000, "recommended": False},
            }

            if self.model not in valid_models:
                warnings.warn(
                    f"\n⚠️  Unknown Anthropic model: {self.model}\n"
                    f"   Supported models: {', '.join(valid_models.keys())}\n"
                    f"   Proceeding anyway, but this may cause issues.\n",
                    UserWarning
                )
            elif not valid_models[self.model].get("recommended"):
                print(
                    f"\n💡 You're using {self.model}\n"
                    f"   Consider upgrading to claude-3-5-sonnet-20241022 for best performance.\n",
                    file=sys.stderr
                )

        elif self.provider == "openai":
            valid_models = [
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4-turbo-preview",
                "gpt-4-1106-preview",
                "gpt-4-0125-preview",
                "gpt-4",
                "gpt-3.5-turbo",
            ]

            # Check if model starts with any valid prefix
            if not any(self.model.startswith(m) for m in valid_models):
                warnings.warn(
                    f"\n⚠️  Unknown OpenAI model: {self.model}\n"
                    f"   Recommended models: gpt-4o, gpt-4-turbo, gpt-4\n"
                    f"   Proceeding anyway, but this may cause issues.\n",
                    UserWarning
                )

            # Recommend GPT-4o
            if "gpt-3.5" in self.model or "gpt-4" in self.model and "gpt-4o" not in self.model:
                print(
                    f"\n💡 You're using {self.model}\n"
                    f"   Consider using gpt-4o for best performance and value.\n",
                    file=sys.stderr
                )

    def _validate_tokens(self) -> None:
        """Validate token configuration."""
        if self.max_tokens > 8192:
            warnings.warn(
                f"\n⚠️  FLUX_MAX_TOKENS is set to {self.max_tokens}, which is very high.\n"
                f"   This may cause slower responses and higher costs.\n"
                f"   Recommended: 4096 for most use cases, 8192 for complex tasks.\n",
                UserWarning
            )

        if self.max_tokens < 1024:
            warnings.warn(
                f"\n⚠️  FLUX_MAX_TOKENS is set to {self.max_tokens}, which is very low.\n"
                f"   This may cause incomplete responses.\n"
                f"   Recommended: 4096 for most use cases.\n",
                UserWarning
            )

    @property
    def conversation_history_path(self) -> Path:
        """Path to conversation history file."""
        return self.flux_dir / "history.jsonl"

    @property
    def state_path(self) -> Path:
        """Path to state file."""
        return self.flux_dir / "state.json"
