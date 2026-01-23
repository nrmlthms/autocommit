"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all fixtures from git_scenarios
from tests.fixtures.git_scenarios import (  # noqa: E402
    empty_git_repo,
    git_repo_with_commits,
    git_repo_with_gitignore,
    git_repo_with_mixed_changes,
    git_repo_with_staged_changes,
    git_repo_with_unstaged_changes,
    git_repo_with_untracked_files,
)

# Re-export fixtures so they're available to all tests
__all__ = [
    "empty_git_repo",
    "git_repo_with_commits",
    "git_repo_with_staged_changes",
    "git_repo_with_unstaged_changes",
    "git_repo_with_untracked_files",
    "git_repo_with_gitignore",
    "git_repo_with_mixed_changes",
]


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
