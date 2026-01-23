"""Integration tests for git state handling in AutoCommit."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lazycommit import AutoCommit
from lazycommit.config import Config


@pytest.fixture
def git_repo_with_commit() -> Path:
    """Create a temporary git repository with initial commit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir).resolve()

        # Initialize git repo with main as default branch
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
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

        # Create initial commit
        test_file = repo_path / "test.txt"
        test_file.write_text("initial content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        yield repo_path


class TestAutoCommitGitStates:
    """Test AutoCommit behavior with different git states."""

    def test_autocommit_normal_state(self, git_repo_with_commit: Path) -> None:
        """Test AutoCommit in normal repository state."""
        config = Config(interactive_mode=False)

        # Add a change
        test_file = git_repo_with_commit / "new_file.txt"
        test_file.write_text("new content")

        # Mock OpenAI API
        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "feat: add new file"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_commit),
                api_key="test-key",
            )

            # Should succeed
            exit_code = autocommit.run(push=False, dry_run=False)
            assert exit_code == 0

    def test_autocommit_detached_head_warns_but_allows(
        self, git_repo_with_commit: Path, capsys
    ) -> None:
        """Test AutoCommit warns about detached HEAD but allows commit."""
        config = Config(interactive_mode=False)

        # Get current HEAD and detach
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo_with_commit,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()

        subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        # Add a change
        test_file = git_repo_with_commit / "new_file.txt"
        test_file.write_text("new content")

        # Mock OpenAI API
        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "feat: add new file"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_commit),
                api_key="test-key",
            )

            # Should succeed but with warning
            exit_code = autocommit.run(push=False, dry_run=False)
            assert exit_code == 0

            # Check for warning in output
            captured = capsys.readouterr()
            assert "detached" in captured.err.lower()

    def test_autocommit_merge_conflict_fails(self, git_repo_with_commit: Path) -> None:
        """Test AutoCommit fails with merge conflict."""
        config = Config(interactive_mode=False)

        # Create merge conflict
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        test_file = git_repo_with_commit / "test.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        test_file.write_text("main content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        # Create merge conflict
        subprocess.run(
            ["git", "merge", "feature"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=False,
        )

        autocommit = AutoCommit(
            config=config,
            repo_path=str(git_repo_with_commit),
            api_key="test-key",
        )

        # Should fail with GitStateError
        exit_code = autocommit.run(push=False, dry_run=False)
        assert exit_code == 1

    def test_autocommit_rebase_in_progress_fails(
        self, git_repo_with_commit: Path
    ) -> None:
        """Test AutoCommit fails during rebase."""
        config = Config(interactive_mode=False)

        # Create rebase situation
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        test_file = git_repo_with_commit / "test.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        test_file.write_text("main content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "checkout", "feature"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        # Start rebase (will fail with conflict)
        subprocess.run(
            ["git", "rebase", "main"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=False,
        )

        autocommit = AutoCommit(
            config=config,
            repo_path=str(git_repo_with_commit),
            api_key="test-key",
        )

        # Should fail with GitStateError
        exit_code = autocommit.run(push=False, dry_run=False)
        assert exit_code == 1

    def test_autocommit_no_changes(self, git_repo_with_commit: Path) -> None:
        """Test AutoCommit with no changes returns success."""
        config = Config(interactive_mode=False)

        autocommit = AutoCommit(
            config=config,
            repo_path=str(git_repo_with_commit),
            api_key="test-key",
        )

        # Should succeed with message about no changes
        exit_code = autocommit.run(push=False, dry_run=False)
        assert exit_code == 0

    def test_autocommit_dry_run_detached_head(
        self, git_repo_with_commit: Path, capsys
    ) -> None:
        """Test dry run shows warning for detached HEAD."""
        config = Config(interactive_mode=False)

        # Detach HEAD
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo_with_commit,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()

        subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        # Add a change
        test_file = git_repo_with_commit / "new_file.txt"
        test_file.write_text("new content")

        # Mock OpenAI API
        with patch("lazycommit.generator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "feat: add new file"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            autocommit = AutoCommit(
                config=config,
                repo_path=str(git_repo_with_commit),
                api_key="test-key",
            )

            # Dry run should succeed and show warning
            exit_code = autocommit.run(push=False, dry_run=True)
            assert exit_code == 0

            captured = capsys.readouterr()
            assert (
                "detached" in captured.err.lower() or "detached" in captured.out.lower()
            )


class TestGitStateErrorMessages:
    """Test that error messages are helpful for different git states."""

    def test_merge_conflict_error_message(
        self, git_repo_with_commit: Path, capsys
    ) -> None:
        """Test merge conflict error message is helpful."""
        config = Config(interactive_mode=False)

        # Create merge conflict
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        test_file = git_repo_with_commit / "test.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        test_file.write_text("main content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "merge", "feature"],
            cwd=git_repo_with_commit,
            capture_output=True,
            check=False,
        )

        autocommit = AutoCommit(
            config=config,
            repo_path=str(git_repo_with_commit),
            api_key="test-key",
        )

        exit_code = autocommit.run(push=False, dry_run=False)
        assert exit_code == 1

        captured = capsys.readouterr()
        error_output = captured.err

        # Check for helpful information in error message
        assert "merge" in error_output.lower()
        assert "conflict" in error_output.lower() or "abort" in error_output.lower()
