"""Custom exceptions for AutoCommit."""

from typing import Optional


class AutoCommitError(Exception):
    """Base exception for AutoCommit errors."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        """
        Initialize AutoCommit error.

        Args:
            message: Error message
            suggestion: Optional actionable suggestion for fixing the error
        """
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)


class GitError(AutoCommitError):
    """Git command failed."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        stderr: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        """
        Initialize Git error.

        Args:
            message: Error message
            command: The git command that failed
            stderr: Standard error output from git
            suggestion: Optional actionable suggestion
        """
        self.command = command
        self.stderr = stderr
        super().__init__(message, suggestion)


class NotAGitRepositoryError(GitError):
    """Directory is not a git repository."""

    def __init__(self, path: str):
        """Initialize NotAGitRepositoryError."""
        super().__init__(
            message=f"'{path}' is not a git repository",
            suggestion="Run 'git init' to initialize a git repository or navigate to an existing git repository.",
        )
        self.path = path


class NoChangesError(AutoCommitError):
    """No changes detected to commit."""

    def __init__(self) -> None:
        """Initialize NoChangesError."""
        super().__init__(
            message="No changes detected",
            suggestion="Make some changes to files, or check if changes are already committed.",
        )


class GitStateError(GitError):
    """Repository is in an unsafe state for committing."""

    def __init__(self, state: str, suggestion: Optional[str] = None):
        """
        Initialize GitStateError.

        Args:
            state: Description of the current git state
            suggestion: Optional actionable suggestion for resolving the state
        """
        super().__init__(
            message=f"Repository is in {state} state",
            suggestion=suggestion,
        )
        self.state = state


class CommitFailedError(GitError):
    """Commit creation failed."""

    def __init__(self, message: str, stderr: Optional[str] = None):
        """Initialize CommitFailedError."""
        super().__init__(
            message=f"Failed to create commit: {message}",
            stderr=stderr,
            suggestion="Check that all files are properly staged and there are no git conflicts.",
        )


class PushFailedError(GitError):
    """Push to remote failed."""

    def __init__(self, stderr: Optional[str] = None):
        """Initialize PushFailedError."""
        suggestion = (
            "Common causes:\n"
            "  • No remote repository configured (run: git remote add origin <url>)\n"
            "  • Authentication failed (check your credentials)\n"
            "  • Remote branch diverged (run: git pull --rebase)\n"
            "  • Network connectivity issues"
        )
        super().__init__(
            message="Failed to push to remote",
            stderr=stderr,
            suggestion=suggestion,
        )


class APIError(AutoCommitError):
    """LLM API error."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize APIError.

        Args:
            message: Error message
            original_error: Original exception from API
        """
        suggestion = (
            "Common causes:\n"
            "  • Invalid or missing API key (check OPENAI_API_KEY environment variable)\n"
            "  • API rate limit exceeded (wait and retry)\n"
            "  • Network connectivity issues\n"
            "  • Invalid model name in config"
        )
        super().__init__(message=message, suggestion=suggestion)
        self.original_error = original_error


class ConfigurationError(AutoCommitError):
    """Configuration error."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        """
        Initialize ConfigurationError.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
        """
        suggestion = (
            "Check your configuration file (~/.lazycommitrc) or environment variables"
        )
        if config_key:
            suggestion += f" for the '{config_key}' setting"
        super().__init__(message=message, suggestion=suggestion)
        self.config_key = config_key


class ValidationError(AutoCommitError):
    """Input validation error."""

    def __init__(self, message: str, field: Optional[str] = None):
        """
        Initialize ValidationError.

        Args:
            message: Error message
            field: The field that failed validation
        """
        super().__init__(message=message)
        self.field = field
