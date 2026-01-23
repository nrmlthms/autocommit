"""Unit tests for ChangeDetector class."""

import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from lazycommit.detector import ChangeDetector, ChangeSet, FileChange, FileStatus
from lazycommit.exceptions import NotAGitRepositoryError


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


class TestFileStatus:
    """Test cases for FileStatus enum."""

    def test_file_status_values(self) -> None:
        """Test FileStatus enum values."""
        assert FileStatus.MODIFIED.value == "M"
        assert FileStatus.ADDED.value == "A"
        assert FileStatus.DELETED.value == "D"
        assert FileStatus.RENAMED.value == "R"
        assert FileStatus.COPIED.value == "C"
        assert FileStatus.UNTRACKED.value == "??"
        assert FileStatus.UNMERGED.value == "U"


class TestFileChange:
    """Test cases for FileChange dataclass."""

    def test_file_change_creation(self) -> None:
        """Test creating FileChange instance."""
        change = FileChange(
            path=Path("/test/file.py"),
            status=FileStatus.MODIFIED,
            staged=True,
            diff="@@ -1,1 +1,1 @@",
        )

        assert change.path == Path("/test/file.py")
        assert change.status == FileStatus.MODIFIED
        assert change.staged is True
        assert change.diff == "@@ -1,1 +1,1 @@"

    def test_file_change_repr(self) -> None:
        """Test FileChange string representation."""
        change = FileChange(
            path=Path("/test/file.py"), status=FileStatus.MODIFIED, staged=True
        )

        repr_str = repr(change)
        assert "MODIFIED" in repr_str
        assert "file.py" in repr_str
        assert "staged" in repr_str


class TestChangeSet:
    """Test cases for ChangeSet dataclass."""

    def test_empty_changeset(self) -> None:
        """Test empty changeset."""
        changeset = ChangeSet(
            staged_changes=[], unstaged_changes=[], untracked_files=[]
        )

        assert not changeset.has_changes
        assert changeset.total_changes == 0

    def test_changeset_with_staged_changes(self) -> None:
        """Test changeset with staged changes."""
        changes = [
            FileChange(
                path=Path("/test/file1.py"), status=FileStatus.MODIFIED, staged=True
            ),
            FileChange(
                path=Path("/test/file2.py"), status=FileStatus.ADDED, staged=True
            ),
        ]
        changeset = ChangeSet(
            staged_changes=changes, unstaged_changes=[], untracked_files=[]
        )

        assert changeset.has_changes
        assert changeset.total_changes == 2
        assert len(changeset.staged_changes) == 2

    def test_changeset_with_untracked_files(self) -> None:
        """Test changeset with untracked files."""
        changeset = ChangeSet(
            staged_changes=[],
            unstaged_changes=[],
            untracked_files=[Path("/test/new_file.py")],
        )

        assert changeset.has_changes
        assert changeset.total_changes == 1

    def test_changeset_repr(self) -> None:
        """Test ChangeSet string representation."""
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"), status=FileStatus.MODIFIED, staged=True
                )
            ],
            unstaged_changes=[],
            untracked_files=[Path("/test/new.py")],
        )

        repr_str = repr(changeset)
        assert "staged=1" in repr_str
        assert "untracked=1" in repr_str


