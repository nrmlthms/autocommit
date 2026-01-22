"""Core AutoCommit functionality."""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import Config
from .detector import ChangeDetector, ChangeSet
from .generator import LLMCommitMessageGenerator


class AutoCommit:
    """Main AutoCommit tool for automatic git operations."""

    def __init__(
        self,
        config: Optional[Config] = None,
        repo_path: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize AutoCommit.

        Args:
            config: Config object (if None, loads default config)
            repo_path: Path to git repository (default: current directory)
            api_key: OpenAI API key (overrides config if provided)
            model: OpenAI model to use (overrides config if provided)
        """
        # Load config if not provided
        if config is None:
            config = Config.load()

        self.config = config

        # Override repo path
        if repo_path:
            self.repo_path = Path(repo_path)
        elif config.default_repo_path:
            self.repo_path = Path(config.default_repo_path)
        else:
            self.repo_path = Path.cwd()

        self.detector = ChangeDetector(self.repo_path)
        self.message_generator = LLMCommitMessageGenerator(
            config=config, api_key=api_key, model=model
        )

    def run(
        self,
        message: Optional[str] = None,
        push: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
        safe_mode: bool = False,
    ) -> int:
        """
        Run the auto-commit process.

        Args:
            message: Custom commit message (if None, auto-generate with LLM)
            push: Whether to push after commit
            dry_run: Show what would be done without actually doing it
            verbose: Show detailed output
            safe_mode: Create backup branch and enable rollback on push failure

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

            # Create backup branch if safe mode is enabled
            backup_branch = None
            if safe_mode and not dry_run:
                backup_branch = self._create_backup_branch()
                if verbose:
                    print(f"\n✓ Created backup branch: {backup_branch}")

            # Commit
            commit_sha = None
            if dry_run:
                print("[DRY RUN] Would create commit")
            else:
                if verbose:
                    print("\nCreating commit...")
                commit_sha = self._commit(commit_message)
                print(f"✓ Committed: {commit_message}")

            # Push
            if push:
                if dry_run:
                    print("[DRY RUN] Would push to remote")
                else:
                    if verbose:
                        print("\nPushing to remote...")

                    # Try to push, rollback on failure if not in safe mode or if safe mode
                    try:
                        self._push()
                        print("✓ Pushed to remote")

                        # Clean up backup branch on successful push
                        if backup_branch:
                            self._delete_backup_branch(backup_branch)
                            if verbose:
                                print(f"✓ Cleaned up backup branch: {backup_branch}")

                    except subprocess.CalledProcessError as e:
                        # Push failed - rollback if we have a commit
                        if commit_sha:
                            print("\n✗ Push failed. Rolling back commit...", file=sys.stderr)
                            self._rollback_commit(backup_branch)
                            print("✓ Commit rolled back successfully", file=sys.stderr)

                            if backup_branch:
                                print(f"✓ Your changes are preserved in branch: {backup_branch}", file=sys.stderr)
                        raise

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

    def _validate_commit_message(self, message: str) -> str:
        """
        Validate and sanitize commit message.

        Args:
            message: The commit message to validate

        Returns:
            Sanitized commit message

        Raises:
            ValueError: If message is invalid
        """
        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty")

        # Strip leading/trailing whitespace
        message = message.strip()

        # Check length
        max_length = self.config.max_message_length
        if len(message) > max_length:
            raise ValueError(
                f"Commit message too long ({len(message)} chars). Maximum is {max_length} characters."
            )

        # Remove or replace control characters (except newlines and tabs)
        # Control characters can cause display issues
        message = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', message)

        # Ensure no null bytes (can cause subprocess issues)
        if '\x00' in message:
            raise ValueError("Commit message contains null bytes")

        return message

    def _commit(self, message: str) -> str:
        """
        Create a git commit.

        Returns:
            The commit SHA
        """
        # Validate and sanitize the commit message
        sanitized_message = self._validate_commit_message(message)

        # Note: Using subprocess.run with a list of args (not shell=True) is safe
        # from shell injection - args are passed directly to git without shell interpretation
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "commit", "-m", sanitized_message],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stderr:
            print(result.stderr, end="")

        # Get the commit SHA
        sha_result = subprocess.run(
            ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return sha_result.stdout.strip()

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

    def _create_backup_branch(self) -> str:
        """
        Create a backup branch before making changes.

        Returns:
            The name of the backup branch
        """
        from datetime import datetime

        # Generate backup branch name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_branch = f"autocommit-backup-{timestamp}"

        # Create the backup branch at current HEAD
        subprocess.run(
            ["git", "-C", str(self.repo_path), "branch", backup_branch],
            capture_output=True,
            text=True,
            check=True,
        )

        return backup_branch

    def _rollback_commit(self, backup_branch: Optional[str] = None) -> None:
        """
        Rollback the last commit.

        Args:
            backup_branch: Optional backup branch to restore from
        """
        if backup_branch:
            # Reset to the backup branch (which points to the pre-commit state)
            subprocess.run(
                ["git", "-C", str(self.repo_path), "reset", "--hard", backup_branch],
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            # No backup branch, just reset the last commit (soft reset to preserve changes)
            subprocess.run(
                ["git", "-C", str(self.repo_path), "reset", "--soft", "HEAD~1"],
                capture_output=True,
                text=True,
                check=True,
            )

    def _delete_backup_branch(self, backup_branch: str) -> None:
        """
        Delete a backup branch.

        Args:
            backup_branch: The name of the backup branch to delete
        """
        subprocess.run(
            ["git", "-C", str(self.repo_path), "branch", "-D", backup_branch],
            capture_output=True,
            text=True,
            check=True,
        )
