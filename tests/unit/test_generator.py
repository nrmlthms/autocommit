"""Unit tests for LLMCommitMessageGenerator class."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lazycommit.config import Config
from lazycommit.detector import ChangeSet, FileChange, FileStatus
from lazycommit.exceptions import ConfigurationError, ValidationError
from lazycommit.generator import LLMCommitMessageGenerator


class TestLLMCommitMessageGenerator:
    """Test cases for LLMCommitMessageGenerator class."""

    def test_init_with_config(self) -> None:
        """Test initialization with config."""
        config = Config(model="gpt-4", temperature=0.5, max_tokens=100)

        with patch("lazycommit.generator.OpenAI"):
            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")

            assert gen.config == config
            assert gen.model == "gpt-4"
            assert gen.api_key == "test-key"

    def test_init_without_api_key(self) -> None:
        """Test initialization without API key raises error."""
        config = Config()

        with pytest.raises(ConfigurationError, match="API key not found"):
            LLMCommitMessageGenerator(config=config)

    def test_init_with_base_url(self) -> None:
        """Test initialization with custom base URL."""
        config = Config(base_url="https://api.openrouter.ai/v1")

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            LLMCommitMessageGenerator(config=config, api_key="test-key")

            # Verify OpenAI was called with base_url
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["base_url"] == "https://api.openrouter.ai/v1"

    def test_validate_config_valid(self) -> None:
        """Test validation with valid config."""
        config = Config(temperature=0.7, max_tokens=100, max_message_length=500)

        with patch("lazycommit.generator.OpenAI"):
            # Should not raise
            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            assert gen.config.temperature == 0.7

    def test_validate_config_invalid_temperature_low(self) -> None:
        """Test validation rejects temperature too low."""
        config = Config(temperature=-0.1, max_tokens=100)

        with patch("lazycommit.generator.OpenAI"):
            with pytest.raises(ValidationError, match="Temperature must be between"):
                LLMCommitMessageGenerator(config=config, api_key="test-key")

    def test_validate_config_invalid_temperature_high(self) -> None:
        """Test validation rejects temperature too high."""
        config = Config(temperature=2.5, max_tokens=100)

        with patch("lazycommit.generator.OpenAI"):
            with pytest.raises(ValidationError, match="Temperature must be between"):
                LLMCommitMessageGenerator(config=config, api_key="test-key")

    def test_validate_config_invalid_max_tokens_zero(self) -> None:
        """Test validation rejects max_tokens of zero."""
        config = Config(temperature=0.7, max_tokens=0)

        with patch("lazycommit.generator.OpenAI"):
            with pytest.raises(ValidationError, match="max_tokens must be positive"):
                LLMCommitMessageGenerator(config=config, api_key="test-key")

    def test_validate_config_invalid_max_tokens_negative(self) -> None:
        """Test validation rejects negative max_tokens."""
        config = Config(temperature=0.7, max_tokens=-100)

        with patch("lazycommit.generator.OpenAI"):
            with pytest.raises(ValidationError, match="max_tokens must be positive"):
                LLMCommitMessageGenerator(config=config, api_key="test-key")

    def test_validate_config_invalid_max_message_length(self) -> None:
        """Test validation rejects invalid max_message_length."""
        config = Config(temperature=0.7, max_tokens=100, max_message_length=0)

        with patch("lazycommit.generator.OpenAI"):
            with pytest.raises(
                ValidationError, match="max_message_length must be positive"
            ):
                LLMCommitMessageGenerator(config=config, api_key="test-key")

    def test_validate_config_warns_high_max_tokens(self, capsys: Any) -> None:
        """Test warning for unusually high max_tokens."""
        config = Config(temperature=0.7, max_tokens=5000)

        with patch("lazycommit.generator.OpenAI"):
            LLMCommitMessageGenerator(config=config, api_key="test-key")

            captured = capsys.readouterr()
            assert "⚠" in captured.err
            assert "unusually high" in captured.err

    def test_estimate_token_count(self) -> None:
        """Test token count estimation."""
        config = Config()

        with patch("lazycommit.generator.OpenAI"):
            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")

            # Test various text lengths
            assert gen._estimate_token_count("") == 1
            assert gen._estimate_token_count("test") == 2
            assert gen._estimate_token_count("a" * 100) == 26
            assert gen._estimate_token_count("a" * 400) == 101

    def test_generate_from_changeset_no_changes(self) -> None:
        """Test generation with no changes."""
        config = Config()
        changeset = ChangeSet([], [], [])

        with patch("lazycommit.generator.OpenAI"):
            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            message = gen.generate_from_changeset(changeset, MagicMock())

            assert message == "No changes to commit"

    def test_generate_from_changeset_with_changes(self) -> None:
        """Test generation with changes."""
        config = Config(cache_enabled=False)  # Disable cache to test API call
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                    diff="@@ -1,1 +1,1 @@\n-old line\n+new line",
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "fix: update file.py"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")

            mock_detector = MagicMock()
            mock_detector.repo_path = Path("/test")

            message = gen.generate_from_changeset(changeset, mock_detector)

            assert message == "fix: update file.py"
            mock_client.chat.completions.create.assert_called_once()

    def test_generate_from_changeset_strips_quotes(self) -> None:
        """Test that generated messages have quotes stripped."""
        config = Config()
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        # Mock OpenAI response with quotes
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '"fix: update file.py"'

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            mock_detector = MagicMock()
            mock_detector.repo_path = Path("/test")

            message = gen.generate_from_changeset(changeset, mock_detector)

            assert message == "fix: update file.py"
            assert '"' not in message

    def test_generate_from_changeset_handles_none_response(self) -> None:
        """Test handling of None response from API."""
        config = Config(cache_enabled=False)  # Disable cache to test fallback
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        # Mock OpenAI response with None content
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            mock_detector = MagicMock()
            mock_detector.repo_path = Path("/test")

            message = gen.generate_from_changeset(changeset, mock_detector)

            # Should fall back to default message
            assert "chore: update" in message

    def test_generate_from_changeset_handles_exception(self, capsys: Any) -> None:
        """Test handling of API exception."""
        config = Config(cache_enabled=False)  # Disable cache to test fallback
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        # Mock OpenAI client to raise exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            mock_detector = MagicMock()
            mock_detector.repo_path = Path("/test")

            message = gen.generate_from_changeset(changeset, mock_detector)

            # Should fall back to default message
            assert "chore: update" in message

            # Should print warning
            captured = capsys.readouterr()
            assert "⚠" in captured.err
            assert "LLM generation failed" in captured.err

    def test_generate_warns_high_token_usage(self, capsys: Any) -> None:
        """Test warning for high estimated token usage."""
        config = Config(
            max_input_tokens=100,  # Low threshold for testing
            cache_enabled=False,  # Disable cache to test token warning
        )
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                    diff="@@ -1,1 +1,1 @@\n" + ("x" * 1000),  # Large diff
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "fix: update"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            mock_detector = MagicMock()
            mock_detector.repo_path = Path("/test")

            gen.generate_from_changeset(changeset, mock_detector)

            captured = capsys.readouterr()
            assert "⚠" in captured.err
            assert "token usage" in captured.err

    def test_build_context(self) -> None:
        """Test context building for LLM."""
        config = Config(max_context_files=5, max_diff_lines=10)
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/repo/file1.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                    diff="@@ -1,1 +1,1 @@\n-old\n+new",
                )
            ],
            unstaged_changes=[
                FileChange(
                    path=Path("/repo/file2.py"),
                    status=FileStatus.ADDED,
                    staged=False,
                )
            ],
            untracked_files=[Path("/repo/file3.py")],
        )

        with patch("lazycommit.generator.OpenAI"):
            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")

            mock_detector = MagicMock()
            mock_detector.repo_path = Path("/repo")

            context = gen._build_context(changeset, mock_detector)

            assert "Total files: 3" in context
            assert "file1.py" in context
            assert "file2.py" in context
            assert "file3.py" in context
            # Check for status indicators in new format
            assert "[M]" in context or "[A]" in context or "[?]" in context

    def test_fallback_message_single_file(self) -> None:
        """Test fallback message for single file."""
        config = Config()
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        with patch("lazycommit.generator.OpenAI"):
            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            message = gen._fallback_message(changeset)

            assert message == "chore: update file"

    def test_fallback_message_multiple_files(self) -> None:
        """Test fallback message for multiple files."""
        config = Config()
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file1.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                ),
                FileChange(
                    path=Path("/test/file2.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                ),
            ],
            unstaged_changes=[],
            untracked_files=[Path("/test/file3.py")],
        )

        with patch("lazycommit.generator.OpenAI"):
            gen = LLMCommitMessageGenerator(config=config, api_key="test-key")
            message = gen._fallback_message(changeset)

            assert message == "chore: update 3 files"