class TestChangeDetector:
    """Test cases for ChangeDetector class."""

    def test_init_with_valid_repo(self, temp_git_repo: Path) -> None:
        """Test initializing with valid git repository."""
        detector = ChangeDetector(temp_git_repo)
        assert detector.repo_path == temp_git_repo.resolve()

    def test_init_with_invalid_repo(self) -> None:
        """Test initializing with non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(NotAGitRepositoryError, match="not a git repository"):
                ChangeDetector(tmpdir)

    def test_get_changes_no_changes(self, temp_git_repo: Path) -> None:
        """Test getting changes when there are none."""
        detector = ChangeDetector(temp_git_repo)
        changes = detector.get_changes(include_diffs=False)

        assert isinstance(changes, ChangeSet)
        assert not changes.has_changes
        assert changes.total_changes == 0

    def test_get_changes_with_modified_file(self, temp_git_repo: Path) -> None:
        """Test detecting modified file."""
        detector = ChangeDetector(temp_git_repo)

        # Modify existing file
        (temp_git_repo / "README.md").write_text("# Modified\n")

        changes = detector.get_changes(include_diffs=False)

        assert changes.has_changes
        assert len(changes.unstaged_changes) == 1
        assert changes.unstaged_changes[0].status == FileStatus.MODIFIED

    def test_get_changes_with_untracked_file(self, temp_git_repo: Path) -> None:
        """Test detecting untracked file."""
        detector = ChangeDetector(temp_git_repo)

        # Create new untracked file
        (temp_git_repo / "new_file.txt").write_text("New content\n")

        changes = detector.get_changes(include_diffs=False)

        assert changes.has_changes
        assert len(changes.untracked_files) == 1
        assert changes.untracked_files[0].name == "new_file.txt"

    def test_get_changes_with_staged_file(self, temp_git_repo: Path) -> None:
        """Test detecting staged file."""
        detector = ChangeDetector(temp_git_repo)

        # Create and stage new file
        new_file = temp_git_repo / "staged.txt"
        new_file.write_text("Staged content\n")
        subprocess.run(
            ["git", "add", "staged.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )

        changes = detector.get_changes(include_diffs=False)

        assert changes.has_changes
        assert len(changes.staged_changes) == 1
        assert changes.staged_changes[0].status == FileStatus.ADDED

    def test_get_changes_with_diffs(self, temp_git_repo: Path) -> None:
        """Test getting changes with diffs included."""
        detector = ChangeDetector(temp_git_repo)

        # Modify file
        (temp_git_repo / "README.md").write_text("# Modified Content\n")

        changes = detector.get_changes(include_diffs=True)

        assert changes.has_changes
        assert len(changes.unstaged_changes) == 1
        assert changes.unstaged_changes[0].diff is not None
        assert "Modified Content" in changes.unstaged_changes[0].diff

    def test_parse_status(self, temp_git_repo: Path) -> None:
        """Test parsing git status codes."""
        detector = ChangeDetector(temp_git_repo)

        assert detector._parse_status("M") == FileStatus.MODIFIED
        assert detector._parse_status("A") == FileStatus.ADDED
        assert detector._parse_status("D") == FileStatus.DELETED
        assert detector._parse_status("R") == FileStatus.RENAMED
        assert detector._parse_status("C") == FileStatus.COPIED
        assert detector._parse_status("U") == FileStatus.UNMERGED

        # Test unknown status (should default to MODIFIED)
        assert detector._parse_status("X") == FileStatus.MODIFIED

    def test_get_diff_stats(self, temp_git_repo: Path) -> None:
        """Test getting diff statistics."""
        detector = ChangeDetector(temp_git_repo)

        # Modify file with known changes
        readme = (temp_git_repo / "README.md").resolve()
        readme.write_text("# Test Repo\n\nNew line 1\nNew line 2\n")

        stats = detector.get_diff_stats(readme)

        assert isinstance(stats, dict)
        assert "additions" in stats
        assert "deletions" in stats
        assert "changes" in stats
        assert stats["additions"] > 0

    def test_stage_file(self, temp_git_repo: Path) -> None:
        """Test staging a file."""
        detector = ChangeDetector(temp_git_repo)

        # Create new file
        new_file = temp_git_repo / "to_stage.txt"
        new_file.write_text("Content\n")

        # Stage it
        detector.stage_file(new_file)

        # Verify it's staged
        changes = detector.get_changes(include_diffs=False)
        assert len(changes.staged_changes) == 1

    def test_stage_all(self, temp_git_repo: Path) -> None:
        """Test staging all changes."""
        detector = ChangeDetector(temp_git_repo)

        # Create multiple files
        (temp_git_repo / "file1.txt").write_text("Content 1\n")
        (temp_git_repo / "file2.txt").write_text("Content 2\n")
        (temp_git_repo / "README.md").write_text("# Modified\n")

        # Stage all
        detector.stage_all()

        # Verify all are staged
        changes = detector.get_changes(include_diffs=False)
        assert len(changes.staged_changes) == 3
        assert len(changes.unstaged_changes) == 0
        assert len(changes.untracked_files) == 0

    def test_unstage_file(self, temp_git_repo: Path) -> None:
        """Test unstaging a file."""
        detector = ChangeDetector(temp_git_repo)

        # Create and stage file
        new_file = temp_git_repo / "staged.txt"
        new_file.write_text("Content\n")
        detector.stage_file(new_file)

        # Unstage it
        detector.unstage_file(new_file)

        # Verify it's unstaged
        changes = detector.get_changes(include_diffs=False)
        assert len(changes.staged_changes) == 0
        assert len(changes.untracked_files) == 1

    def test_is_file_ignored(self, temp_git_repo: Path) -> None:
        """Test checking if file is ignored."""
        detector = ChangeDetector(temp_git_repo)

        # Create .gitignore
        gitignore = temp_git_repo / ".gitignore"
        gitignore.write_text("*.log\n")

        # Create ignored file
        log_file = temp_git_repo / "test.log"
        log_file.write_text("log content\n")

        assert detector.is_file_ignored(log_file)
        assert not detector.is_file_ignored(gitignore)

    def test_get_modified_files(self, temp_git_repo: Path) -> None:
        """Test getting modified files."""
        detector = ChangeDetector(temp_git_repo)

        # Modify file
        (temp_git_repo / "README.md").write_text("# Modified\n")

        modified_files = detector.get_modified_files()

        assert len(modified_files) == 1
        assert any("README.md" in str(f) for f in modified_files)

    def test_get_modified_files_since_ref(self, temp_git_repo: Path) -> None:
        """Test getting modified files since a git reference."""
        detector = ChangeDetector(temp_git_repo)

        # Create and commit a file
        new_file = temp_git_repo / "file1.txt"
        new_file.write_text("Content\n")
        subprocess.run(
            ["git", "add", "file1.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add file1"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )

        # Modify and commit another file
        (temp_git_repo / "README.md").write_text("# Modified\n")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Modify README"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )

        # Get files modified since HEAD~1
        modified_files = detector.get_modified_files(since="HEAD~1")

        assert len(modified_files) == 1
        assert any("README.md" in str(f) for f in modified_files)
