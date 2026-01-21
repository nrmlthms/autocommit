"""Core AutoCommit functionality."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from .detector import ChangeDetector, ChangeSet
from .generator import LLMCommitMessageGenerator


class AutoCommit:
    """Main AutoCommit tool for automatic git operations."""

    def __init__(
        self,
        repo_path: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ):
        """
        Initialize AutoCommit.

        Args:
            repo_path: Path to git repository (default: current directory)
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.detector = ChangeDetector(self.repo_path)
        self.message_generator = LLMCommitMessageGenerator(api_key=api_key, model=model)

    def run(
        self,
        message: Optional[str] = None,
        push: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> int:
        """
        Run the auto-commit process.

        Args:
            message: Custom commit message (if None, auto-generate with LLM)
            push: Whether to push after commit
            dry_run: Show what would be done without actually doing it
            verbose: Show detailed output

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Detect changes
            if verbose:
                print("Detecting changes...")

            changeset = self.detector.get_changes(include_diffs=True)

            if not changeset.has_changes:
                print("No changes detected. Nothing to commit.")
                return 0

            # Display changes
            self._display_changes(changeset, verbose)

            # Stage all changes
            if dry_run:
                print("\n[DRY RUN] Would stage all changes")
            else:
                if verbose:
                    print("\nStaging all changes...")
                self.detector.stage_all()

            # Generate or use provided commit message
            if message:
                commit_message = message
            else:
                if verbose:
                    print("\nGenerating commit message with LLM...")
                commit_message = self.message_generator.generate_from_changeset(
                    changeset, self.detector
                )

            if verbose or dry_run:
                print(f"\nCommit message: {commit_message}")

            # Commit
            if dry_run:
                print("[DRY RUN] Would create commit")
            else:
                if verbose:
                    print("\nCreating commit...")
                self._commit(commit_message)
                print(f"✓ Committed: {commit_message}")

            # Push
            if push:
                if dry_run:
                    print("[DRY RUN] Would push to remote")
                else:
                    if verbose:
                        print("\nPushing to remote...")
                    self._push()
                    print("✓ Pushed to remote")

            return 0

        except subprocess.CalledProcessError as e:
            print(f"Git error: {e.stderr if e.stderr else str(e)}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    def _display_changes(self, changeset: ChangeSet, verbose: bool = False) -> None:
        """Display detected changes."""
        print(f"\nFound {changeset.total_changes} change(s):")

        if changeset.staged_changes and verbose:
            print("\nStaged changes:")
            for change in changeset.staged_changes:
                print(f"  {change.status.value} {change.path.name}")

        if changeset.unstaged_changes:
            print("\nUnstaged changes:")
            for change in changeset.unstaged_changes:
                print(f"  {change.status.value} {change.path.name}")

        if changeset.untracked_files:
            print("\nUntracked files:")
            for path in changeset.untracked_files:
                print(f"  ?? {path.name}")

    def _commit(self, message: str) -> None:
        """Create a git commit."""
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "commit", "-m", message],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stderr:
            print(result.stderr, end="")

    def _push(self) -> None:
        """Push commits to remote repository."""
        # First, check if we have a remote
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "remote"],
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            print("Warning: No remote repository configured. Skipping push.")
            return

        # Push to remote
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "push"],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stderr:
            print(result.stderr, end="")
