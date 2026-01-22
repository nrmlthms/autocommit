"""AutoCommit - Automatic git commit and push tool with LLM-generated messages."""

from .core import AutoCommit
from .detector import ChangeDetector, ChangeSet, FileChange, FileStatus
from .errors import print_error, print_success, print_warning
from .exceptions import (
    APIError,
    AutoCommitError,
    CommitFailedError,
    ConfigurationError,
    GitError,
    NoChangesError,
    NotAGitRepositoryError,
    PushFailedError,
    ValidationError,
)
from .generator import LLMCommitMessageGenerator

__version__ = "0.1.0"

__all__ = [
    "AutoCommit",
    "ChangeDetector",
    "ChangeSet",
    "FileChange",
    "FileStatus",
    "LLMCommitMessageGenerator",
    # Exceptions
    "AutoCommitError",
    "GitError",
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
]
