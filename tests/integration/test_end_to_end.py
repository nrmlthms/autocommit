"""Integration tests for end-to-end workflows."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lazycommit.config import Config
from lazycommit.core import AutoCommit


class TestEndToEndWorkflows:
    """Integration tests for complete workflows."""

    def test_full_commit_workflow(self, git_repo_with_untracked_files: Path) -> None:
        """Test complete workflow from detection to commit."""
        config = Config(interactive_mode=False)

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "feat: add new files"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_untracked_files),
                api_key="test-key",
            )

            # Run without push (no remote configured)
            exit_code = autocommit.run(push=False, dry_run=False)

            assert exit_code == 0

            # Verify commit was created
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=git_repo_with_untracked_files,
                capture_output=True,
                text=True,
            )
            assert "feat: add new files" in result.stdout

    def test_staged_changes_workflow(self, git_repo_with_staged_changes: Path) -> None:
        """Test workflow with pre-staged changes."""
        config = Config(interactive_mode=False)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "chore: update files"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_staged_changes),
                api_key="test-key",
            )

            exit_code = autocommit.run(push=False, dry_run=False)

            assert exit_code == 0

            # Verify commit
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=git_repo_with_staged_changes,
                capture_output=True,
                text=True,
            )
            assert "chore: update files" in result.stdout

    def test_mixed_changes_workflow(self, git_repo_with_mixed_changes: Path) -> None:
        """Test workflow with staged, unstaged, and untracked changes."""
        config = Config(interactive_mode=False)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "refactor: update project"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_mixed_changes),
                api_key="test-key",
            )

            exit_code = autocommit.run(push=False, dry_run=False)

            assert exit_code == 0

            # Verify all changes were committed
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=git_repo_with_mixed_changes,
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == ""  # No uncommitted changes

    def test_dry_run_workflow(self, git_repo_with_untracked_files: Path) -> None:
        """Test dry run doesn't make actual changes."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.generator.OpenAI"):
            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_untracked_files),
                api_key="test-key",
            )

            # Get initial commit count
            result_before = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=git_repo_with_untracked_files,
                capture_output=True,
                text=True,
            )
            commit_count_before = int(result_before.stdout.strip())

            # Run in dry-run mode
            exit_code = autocommit.run(
                message="test: should not commit", dry_run=True, push=False
            )

            assert exit_code == 0

            # Verify no new commits
            result_after = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=git_repo_with_untracked_files,
                capture_output=True,
                text=True,
            )
            commit_count_after = int(result_after.stdout.strip())

            assert commit_count_after == commit_count_before

    def test_safe_mode_workflow(self, git_repo_with_commits: Path) -> None:
        """Test safe mode creates backup branch."""
        config = Config(interactive_mode=False)

        # Create a change
        (git_repo_with_commits / "test.txt").write_text("Test content\n")

        with patch("lazycommit.generator.OpenAI"):
            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_commits),
                api_key="test-key",
            )

            # Get initial branches
            subprocess.run(
                ["git", "branch"],
                cwd=git_repo_with_commits,
                capture_output=True,
                text=True,
            )

            # Run with safe mode (no push)
            exit_code = autocommit.run(
                message="test: add file",
                safe_mode=True,
                push=False,
                dry_run=False,
            )

            assert exit_code == 0

            # Verify backup branch was created
            result_after = subprocess.run(
                ["git", "branch"],
                cwd=git_repo_with_commits,
                capture_output=True,
                text=True,
            )
            branches_after = result_after.stdout

            # When push=False, backup branch is retained (not cleaned up)
            # This is expected behavior since cleanup only happens on successful push
            assert "lazycommit-backup" in branches_after

    def test_verbose_output(
        self, git_repo_with_untracked_files: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test verbose mode produces detailed output."""
        config = Config(interactive_mode=False, show_progress=False)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "feat: add files"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_untracked_files),
                api_key="test-key",
            )

            exit_code = autocommit.run(push=False, verbose=True, dry_run=False)

            assert exit_code == 0

            captured = capsys.readouterr()
            assert "Checking repository state" in captured.out
            assert "Generating commit message" in captured.out
            assert "Committed:" in captured.out
            assert "Untracked Files:" in captured.out

    def test_custom_message_workflow(self, git_repo_with_untracked_files: Path) -> None:
        """Test workflow with custom commit message (no LLM)."""
        config = Config(interactive_mode=False)

        with patch("lazycommit.generator.OpenAI"):
            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_untracked_files),
                api_key="test-key",
            )

            exit_code = autocommit.run(
                message="docs: add documentation",
                push=False,
                dry_run=False,
            )

            assert exit_code == 0

            # Verify custom message was used
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=git_repo_with_untracked_files,
                capture_output=True,
                text=True,
            )
            assert "docs: add documentation" in result.stdout

    def test_llm_failure_fallback(self, git_repo_with_untracked_files: Path) -> None:
        """Test that LLM failure uses fallback message."""
        config = Config(
            cache_enabled=False, interactive_mode=False
        )  # Disable cache to test fallback

        # Mock OpenAI to raise exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_untracked_files),
                api_key="test-key",
            )

            exit_code = autocommit.run(push=False, dry_run=False)

            assert exit_code == 0

            # Verify fallback message was used
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=git_repo_with_untracked_files,
                capture_output=True,
                text=True,
            )
            assert "chore: update" in result.stdout
