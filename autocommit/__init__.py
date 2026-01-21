"""AutoCommit - Automatic git commit and push tool with LLM-generated messages."""

from .core import AutoCommit
from .detector import ChangeDetector, ChangeSet, FileChange, FileStatus
from .generator import LLMCommitMessageGenerator

__version__ = "0.1.0"

__all__ = [
    "AutoCommit",
    "ChangeDetector",
    "ChangeSet",
    "FileChange",
    "FileStatus",
    "LLMCommitMessageGenerator",
]
