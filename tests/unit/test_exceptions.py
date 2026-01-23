"""Unit tests for custom exceptions."""

from lazycommit.exceptions import (
    APIError,
    AutoCommitError,
    CommitFailedError,
    ConfigurationError,
    GitError,
    GitStateError,
    NoChangesError,
    NotAGitRepositoryError,
    PushFailedError,
    ValidationError,
)


class TestAutoCommitError:
    """Test cases for AutoCommitError base class."""

    def test_init_with_message(self) -> None:
        """Test creating error with message only."""
        error = AutoCommitError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.suggestion is None

    def test_init_with_suggestion(self) -> None:
        """Test creating error with suggestion."""
        error = AutoCommitError(
            "Something went wrong", suggestion="Try running with --verbose"
        )

        assert error.message == "Something went wrong"
        assert error.suggestion == "Try running with --verbose"


class TestGitError:
    """Test cases for GitError."""

    def test_init_with_command_and_stderr(self) -> None:
        """Test creating GitError with command and stderr."""
        error = GitError(
            message="Command failed",
            command="git push",
            stderr="fatal: remote error",
            suggestion="Check your remote configuration",
        )

        assert error.message == "Command failed"
        assert error.command == "git push"
        assert error.stderr == "fatal: remote error"
        assert error.suggestion == "Check your remote configuration"


class TestNotAGitRepositoryError:
    """Test cases for NotAGitRepositoryError."""

    def test_init_with_path(self) -> None:
        """Test creating NotAGitRepositoryError."""
        error = NotAGitRepositoryError("/some/path")

        assert "/some/path" in error.message
        assert "not a git repository" in error.message
        assert error.suggestion is not None
        assert "git init" in error.suggestion
        assert error.path == "/some/path"


class TestGitStateError:
    """Test cases for GitStateError."""

    def test_init_with_state(self) -> None:
        """Test creating GitStateError."""
        error = GitStateError(
            state="merge", suggestion="Resolve conflicts and complete merge"
        )

        assert "merge" in error.message
        assert error.state == "merge"
        assert error.suggestion == "Resolve conflicts and complete merge"


class TestNoChangesError:
    """Test cases for NoChangesError."""

    def test_init(self) -> None:
        """Test creating NoChangesError."""
        error = NoChangesError()

        assert "No changes detected" in error.message
        assert error.suggestion is not None


class TestCommitFailedError:
    """Test cases for CommitFailedError."""

    def test_init_with_stderr(self) -> None:
        """Test creating CommitFailedError with stderr."""
        error = CommitFailedError(message="Commit failed", stderr="fatal: not possible")

        assert "Failed to create commit" in error.message
        assert error.stderr == "fatal: not possible"
        assert error.suggestion is not None


class TestPushFailedError:
    """Test cases for PushFailedError."""

    def test_init_with_stderr(self) -> None:
        """Test creating PushFailedError."""
        error = PushFailedError(stderr="fatal: no remote")

        assert "Failed to push" in error.message
        assert error.stderr == "fatal: no remote"
        assert error.suggestion is not None
        assert "remote" in error.suggestion.lower()
        assert "authentication" in error.suggestion.lower()


class TestAPIError:
    """Test cases for APIError."""

    def test_init_with_original_error(self) -> None:
        """Test creating APIError with original exception."""
        original = Exception("API timeout")
        error = APIError(message="API call failed", original_error=original)

        assert error.message == "API call failed"
        assert error.original_error == original
        assert error.suggestion is not None
        assert "API key" in error.suggestion


class TestConfigurationError:
    """Test cases for ConfigurationError."""

    def test_init_with_config_key(self) -> None:
        """Test creating ConfigurationError with config key."""
        error = ConfigurationError(message="Invalid value", config_key="temperature")

        assert error.message == "Invalid value"
        assert error.config_key == "temperature"
        assert error.suggestion is not None
        assert "temperature" in error.suggestion


class TestValidationError:
    """Test cases for ValidationError."""

    def test_init_with_field(self) -> None:
        """Test creating ValidationError with field."""
        error = ValidationError(message="Value out of range", field="max_tokens")

        assert error.message == "Value out of range"
        assert error.field == "max_tokens"
