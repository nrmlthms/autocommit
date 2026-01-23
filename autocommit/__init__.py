"""AutoCommit - Automatic git commit and push tool with LLM-generated messages."""

from .cache import CommitMessageCache
from .core import AutoCommit
from .detector import ChangeDetector, ChangeSet, FileChange, FileStatus
from .errors import print_error, print_success, print_warning
from .exceptions import (
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
from .generator import LLMCommitMessageGenerator
from .git_state import GitState, GitStateDetector, RepositoryState
from .retry import exponential_backoff, retry_on_api_error

__version__ = "0.1.0"

__all__ = [
    "AutoCommit",
    "ChangeDetector",
    "ChangeSet",
    "FileChange",
    "FileStatus",
    "LLMCommitMessageGenerator",
    "CommitMessageCache",
    # Git state
    "GitState",
    "GitStateDetector",
    "RepositoryState",
    # Exceptions
    "AutoCommitError",
    "GitError",
    "GitStateError",
    "NotAGitRepositoryError",
    "NoChangesError",
    "CommitFailedError",
    "PushFailedError",
    "APIError",
    "ConfigurationError",
    "ValidationError",
    # Error utilities
    "print_error",
    "print_warning",
    "print_success",
    # Retry utilities
    "exponential_backoff",
    "retry_on_api_error",
]
