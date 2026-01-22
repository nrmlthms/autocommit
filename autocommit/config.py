"""Configuration management for AutoCommit."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union


@dataclass
class Config:
    """Configuration settings for AutoCommit."""

    # LLM Settings
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 100
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For OpenRouter or custom API endpoints

    # Commit Message Settings
    max_message_length: int = 500
    max_context_files: int = 10
    max_diff_lines: int = 20
    max_input_tokens: int = 8000  # Maximum estimated input tokens before warning

    # Behavior Settings
    push_by_default: bool = True
    safe_mode_by_default: bool = False
    verbose_by_default: bool = False

    # Repository Settings
    default_repo_path: Optional[str] = None

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "Config":
        """
        Load configuration from file and environment variables.

        Priority order (highest to lowest):
        1. Explicitly passed parameters (handled by callers)
        2. Environment variables
        3. Config file (~/.lazycommitrc)
        4. Default values

        Args:
            config_file: Optional path to config file (default: ~/.lazycommitrc)

        Returns:
            Config instance
        """
        config = cls()

        # Load from config file
        if config_file is None:
            config_file = Path.home() / ".lazycommitrc"

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    file_config = json.load(f)
                    config._apply_dict(file_config)
            except (json.JSONDecodeError, IOError) as e:
                # Silently ignore config file errors, use defaults
                pass

        # Override with environment variables
        config._apply_env_vars()

        return config

    def _apply_dict(self, config_dict: dict[str, Union[str, int, float, bool]]) -> None:
        """Apply configuration from a dictionary."""
        for key, value in config_dict.items():
            if hasattr(self, key):
                # Type validation
                expected_type = type(getattr(self, key))
                if expected_type == type(None):
                    # For Optional fields, just set the value
                    setattr(self, key, value)
                elif isinstance(value, expected_type):
                    setattr(self, key, value)
                elif expected_type in (int, float, str, bool):
                    # Try to convert
                    try:
                        setattr(self, key, expected_type(value))
                    except (ValueError, TypeError):
                        pass  # Ignore invalid values

    def _apply_env_vars(self) -> None:
        """Apply configuration from environment variables."""
        env_mappings: dict[str, Union[str, tuple[str, Callable[[str], Any]]]] = {
            "OPENAI_API_KEY": "api_key",
            "BASE_URL": "base_url",
            "LAZYCOMMIT_MODEL": "model",
            "LAZYCOMMIT_TEMPERATURE": ("temperature", float),
            "LAZYCOMMIT_MAX_TOKENS": ("max_tokens", int),
            "LAZYCOMMIT_MAX_MESSAGE_LENGTH": ("max_message_length", int),
            "LAZYCOMMIT_MAX_INPUT_TOKENS": ("max_input_tokens", int),
            "LAZYCOMMIT_PUSH_BY_DEFAULT": ("push_by_default", lambda x: x.lower() in ("true", "1", "yes")),
            "LAZYCOMMIT_SAFE_MODE": ("safe_mode_by_default", lambda x: x.lower() in ("true", "1", "yes")),
            "LAZYCOMMIT_VERBOSE": ("verbose_by_default", lambda x: x.lower() in ("true", "1", "yes")),
        }

        for env_var, mapping in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if isinstance(mapping, str):
                    # Direct mapping
                    setattr(self, mapping, value)
                else:
                    # Mapping with type conversion
                    attr_name, converter = mapping
                    try:
                        converted_value: Any = converter(value)
                        setattr(self, attr_name, converted_value)
                    except (ValueError, TypeError):
                        pass  # Ignore invalid values

    def to_dict(self) -> dict[str, Union[int, float, str, bool]]:
        """Convert configuration to dictionary."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_message_length": self.max_message_length,
            "max_context_files": self.max_context_files,
            "max_diff_lines": self.max_diff_lines,
            "max_input_tokens": self.max_input_tokens,
            "push_by_default": self.push_by_default,
            "safe_mode_by_default": self.safe_mode_by_default,
            "verbose_by_default": self.verbose_by_default,
        }

    def save(self, config_file: Optional[Path] = None) -> None:
        """
        Save configuration to file.

        Args:
            config_file: Optional path to config file (default: ~/.lazycommitrc)
        """
        if config_file is None:
            config_file = Path.home() / ".lazycommitrc"

        config_dict = self.to_dict()

        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2)


def create_default_config_file() -> Path:
    """
    Create a default .lazycommitrc file in the user's home directory.

    Returns:
        Path to the created config file
    """
    config_file = Path.home() / ".lazycommitrc"

    if config_file.exists():
        raise FileExistsError(f"Config file already exists at {config_file}")

    config = Config()
    config.save(config_file)

    return config_file
