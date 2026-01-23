"""Test fixtures for different git scenarios."""

import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def empty_git_repo() -> Iterator[Path]:
    """Create an empty git repository (no commits)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        yield repo_path


@pytest.fixture
def git_repo_with_commits() -> Iterator[Path]:
    """Create a git repository with multiple commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create multiple commits
        (repo_path / "README.md").write_text("# Test Repo\n")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        (repo_path / "src").mkdir()
        (repo_path / "src" / "main.py").write_text("print('Hello')\n")
        subprocess.run(
            ["git", "add", "src/main.py"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add main.py"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        yield repo_path


@pytest.fixture
def git_repo_with_staged_changes() -> Iterator[Path]:
    """Create a git repository with staged changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Initial commit
        (repo_path / "README.md").write_text("# Test\n")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create staged changes
        (repo_path / "new_file.py").write_text("# New file\n")
        subprocess.run(
            ["git", "add", "new_file.py"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        (repo_path / "README.md").write_text("# Test\nModified\n")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, capture_output=True, check=True
        )

        yield repo_path


@pytest.fixture
def git_repo_with_unstaged_changes() -> Iterator[Path]:
    """Create a git repository with unstaged changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Initial commit
        (repo_path / "README.md").write_text("# Test\n")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create unstaged changes
        (repo_path / "README.md").write_text("# Test\nModified but not staged\n")

        yield repo_path


@pytest.fixture
def git_repo_with_untracked_files() -> Iterator[Path]:
    """Create a git repository with untracked files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Initial commit
        (repo_path / "README.md").write_text("# Test\n")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create untracked files
        (repo_path / "untracked1.py").write_text("# Untracked\n")
        (repo_path / "untracked2.txt").write_text("Text\n")

        yield repo_path


@pytest.fixture
def git_repo_with_gitignore() -> Iterator[Path]:
    """Create a git repository with .gitignore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create .gitignore
        (repo_path / ".gitignore").write_text("*.log\n__pycache__/\n.env\n")
        subprocess.run(
            ["git", "add", ".gitignore"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add gitignore"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create ignored files
        (repo_path / "test.log").write_text("Log content\n")
        (repo_path / "__pycache__").mkdir()
        (repo_path / "__pycache__" / "test.pyc").write_text("Binary\n")

        yield repo_path


@pytest.fixture
def git_repo_with_mixed_changes() -> Iterator[Path]:
    """Create a git repository with staged, unstaged, and untracked changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Initial commit
        (repo_path / "README.md").write_text("# Initial\n")
        (repo_path / "file1.py").write_text("# File 1\n")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Staged change
        (repo_path / "README.md").write_text("# Initial\n\nStaged change\n")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, capture_output=True, check=True
        )

        # Unstaged change
        (repo_path / "file1.py").write_text("# File 1\n# Unstaged change\n")

        # Untracked file
        (repo_path / "new_file.txt").write_text("New content\n")

        yield repo_path
