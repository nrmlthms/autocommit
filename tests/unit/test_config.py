"""Unit tests for Config class."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from lazycommit.config import Config, create_default_config_file


class TestConfig:
    """Test cases for Config class."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = Config()

        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 400  # Increased for commit messages with body
        assert config.max_message_length == 500
        assert config.max_context_files == 10
        assert config.max_diff_lines == 20
        assert config.max_input_tokens == 8000
        assert config.push_by_default is True
        assert config.safe_mode_by_default is False
        assert config.verbose_by_default is False
        assert config.api_key is None
        assert config.base_url is None
        assert config.default_repo_path is None

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = Config(
            model="gpt-4",
            temperature=0.5,
            max_tokens=200,
            max_message_length=1000,
            api_key="test-key",
        )

        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 200
        assert config.max_message_length == 1000
        assert config.api_key == "test-key"

    def test_load_from_file(self) -> None:
        """Test loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "model": "gpt-4",
                "temperature": 0.8,
                "max_tokens": 150,
                "push_by_default": False,
            }
            json.dump(config_data, f)
            config_file = Path(f.name)

        try:
            config = Config.load(config_file)

            assert config.model == "gpt-4"
            assert config.temperature == 0.8
            assert config.max_tokens == 150
            assert config.push_by_default is False
        finally:
            config_file.unlink()

    def test_load_with_invalid_json(self) -> None:
        """Test loading configuration from invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            config_file = Path(f.name)

        try:
            # Should fall back to defaults without raising an error
            config = Config.load(config_file)
            assert config.model == "gpt-4o-mini"  # Default value
        finally:
            config_file.unlink()

    def test_apply_env_vars(self) -> None:
        """Test applying environment variables."""
        # Save original env vars
        original_env = {}
        env_vars = [
            "OPENAI_API_KEY",
            "BASE_URL",
            "LAZYCOMMIT_MODEL",
            "LAZYCOMMIT_TEMPERATURE",
            "LAZYCOMMIT_MAX_TOKENS",
        ]
        for var in env_vars:
            original_env[var] = os.environ.get(var)

        try:
            # Set test env vars
            os.environ["OPENAI_API_KEY"] = "test-api-key"
            os.environ["BASE_URL"] = "https://test.example.com"
            os.environ["LAZYCOMMIT_MODEL"] = "gpt-4-turbo"
            os.environ["LAZYCOMMIT_TEMPERATURE"] = "0.9"
            os.environ["LAZYCOMMIT_MAX_TOKENS"] = "250"

            config = Config.load()

            assert config.api_key == "test-api-key"
            assert config.base_url == "https://test.example.com"
            assert config.model == "gpt-4-turbo"
            assert config.temperature == 0.9
            assert config.max_tokens == 250
        finally:
            # Restore original env vars
            for var, value in original_env.items():
                if value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = value

    def test_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config = Config(model="gpt-4", temperature=0.5)
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["model"] == "gpt-4"
        assert config_dict["temperature"] == 0.5
        assert "api_key" not in config_dict  # Sensitive data not included
        assert "base_url" not in config_dict

    def test_save_and_load(self) -> None:
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_file = Path(f.name)

        try:
            # Create and save config
            config1 = Config(
                model="gpt-4",
                temperature=0.6,
                max_tokens=300,
                push_by_default=False,
            )
            config1.save(config_file)

            # Load config
            config2 = Config.load(config_file)

            assert config2.model == "gpt-4"
            assert config2.temperature == 0.6
            assert config2.max_tokens == 300
            assert config2.push_by_default is False
        finally:
            config_file.unlink()

    def test_type_validation_in_apply_dict(self) -> None:
        """Test type validation when applying dictionary."""
        config = Config()

        # Test with correct types
        config._apply_dict({"temperature": 0.5, "max_tokens": 200})
        assert config.temperature == 0.5
        assert config.max_tokens == 200

        # Test with convertible types
        config._apply_dict({"temperature": "0.8", "max_tokens": "150"})
        assert config.temperature == 0.8
        assert config.max_tokens == 150

        # Test with invalid types (should be ignored)
        original_temp = config.temperature
        config._apply_dict({"temperature": [1, 2, 3]})  # Invalid type
        assert config.temperature == original_temp  # Unchanged

    def test_boolean_env_vars(self) -> None:
        """Test boolean environment variable parsing."""
        original_env = os.environ.get("LAZYCOMMIT_PUSH_BY_DEFAULT")

        try:
            # Test various true values
            for true_value in ["true", "TRUE", "1", "yes", "YES"]:
                os.environ["LAZYCOMMIT_PUSH_BY_DEFAULT"] = true_value
                config = Config.load()
                assert config.push_by_default is True, f"Failed for value: {true_value}"

            # Test false values
            for false_value in ["false", "FALSE", "0", "no", "NO"]:
                os.environ["LAZYCOMMIT_PUSH_BY_DEFAULT"] = false_value
                config = Config.load()
                assert config.push_by_default is False, (
                    f"Failed for value: {false_value}"
                )
        finally:
            if original_env is None:
                os.environ.pop("LAZYCOMMIT_PUSH_BY_DEFAULT", None)
            else:
                os.environ["LAZYCOMMIT_PUSH_BY_DEFAULT"] = original_env


class TestCreateDefaultConfigFile:
    """Test cases for create_default_config_file function."""

    def test_create_default_config_file(self) -> None:
        """Test creating default config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the home directory
            original_home = Path.home

            def mock_home() -> Path:
                return Path(tmpdir)

            Path.home = mock_home  # type: ignore

            try:
                created_file = create_default_config_file()
                assert created_file.exists()
                assert created_file.name == ".lazycommitrc"

                # Verify content
                with open(created_file) as f:
                    data = json.load(f)
                assert "model" in data
                assert "temperature" in data
            finally:
                Path.home = original_home  # type: ignore

    def test_create_default_config_file_already_exists(self) -> None:
        """Test error when config file already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".lazycommitrc"
            config_file.touch()

            original_home = Path.home

            def mock_home() -> Path:
                return Path(tmpdir)

            Path.home = mock_home  # type: ignore

            try:
                with pytest.raises(FileExistsError):
                    create_default_config_file()
            finally:
                Path.home = original_home  # type: ignore
