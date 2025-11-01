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
    
    # API Keys
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    
    # LLM Settings
    model: str = field(default_factory=lambda: os.getenv("FLUX_MODEL", "claude-3-5-sonnet-20240620"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("FLUX_MAX_TOKENS", "4096")))
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
        if not self.anthropic_api_key:
            raise ValueError(
                "\n❌ ANTHROPIC_API_KEY environment variable is required.\n"
                "   Please set it in your .env file or shell environment.\n"
                "   Get your API key from: https://console.anthropic.com/\n"
            )
        
        # Validate model selection
        self._validate_model()
        
        # Validate token limits
        self._validate_tokens()
        
        # Create directories
        self.flux_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_model(self) -> None:
        """Validate and warn about model selection."""
        valid_models = {
            "claude-3-5-sonnet-20240620": {"context": 200000, "recommended": True},
            "claude-3-5-sonnet-20241022": {"context": 200000, "recommended": False},  # Not widely available yet
            "claude-3-opus-20240229": {"context": 200000, "recommended": False},
            "claude-3-sonnet-20240229": {"context": 200000, "recommended": False},
            "claude-3-haiku-20240307": {"context": 200000, "recommended": False},
        }
        
        if self.model not in valid_models:
            warnings.warn(
                f"\n⚠️  Unknown model: {self.model}\n"
                f"   Supported models: {', '.join(valid_models.keys())}\n"
                f"   Proceeding anyway, but this may cause issues.\n",
                UserWarning
            )
        elif not valid_models[self.model].get("recommended"):
            print(
                f"\n💡 You're using {self.model}\n"
                f"   Consider upgrading to claude-3-5-sonnet-20240620 for best performance.\n",
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
