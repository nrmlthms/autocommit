"""Unit tests for error formatting utilities."""

import sys
from io import StringIO

import pytest

from lazycommit.errors import (
    Colors,
    format_error,
    print_error,
    print_success,
    print_warning,
)
from lazycommit.exceptions import (
    APIError,
    AutoCommitError,
    ConfigurationError,
    GitError,
)


class TestColors:
    """Test cases for Colors class."""

    def test_disable_if_not_tty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test disabling colors when not a TTY."""
        # Mock stderr.isatty() to return False
        monkeypatch.setattr(sys.stderr, "isatty", lambda: False)

        Colors.disable_if_not_tty()

        # Colors should be empty strings
        assert Colors.RESET == ""
        assert Colors.RED == ""
        assert Colors.GREEN == ""


class TestFormatError:
    """Test cases for format_error function."""

    def test_format_autocommit_error(self) -> None:
        """Test formatting AutoCommitError."""
        error = AutoCommitError(
            message="Something went wrong", suggestion="Try this fix"
        )

        formatted = format_error(error, show_suggestion=True, use_colors=False)

        assert "Something went wrong" in formatted
        assert "Try this fix" in formatted
        assert "Suggestion:" in formatted

    def test_format_error_without_suggestion(self) -> None:
        """Test formatting error without showing suggestion."""
        error = AutoCommitError(
            message="Something went wrong", suggestion="Try this fix"
        )

        formatted = format_error(error, show_suggestion=False, use_colors=False)

        assert "Something went wrong" in formatted
        assert "Try this fix" not in formatted
        assert "Suggestion:" not in formatted

    def test_format_git_error_with_stderr(self) -> None:
        """Test formatting GitError with stderr."""
        error = GitError(
            message="Git command failed",
            stderr="fatal: remote error",
            suggestion="Check remote",
        )

        formatted = format_error(error, show_suggestion=True, use_colors=False)

        assert "Git command failed" in formatted
        assert "fatal: remote error" in formatted
        assert "Check remote" in formatted

    def test_format_generic_error(self) -> None:
        """Test formatting generic Exception."""
        error = Exception("Generic error")

        formatted = format_error(error, show_suggestion=True, use_colors=False)

        assert "Generic error" in formatted
        assert "Error:" in formatted

    def test_format_with_colors(self) -> None:
        """Test formatting with colors enabled."""
        error = AutoCommitError(message="Test error", suggestion="Test suggestion")

        # Just check it doesn't crash with colors
        formatted = format_error(error, show_suggestion=True, use_colors=True)
        assert "Test error" in formatted


class TestPrintError:
    """Test cases for print_error function."""

    def test_print_error_to_default_stderr(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing error to stderr."""
        error = AutoCommitError("Test error")

        print_error(error, use_colors=False)

        captured = capsys.readouterr()
        assert "Test error" in captured.err

    def test_print_error_to_custom_file(self) -> None:
        """Test printing error to custom file."""
        error = AutoCommitError("Test error")
        output = StringIO()

        print_error(error, use_colors=False, file=output)

        assert "Test error" in output.getvalue()

    def test_print_error_with_suggestion(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing error with suggestion."""
        error = ConfigurationError(message="Invalid config", config_key="temperature")

        print_error(error, show_suggestion=True, use_colors=False)

        captured = capsys.readouterr()
        assert "Invalid config" in captured.err
        assert "temperature" in captured.err


class TestPrintWarning:
    """Test cases for print_warning function."""

    def test_print_warning(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing warning message."""
        print_warning("This is a warning", use_colors=False)

        captured = capsys.readouterr()
        assert "This is a warning" in captured.err
        # Rich format uses emoji instead of "Warning:"
        assert "⚠" in captured.err


class TestPrintSuccess:
    """Test cases for print_success function."""

    def test_print_success(self, capsys: pytest.CaptureFixture) -> None:
        """Test printing success message."""
        print_success("Operation successful", use_colors=False)

        captured = capsys.readouterr()
        assert "Operation successful" in captured.out


class TestErrorContextInformation:
    """Test that errors include proper context."""

    def test_api_error_includes_suggestions(self) -> None:
        """Test APIError includes helpful suggestions."""
        error = APIError("API failed")

        formatted = format_error(error, show_suggestion=True, use_colors=False)

        assert "API key" in formatted
        assert "rate limit" in formatted.lower()

    def test_configuration_error_includes_config_location(self) -> None:
        """Test ConfigurationError mentions config file location."""
        error = ConfigurationError("Bad config", config_key="model")

        formatted = format_error(error, show_suggestion=True, use_colors=False)

        assert ".lazycommitrc" in formatted
        assert "model" in formatted
