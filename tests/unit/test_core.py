"""Unit tests for AutoCommit core class."""

import subprocess
import tempfile
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from lazycommit.config import Config
from lazycommit.core import AutoCommit
from lazycommit.detector import ChangeSet, FileChange, FileStatus
from lazycommit.exceptions import ValidationError


@pytest.fixture
def temp_git_repo() -> Iterator[Path]:
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
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

        # Create initial commit
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

        yield repo_path


class TestAutoCommit:
    """Test cases for AutoCommit class."""

    def test_init_with_config(self, temp_git_repo: Path) -> None:
        """Test initialization with config."""
        config = Config(model="gpt-4", temperature=0.5)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            assert autocommit.config == config
            assert autocommit.repo_path == temp_git_repo

    def test_init_without_config(self, temp_git_repo: Path) -> None:
        """Test initialization without config loads defaults."""
        with patch("lazycommit.core.Config.load") as mock_load:
            mock_load.return_value = Config()

            with patch("lazycommit.core.LLMCommitMessageGenerator"):
                autocommit = AutoCommit(
                    repo_path=str(temp_git_repo), api_key="test-key"
                )

                mock_load.assert_called_once()
                assert autocommit.config is not None

    def test_run_no_changes(
        self, temp_git_repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test run with no changes."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            exit_code = autocommit.run(dry_run=True)

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "No changes detected" in captured.out

    def test_run_with_custom_message(
        self, temp_git_repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test run with custom commit message."""
        config = Config(interactive_mode=False)

        # Create a change
        (temp_git_repo / "test.txt").write_text("Test content\n")

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            exit_code = autocommit.run(
                message="test: add test file", push=False, dry_run=False
            )

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "test: add test file" in captured.out

    def test_run_dry_run(
        self, temp_git_repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test dry run mode."""
        config = Config(interactive_mode=False)

        # Create a change
        (temp_git_repo / "test.txt").write_text("Test content\n")

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            exit_code = autocommit.run(
                message="test: add file", dry_run=True, push=False
            )

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out

    def test_run_with_generated_message(
        self, temp_git_repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test run with LLM-generated message."""
        config = Config(interactive_mode=False)

        # Create a change
        (temp_git_repo / "test.txt").write_text("Test content\n")

        # Mock the message generator
        mock_generator = MagicMock()
        mock_generator.generate_from_changeset.return_value = "feat: add test file"

        with patch("lazycommit.core.LLMCommitMessageGenerator") as mock_gen_class:
            mock_gen_class.return_value = mock_generator

            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            exit_code = autocommit.run(push=False, dry_run=False)

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "feat: add test file" in captured.out

    def test_validate_commit_message_valid(self, temp_git_repo: Path) -> None:
        """Test validating a valid commit message."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            message = "fix: resolve bug in parser"
            sanitized = autocommit._validate_commit_message(message)

            assert sanitized == message

    def test_validate_commit_message_strips_whitespace(
        self, temp_git_repo: Path
    ) -> None:
        """Test that commit message validation strips whitespace."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            message = "  fix: resolve bug  \n"
            sanitized = autocommit._validate_commit_message(message)

            assert sanitized == "fix: resolve bug"

    def test_validate_commit_message_empty(self, temp_git_repo: Path) -> None:
        """Test that empty commit message is rejected."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            with pytest.raises(ValidationError, match="cannot be empty"):
                autocommit._validate_commit_message("")

            with pytest.raises(ValidationError, match="cannot be empty"):
                autocommit._validate_commit_message("   ")

    def test_validate_commit_message_too_long(self, temp_git_repo: Path) -> None:
        """Test that overly long commit message is rejected."""
        config = Config(max_message_length=50)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            long_message = "fix: " + "x" * 100
            with pytest.raises(ValidationError, match="too long"):
                autocommit._validate_commit_message(long_message)

    def test_validate_commit_message_removes_control_chars(
        self, temp_git_repo: Path
    ) -> None:
        """Test that control characters are removed."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            message = "fix: resolve\x07bug"
            sanitized = autocommit._validate_commit_message(message)

            assert "\x07" not in sanitized
            assert sanitized == "fix: resolvebug"

    def test_display_changes(
        self, temp_git_repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test displaying changes."""
        config = Config(interactive_mode=False)
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file1.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[
                FileChange(
                    path=Path("/test/file2.py"),
                    status=FileStatus.ADDED,
                    staged=False,
                )
            ],
            untracked_files=[Path("/test/file3.py")],
        )

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            autocommit._display_changes(changeset, verbose=True)

            captured = capsys.readouterr()
            # Check for rich formatted output
            assert "1 staged" in captured.out
            assert "1 unstaged" in captured.out
            assert "1 untracked" in captured.out
            assert "Staged Changes" in captured.out
            assert "Unstaged Changes" in captured.out
            assert "Untracked Files" in captured.out

    def test_run_with_safe_mode(
        self, temp_git_repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test run with safe mode enabled."""
        config = Config(interactive_mode=False)

        # Create a change
        (temp_git_repo / "test.txt").write_text("Test content\n")

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            # Run with safe mode (no push to avoid remote errors)
            exit_code = autocommit.run(
                message="test: add file", push=False, safe_mode=True, verbose=True
            )

            assert exit_code == 0
            captured = capsys.readouterr()
            # Backup branch should be created
            assert "backup branch" in captured.out.lower()

    def test_commit_creates_commit(self, temp_git_repo: Path) -> None:
        """Test that _commit creates a git commit."""
        config = Config(interactive_mode=False)

        # Create and stage a file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("Test content\n")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            commit_sha = autocommit._commit("test: add test file")

            assert len(commit_sha) == 40  # Git SHA is 40 characters
            assert commit_sha.isalnum()

    def test_create_backup_branch(self, temp_git_repo: Path) -> None:
        """Test creating backup branch."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            backup_branch = autocommit._create_backup_branch()

            assert backup_branch.startswith("lazycommit-backup-")

            # Verify branch exists
            result = subprocess.run(
                ["git", "branch", "--list", backup_branch],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )
            assert backup_branch in result.stdout

    def test_delete_backup_branch(self, temp_git_repo: Path) -> None:
        """Test deleting backup branch."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            # Create backup branch
            backup_branch = autocommit._create_backup_branch()

            # Delete it
            autocommit._delete_backup_branch(backup_branch)

            # Verify it's deleted
            result = subprocess.run(
                ["git", "branch", "--list", backup_branch],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )
            assert backup_branch not in result.stdout

    def test_push_with_no_remote(
        self, temp_git_repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test push when no remote is configured."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.core.LLMCommitMessageGenerator"):
            autocommit = AutoCommit(
                config=config, repo_path=str(temp_git_repo), api_key="test-key"
            )

            # Should not raise error, just print warning
            autocommit._push()

            captured = capsys.readouterr()
            assert "No remote repository" in captured.out
