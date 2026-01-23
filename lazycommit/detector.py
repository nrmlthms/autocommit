"""Change detection component for tracking git repository changes."""

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set, Union

from .exceptions import NotAGitRepositoryError


class FileStatus(Enum):
    """Git file status types."""

    MODIFIED = "M"
    ADDED = "A"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNTRACKED = "??"
    UNMERGED = "U"


@dataclass
class FileChange:
    """Represents a single file change."""

    path: Path
    status: FileStatus
    staged: bool
    diff: Optional[str] = None

    def __repr__(self) -> str:
        staged_str = "staged" if self.staged else "unstaged"
        return f"FileChange({self.status.name}, {self.path}, {staged_str})"


@dataclass
class ChangeSet:
    """Collection of changes in the repository."""

    staged_changes: List[FileChange]
    unstaged_changes: List[FileChange]
    untracked_files: List[Path]

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(
            self.staged_changes or self.unstaged_changes or self.untracked_files
        )

    @property
    def total_changes(self) -> int:
        """Total number of changed files."""
        return (
            len(self.staged_changes)
            + len(self.unstaged_changes)
            + len(self.untracked_files)
        )

    def __repr__(self) -> str:
        return (
            f"ChangeSet(staged={len(self.staged_changes)}, "
            f"unstaged={len(self.unstaged_changes)}, "
            f"untracked={len(self.untracked_files)})"
        )


