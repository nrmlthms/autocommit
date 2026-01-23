"""Git repository state detection and validation."""

import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from .exceptions import GitError


class GitState(Enum):
    """Possible git repository states."""

    NORMAL = "normal"
    MERGE_IN_PROGRESS = "merge"
    REBASE_IN_PROGRESS = "rebase"
    REBASE_INTERACTIVE = "rebase-i"
    REBASE_MERGE = "rebase-m"
    CHERRY_PICK_IN_PROGRESS = "cherry-pick"
    REVERT_IN_PROGRESS = "revert"
    BISECT_IN_PROGRESS = "bisect"
    DETACHED_HEAD = "detached"
    BARE_REPOSITORY = "bare"


@dataclass
class RepositoryState:
    """Represents the current state of a git repository."""

    state: GitState
    is_safe_for_commit: bool
    branch_name: Optional[str] = None
    head_commit: Optional[str] = None
    conflicted_files: list[str] = field(default_factory=list)
    suggestion: Optional[str] = None


class GitStateDetector:
    """Detect and validate git repository state."""

    def __init__(self, repo_path: Union[str, Path] = "."):
        """
        Initialize the git state detector.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path).resolve()

    def _run_git_command(
        self, args: list[str], check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command in the repository."""
        return subprocess.run(
            ["git", "-C", str(self.repo_path)] + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def _get_git_dir(self) -> Path:
        """Get the .git directory path."""
        result = self._run_git_command(["rev-parse", "--git-dir"], check=True)
        git_dir = result.stdout.strip()
        if git_dir.startswith("/"):
            return Path(git_dir)
        return self.repo_path / git_dir

    def _is_bare_repository(self) -> bool:
        """Check if the repository is bare."""
        result = self._run_git_command(["rev-parse", "--is-bare-repository"])
        return result.stdout.strip() == "true"

    def _is_detached_head(self) -> bool:
        """Check if HEAD is detached."""
        result = self._run_git_command(["symbolic-ref", "-q", "HEAD"])
        return result.returncode != 0

    def _get_current_branch(self) -> Optional[str]:
        """Get the current branch name."""
        result = self._run_git_command(["symbolic-ref", "--short", "HEAD"])
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def _get_head_commit(self) -> Optional[str]:
        """Get the current HEAD commit hash."""
        result = self._run_git_command(["rev-parse", "--short", "HEAD"])
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def _check_merge_in_progress(self, git_dir: Path) -> bool:
        """Check if a merge is in progress."""
        return (git_dir / "MERGE_HEAD").exists()

    def _check_rebase_in_progress(self, git_dir: Path) -> tuple[bool, Optional[str]]:
        """
        Check if a rebase is in progress.

        Returns:
            Tuple of (is_rebasing, rebase_type)
        """
        if (git_dir / "rebase-merge").exists():
            if (git_dir / "rebase-merge" / "interactive").exists():
                return True, "interactive"
            return True, "merge"
        elif (git_dir / "rebase-apply").exists():
            return True, "apply"
        return False, None

    def _check_cherry_pick_in_progress(self, git_dir: Path) -> bool:
        """Check if a cherry-pick is in progress."""
        return (git_dir / "CHERRY_PICK_HEAD").exists()

    def _check_revert_in_progress(self, git_dir: Path) -> bool:
        """Check if a revert is in progress."""
        return (git_dir / "REVERT_HEAD").exists()

    def _check_bisect_in_progress(self, git_dir: Path) -> bool:
        """Check if a bisect is in progress."""
        return (git_dir / "BISECT_LOG").exists()

    def _get_conflicted_files(self) -> list[str]:
        """Get list of files with merge conflicts."""
        result = self._run_git_command(["diff", "--name-only", "--diff-filter=U"])
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return [line.strip() for line in result.stdout.strip().split("\n") if line]

    def get_state(self) -> RepositoryState:
        """
        Detect the current state of the git repository.

        Returns:
            RepositoryState object describing the repository state

        Raises:
            GitError: If unable to determine repository state
        """
        try:
            # Check if bare repository
            if self._is_bare_repository():
                return RepositoryState(
                    state=GitState.BARE_REPOSITORY,
                    is_safe_for_commit=False,
                    suggestion="Cannot commit to bare repository. Clone it first.",
                )

            git_dir = self._get_git_dir()
            branch_name = self._get_current_branch()
            head_commit = self._get_head_commit()

            # Check for various in-progress operations
            if self._check_merge_in_progress(git_dir):
                conflicted_files = self._get_conflicted_files()
                if conflicted_files:
                    return RepositoryState(
                        state=GitState.MERGE_IN_PROGRESS,
                        is_safe_for_commit=False,
                        branch_name=branch_name,
                        head_commit=head_commit,
                        conflicted_files=conflicted_files,
                        suggestion=(
                            "Merge is in progress with conflicts. Resolve conflicts first:\n"
                            f"  • {len(conflicted_files)} file(s) have conflicts\n"
                            "  • Edit conflicted files and mark as resolved: git add <file>\n"
                            "  • Then complete merge: git commit\n"
                            "  • Or abort merge: git merge --abort"
                        ),
                    )
                else:
                    # Merge in progress but no conflicts - safe to commit
                    return RepositoryState(
                        state=GitState.MERGE_IN_PROGRESS,
                        is_safe_for_commit=True,
                        branch_name=branch_name,
                        head_commit=head_commit,
                        suggestion="Merge commit ready. All conflicts resolved.",
                    )

            is_rebasing, rebase_type = self._check_rebase_in_progress(git_dir)
            if is_rebasing:
                state_map = {
                    "interactive": GitState.REBASE_INTERACTIVE,
                    "merge": GitState.REBASE_MERGE,
                    "apply": GitState.REBASE_IN_PROGRESS,
                }
                return RepositoryState(
                    state=state_map.get(rebase_type or "", GitState.REBASE_IN_PROGRESS),
                    is_safe_for_commit=False,
                    branch_name=branch_name,
                    head_commit=head_commit,
                    suggestion=(
                        "Rebase is in progress. Complete it first:\n"
                        "  • Resolve any conflicts\n"
                        "  • Continue rebase: git rebase --continue\n"
                        "  • Or abort rebase: git rebase --abort"
                    ),
                )

            if self._check_cherry_pick_in_progress(git_dir):
                conflicted_files = self._get_conflicted_files()
                if conflicted_files:
                    return RepositoryState(
                        state=GitState.CHERRY_PICK_IN_PROGRESS,
                        is_safe_for_commit=False,
                        branch_name=branch_name,
                        head_commit=head_commit,
                        conflicted_files=conflicted_files,
                        suggestion=(
                            "Cherry-pick is in progress with conflicts:\n"
                            "  • Resolve conflicts in the affected files\n"
                            "  • Stage resolved files: git add <file>\n"
                            "  • Continue cherry-pick: git cherry-pick --continue\n"
                            "  • Or abort cherry-pick: git cherry-pick --abort"
                        ),
                    )

            if self._check_revert_in_progress(git_dir):
                return RepositoryState(
                    state=GitState.REVERT_IN_PROGRESS,
                    is_safe_for_commit=False,
                    branch_name=branch_name,
                    head_commit=head_commit,
                    suggestion=(
                        "Revert is in progress. Complete it first:\n"
                        "  • Resolve any conflicts\n"
                        "  • Continue revert: git revert --continue\n"
                        "  • Or abort revert: git revert --abort"
                    ),
                )

            if self._check_bisect_in_progress(git_dir):
                return RepositoryState(
                    state=GitState.BISECT_IN_PROGRESS,
                    is_safe_for_commit=False,
                    branch_name=branch_name,
                    head_commit=head_commit,
                    suggestion=(
                        "Bisect is in progress. Complete it first:\n"
                        "  • Mark current commit: git bisect good/bad\n"
                        "  • Or abort bisect: git bisect reset"
                    ),
                )

            # Check for detached HEAD (not during other operations)
            if self._is_detached_head():
                return RepositoryState(
                    state=GitState.DETACHED_HEAD,
                    is_safe_for_commit=True,  # Can commit but should warn
                    branch_name=None,
                    head_commit=head_commit,
                    suggestion=(
                        f"HEAD is detached at {head_commit}. Commits may be lost.\n"
                        "  • Create a branch to save your work: git checkout -b <branch-name>\n"
                        "  • Or return to a branch: git checkout <branch-name>"
                    ),
                )

            # Normal state
            return RepositoryState(
                state=GitState.NORMAL,
                is_safe_for_commit=True,
                branch_name=branch_name,
                head_commit=head_commit,
            )

        except subprocess.CalledProcessError as e:
            raise GitError(
                message="Failed to determine repository state",
                stderr=e.stderr if hasattr(e, "stderr") else None,
            )

    def check_state_safety(self) -> tuple[bool, Optional[str]]:
        """
        Check if the repository is in a safe state for auto-commit.

        Returns:
            Tuple of (is_safe, reason)
        """
        state = self.get_state()

        if not state.is_safe_for_commit:
            return False, state.suggestion

        # Warn about detached HEAD but allow commit
        if state.state == GitState.DETACHED_HEAD:
            return True, state.suggestion

        return True, None
