"""Unit tests for git state detection."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from lazycommit.git_state import GitState, GitStateDetector, RepositoryState


@pytest.fixture
def git_repo() -> Path:
    """Create a temporary git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir).resolve()

        # Initialize git repo
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


class TestGitStateDetector:
    """Test cases for GitStateDetector."""

    def test_normal_state(self, git_repo: Path) -> None:
        """Test detection of normal repository state."""
        detector = GitStateDetector(git_repo)
        state = detector.get_state()

        assert state.state == GitState.NORMAL
        assert state.is_safe_for_commit is True
        assert state.branch_name == "main" or state.branch_name == "master"
        assert state.head_commit is not None
        assert len(state.conflicted_files) == 0

    def test_detached_head_state(self, git_repo: Path) -> None:
        """Test detection of detached HEAD state."""
        # Get current HEAD commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()

        # Detach HEAD
        subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        detector = GitStateDetector(git_repo)
        state = detector.get_state()

        assert state.state == GitState.DETACHED_HEAD
        assert state.is_safe_for_commit is True  # Can commit but with warning
        assert state.branch_name is None
        assert state.head_commit is not None
        assert "detached" in state.suggestion.lower()

    def test_merge_in_progress_with_conflicts(self, git_repo: Path) -> None:
        """Test detection of merge in progress with conflicts."""
        # Create a branch with conflicting changes
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        test_file = git_repo / "test.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Switch back to main and create conflicting change
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        test_file.write_text("main content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Try to merge (this will create a conflict)
        subprocess.run(
            ["git", "merge", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=False,  # Expected to fail
        )

        detector = GitStateDetector(git_repo)
        state = detector.get_state()

        assert state.state == GitState.MERGE_IN_PROGRESS
        assert state.is_safe_for_commit is False
        assert len(state.conflicted_files) > 0
        assert "test.txt" in state.conflicted_files
        assert "conflict" in state.suggestion.lower()
        assert "merge --abort" in state.suggestion.lower()

    def test_merge_in_progress_resolved(self, git_repo: Path) -> None:
        """Test detection of merge in progress with conflicts resolved."""
        # Create a branch with non-conflicting changes
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        new_file = git_repo / "feature.txt"
        new_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "feature.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Switch back to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Merge with --no-commit to leave merge in progress
        subprocess.run(
            ["git", "merge", "--no-commit", "--no-ff", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=False,
        )

        detector = GitStateDetector(git_repo)
        state = detector.get_state()

        assert state.state == GitState.MERGE_IN_PROGRESS
        assert state.is_safe_for_commit is True  # No conflicts
        assert len(state.conflicted_files) == 0

    def test_rebase_in_progress(self, git_repo: Path) -> None:
        """Test detection of rebase in progress."""
        # Create a branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Create conflicting changes that will cause rebase to stop
        test_file = git_repo / "test.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Go back to main and create conflicting commit
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        test_file.write_text("main content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Go back to feature and try to rebase (will fail with conflict)
        subprocess.run(
            ["git", "checkout", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "rebase", "main"],
            cwd=git_repo,
            capture_output=True,
            check=False,  # Expected to fail
        )

        detector = GitStateDetector(git_repo)
        state = detector.get_state()

        assert state.state in [
            GitState.REBASE_IN_PROGRESS,
            GitState.REBASE_MERGE,
            GitState.REBASE_INTERACTIVE,
        ]
        assert state.is_safe_for_commit is False
        assert "rebase" in state.suggestion.lower()
        assert "rebase --abort" in state.suggestion.lower()

    def test_cherry_pick_in_progress(self, git_repo: Path) -> None:
        """Test detection of cherry-pick in progress."""
        # Create a branch with a commit
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        test_file = git_repo / "test.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        feature_commit = result.stdout.strip()

        # Go back to main and create conflicting content
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        test_file.write_text("main content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Try to cherry-pick (will create conflict)
        subprocess.run(
            ["git", "cherry-pick", feature_commit],
            cwd=git_repo,
            capture_output=True,
            check=False,  # Expected to fail
        )

        detector = GitStateDetector(git_repo)
        state = detector.get_state()

        # Check if cherry-pick is actually in progress
        git_dir = git_repo / ".git"
        if (git_dir / "CHERRY_PICK_HEAD").exists():
            assert state.state == GitState.CHERRY_PICK_IN_PROGRESS
            assert state.is_safe_for_commit is False
            assert "cherry-pick" in state.suggestion.lower()
            assert "cherry-pick --abort" in state.suggestion.lower()

    def test_check_state_safety_normal(self, git_repo: Path) -> None:
        """Test state safety check for normal state."""
        detector = GitStateDetector(git_repo)
        is_safe, reason = detector.check_state_safety()

        assert is_safe is True
        assert reason is None

    def test_check_state_safety_merge_conflict(self, git_repo: Path) -> None:
        """Test state safety check for merge conflict."""
        # Create merge conflict
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        test_file = git_repo / "test.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        test_file.write_text("main content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            ["git", "merge", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=False,
        )

        detector = GitStateDetector(git_repo)
        is_safe, reason = detector.check_state_safety()

        assert is_safe is False
        assert reason is not None
        assert "conflict" in reason.lower()

    def test_check_state_safety_detached_head(self, git_repo: Path) -> None:
        """Test state safety check for detached HEAD (safe with warning)."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()

        subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        detector = GitStateDetector(git_repo)
        is_safe, reason = detector.check_state_safety()

        assert is_safe is True  # Safe but with warning
        assert reason is not None
        assert "detached" in reason.lower()


class TestRepositoryState:
    """Test cases for RepositoryState dataclass."""

    def test_repository_state_creation(self) -> None:
        """Test creating a RepositoryState object."""
        state = RepositoryState(
            state=GitState.NORMAL,
            is_safe_for_commit=True,
            branch_name="main",
            head_commit="abc123",
        )

        assert state.state == GitState.NORMAL
        assert state.is_safe_for_commit is True
        assert state.branch_name == "main"
        assert state.head_commit == "abc123"
        assert state.conflicted_files == []
        assert state.suggestion is None

    def test_repository_state_with_conflicts(self) -> None:
        """Test creating a RepositoryState with conflicts."""
        state = RepositoryState(
            state=GitState.MERGE_IN_PROGRESS,
            is_safe_for_commit=False,
            branch_name="main",
            head_commit="abc123",
            conflicted_files=["file1.py", "file2.py"],
            suggestion="Resolve conflicts",
        )

        assert state.state == GitState.MERGE_IN_PROGRESS
        assert state.is_safe_for_commit is False
        assert len(state.conflicted_files) == 2
        assert "file1.py" in state.conflicted_files
        assert state.suggestion == "Resolve conflicts"


class TestGitStateEnum:
    """Test cases for GitState enum."""

    def test_git_state_values(self) -> None:
        """Test that all git states have correct values."""
        assert GitState.NORMAL.value == "normal"
        assert GitState.MERGE_IN_PROGRESS.value == "merge"
        assert GitState.REBASE_IN_PROGRESS.value == "rebase"
        assert GitState.DETACHED_HEAD.value == "detached"
        assert GitState.CHERRY_PICK_IN_PROGRESS.value == "cherry-pick"
        assert GitState.REVERT_IN_PROGRESS.value == "revert"
        assert GitState.BISECT_IN_PROGRESS.value == "bisect"