class ChangeDetector:
    """Detect and analyze changes in a git repository."""

    def __init__(self, repo_path: Union[str, Path] = "."):
        """
        Initialize the change detector.

        Args:
            repo_path: Path to the git repository (default: current directory)
        """
        self.repo_path = Path(repo_path).resolve()
        self._verify_git_repo()

    def _verify_git_repo(self) -> None:
        """Verify that the path is a git repository."""
        try:
            self._run_git_command(["rev-parse", "--git-dir"])
        except subprocess.CalledProcessError:
            raise NotAGitRepositoryError(str(self.repo_path))

    def _run_git_command(
        self, args: List[str], check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command in the repository."""
        return subprocess.run(
            ["git", "-C", str(self.repo_path)] + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def get_changes(self, include_diffs: bool = True) -> ChangeSet:
        """
        Get all changes in the repository.

        Args:
            include_diffs: Whether to include diff content for each change

        Returns:
            ChangeSet containing all detected changes
        """
        staged_changes = self._get_staged_changes(include_diffs)
        unstaged_changes = self._get_unstaged_changes(include_diffs)
        untracked_files = self._get_untracked_files()

        return ChangeSet(
            staged_changes=staged_changes,
            unstaged_changes=unstaged_changes,
            untracked_files=untracked_files,
        )

    def _get_staged_changes(self, include_diffs: bool = True) -> List[FileChange]:
        """Get staged changes."""
        result = self._run_git_command(["diff", "--cached", "--name-status"])
        changes = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            status_code = parts[0]
            status = self._parse_status(
                status_code[0]
            )  # First char is the status (R100 -> R)

            # Handle renamed files: R<percentage>\told_path\tnew_path
            if status == FileStatus.RENAMED and len(parts) >= 3:
                # parts[1] is old_path, parts[2] is new_path
                file_path = parts[2]  # Use new path for current reference
            else:
                file_path = parts[1]

            path = self.repo_path / file_path

            diff = None
            if include_diffs and status != FileStatus.DELETED:
                diff = self._get_file_diff(file_path, staged=True)

            changes.append(FileChange(path=path, status=status, staged=True, diff=diff))

        return changes

    def _get_unstaged_changes(self, include_diffs: bool = True) -> List[FileChange]:
        """Get unstaged changes (modified but not staged)."""
        result = self._run_git_command(["diff", "--name-status"])
        changes = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            status_code = parts[0]
            status = self._parse_status(
                status_code[0]
            )  # First char is the status (R100 -> R)

            # Handle renamed files: R<percentage>\told_path\tnew_path
            if status == FileStatus.RENAMED and len(parts) >= 3:
                # parts[1] is old_path, parts[2] is new_path
                file_path = parts[2]  # Use new path for current reference
            else:
                file_path = parts[1]

            path = self.repo_path / file_path

            diff = None
            if include_diffs and status != FileStatus.DELETED:
                diff = self._get_file_diff(file_path, staged=False)

            changes.append(
                FileChange(path=path, status=status, staged=False, diff=diff)
            )

        return changes

    def _get_untracked_files(self) -> List[Path]:
        """Get untracked files."""
        result = self._run_git_command(["ls-files", "--others", "--exclude-standard"])
        untracked = []

        for line in result.stdout.strip().split("\n"):
            if line:
                untracked.append(self.repo_path / line)

        return untracked

    def _parse_status(self, status_code: str) -> FileStatus:
        """
        Parse git status code to FileStatus enum.

        Args:
            status_code: Single character git status code

        Returns:
            Corresponding FileStatus enum value. Defaults to FileStatus.MODIFIED
            for unknown status codes.
        """
        status_map: dict[str, FileStatus] = {
            "M": FileStatus.MODIFIED,
            "A": FileStatus.ADDED,
            "D": FileStatus.DELETED,
            "R": FileStatus.RENAMED,
            "C": FileStatus.COPIED,
            "U": FileStatus.UNMERGED,
        }
        # Explicitly return MODIFIED as default for unknown status codes
        return status_map.get(status_code, FileStatus.MODIFIED)

    def _get_file_diff(self, file_path: str, staged: bool = False) -> str:
        """Get diff for a specific file."""
        args = ["diff"]
        if staged:
            args.append("--cached")
        args.append(file_path)

        result = self._run_git_command(args)
        return result.stdout

    def get_diff_stats(self, file_path: Union[str, Path]) -> dict[str, int]:
        """
        Get statistics about changes in a file.

        Args:
            file_path: Path to the file (relative to repo root)

        Returns:
            Dict with 'additions', 'deletions', and 'changes' counts
        """
        rel_path = Path(file_path).relative_to(self.repo_path)
        result = self._run_git_command(
            ["diff", "--numstat", str(rel_path)], check=False
        )

        if not result.stdout.strip():
            return {"additions": 0, "deletions": 0, "changes": 0}

        parts = result.stdout.strip().split("\t")
        if len(parts) >= 2:
            additions = int(parts[0]) if parts[0] != "-" else 0
            deletions = int(parts[1]) if parts[1] != "-" else 0
            return {
                "additions": additions,
                "deletions": deletions,
                "changes": additions + deletions,
            }

        return {"additions": 0, "deletions": 0, "changes": 0}

    def is_file_ignored(self, file_path: Union[str, Path]) -> bool:
        """Check if a file is ignored by git."""
        result = self._run_git_command(["check-ignore", str(file_path)], check=False)
        return result.returncode == 0

    def stage_file(self, file_path: Union[str, Path]) -> None:
        """Stage a file for commit."""
        self._run_git_command(["add", str(file_path)])

    def stage_all(self) -> None:
        """Stage all changes."""
        self._run_git_command(["add", "-A"])

    def unstage_file(self, file_path: Union[str, Path]) -> None:
        """Unstage a file."""
        self._run_git_command(["reset", "HEAD", str(file_path)])

    def unstage_all(self) -> None:
        """Unstage all staged changes."""
        self._run_git_command(["reset", "HEAD"])

    def get_modified_files(self, since: Optional[str] = None) -> Set[Path]:
        """
        Get list of modified files.

        Args:
            since: Git reference to compare against (e.g., 'HEAD~1', 'main')
                  If None, compares working directory to HEAD

        Returns:
            Set of modified file paths
        """
        if since:
            result = self._run_git_command(["diff", "--name-only", since], check=False)
        else:
            result = self._run_git_command(["diff", "--name-only"], check=False)

        files = set()
        for line in result.stdout.strip().split("\n"):
            if line:
                files.add(self.repo_path / line)

        return files


if __name__ == "__main__":
    # Example usage
    detector = ChangeDetector()

    print("Detecting changes...\n")
    changes = detector.get_changes(include_diffs=False)

    print(f"Summary: {changes}\n")

    if changes.staged_changes:
        print("Staged changes:")
        for change in changes.staged_changes:
            print(f"  {change}")
        print()

    if changes.unstaged_changes:
        print("Unstaged changes:")
        for change in changes.unstaged_changes:
            stats = detector.get_diff_stats(change.path)
            print(f"  {change} (+{stats['additions']} -{stats['deletions']})")
        print()

    if changes.untracked_files:
        print("Untracked files:")
        for path in changes.untracked_files:
            print(f"  {path}")
        print()

    if not changes.has_changes:
        print("No changes detected.")
