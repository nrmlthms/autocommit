"""Core AutoCommit functionality."""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import Config
from .detector import ChangeDetector, ChangeSet
from .errors import print_error, print_success, print_warning
from .exceptions import (
    AutoCommitError,
    CommitFailedError,
    GitStateError,
    NoChangesError,
    PushFailedError,
    ValidationError,
)
from .generator import LLMCommitMessageGenerator
from .git_state import GitStateDetector
from .prompts import (
    console,
    display_changes_summary,
    display_file_list,
    display_info,
    display_status,
    display_success,
    display_warning,
    prompt_commit_message_review,
)


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
        self.state_detector = GitStateDetector(self.repo_path)
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
            # Check repository state
            if verbose:
                display_status("Checking repository state...")

            repo_state = self.state_detector.get_state()

            # Handle unsafe states
            if not repo_state.is_safe_for_commit:
                raise GitStateError(
                    state=repo_state.state.value,
                    suggestion=repo_state.suggestion,
                )

            # Warn about detached HEAD but allow proceeding
            if repo_state.state.value == "detached":
                display_warning(
                    f"Working on detached HEAD at {repo_state.head_commit}"
                )
                if repo_state.suggestion and verbose:
                    console.print(f"\n{repo_state.suggestion}\n", style="dim")

            # Detect changes
            if self.config.show_progress:
                with console.status(
                    "[cyan]Detecting changes...[/cyan]", spinner="dots"
                ):
                    changeset = self.detector.get_changes(include_diffs=True)
            else:
                changeset = self.detector.get_changes(include_diffs=True)

            if not changeset.has_changes:
                if verbose:
                    display_warning("No changes detected. Nothing to commit.")
                else:
                    console.print("No changes detected. Nothing to commit.")
                return 0

            # Display changes
            self._display_changes(changeset, verbose)

            # Stage all changes
            if dry_run:
                console.print("\n[bold cyan][DRY RUN][/bold cyan] Would stage all changes")
            else:
                if self.config.show_progress:
                    with console.status(
                        "[cyan]Staging all changes...[/cyan]", spinner="dots"
                    ):
                        self.detector.stage_all()
                else:
                    self.detector.stage_all()

            # Generate or use provided commit message
            if message:
                commit_message = message
                use_interactive = False  # Skip prompt if message provided explicitly
            else:
                if verbose:
                    display_status("Generating commit message with LLM...")
                commit_message = self.message_generator.generate_from_changeset(
                    changeset, self.detector
                )
                use_interactive = self.config.interactive_mode and not dry_run

            # Interactive review (if enabled and message was auto-generated)
            if use_interactive:
                action, edited_message = prompt_commit_message_review(
                    commit_message,
                    allow_edit=True,
                )

                if action == "no":
                    console.print("[yellow]Commit cancelled by user.[/yellow]")
                    return 0
                elif action == "edit" and edited_message:
                    commit_message = edited_message
                    console.print()
                    display_success("Using edited message")
                # If action == "yes", just continue with original message

            if verbose or dry_run:
                if not use_interactive:  # Don't print again if already shown in prompt
                    console.print(f"\n[bold]Commit message:[/bold] {commit_message}")

            # Create backup branch if safe mode is enabled
            backup_branch = None
            if safe_mode and not dry_run:
                backup_branch = self._create_backup_branch()
                if verbose:
                    console.print()
                    display_success(f"Created backup branch: {backup_branch}")

            # Commit
            commit_sha = None
            if dry_run:
                console.print("[bold cyan][DRY RUN][/bold cyan] Would create commit")
            else:
                try:
                    if self.config.show_progress:
                        with console.status(
                            "[cyan]Creating commit...[/cyan]", spinner="dots"
                        ):
                            commit_sha = self._commit(commit_message)
                    else:
                        commit_sha = self._commit(commit_message)
                    display_success(f"Committed: {commit_message}")
                except subprocess.CalledProcessError as e:
                    raise CommitFailedError(
                        message=str(e),
                        stderr=e.stderr if e.stderr else None,
                    )

            # Push
            if push:
                if dry_run:
                    console.print("[bold cyan][DRY RUN][/bold cyan] Would push to remote")
                else:
                    # Try to push, rollback on failure
                    try:
                        if self.config.show_progress:
                            with console.status(
                                "[cyan]Pushing to remote...[/cyan]", spinner="dots"
                            ):
                                self._push()
                        else:
                            self._push()
                        display_success("Pushed to remote")

                        # Clean up backup branch on successful push
                        if backup_branch:
                            self._delete_backup_branch(backup_branch)
                            if verbose:
                                display_success(f"Cleaned up backup branch: {backup_branch}")

                    except subprocess.CalledProcessError as e:
                        # Push failed - rollback if we have a commit
                        if commit_sha:
                            display_warning("Push failed. Rolling back commit...")
                            self._rollback_commit(backup_branch)
                            display_success("Commit rolled back successfully")

                            if backup_branch:
                                display_success(f"Your changes are preserved in branch: {backup_branch}")

                        # Raise PushFailedError with context
                        raise PushFailedError(stderr=e.stderr if e.stderr else None)

            return 0

        except AutoCommitError as e:
            # Handle our custom exceptions with formatted output
            print_error(e, show_suggestion=True, use_colors=True)
            return 1
        except subprocess.CalledProcessError as e:
            # Handle unexpected git errors
            from .exceptions import GitError

            git_error = GitError(
                message=f"Git command failed: {e.cmd}",
                stderr=e.stderr if e.stderr else None,
                suggestion="Check the git output above for details.",
            )
            print_error(git_error, show_suggestion=True, use_colors=True)
            return 1
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.", file=sys.stderr)
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            # Handle unexpected errors
            print_error(e, show_suggestion=False, use_colors=True)
            if verbose:
                import traceback
                print("\nFull traceback:", file=sys.stderr)
                traceback.print_exc()
            return 1

    def _display_changes(self, changeset: ChangeSet, verbose: bool = False) -> None:
        """Display detected changes using rich formatting."""
        # Display summary
        display_changes_summary(
            staged=len(changeset.staged_changes),
            unstaged=len(changeset.unstaged_changes),
            untracked=len(changeset.untracked_files),
        )

        # Display file lists if verbose
        if verbose:
            if changeset.staged_changes:
                display_file_list(
                    [str(c.path.name) for c in changeset.staged_changes],
                    title="Staged Changes",
                    style="green",
                )

            if changeset.unstaged_changes:
                display_file_list(
                    [str(c.path.name) for c in changeset.unstaged_changes],
                    title="Unstaged Changes",
                    style="yellow",
                )

            if changeset.untracked_files:
                display_file_list(
                    [str(p.name) for p in changeset.untracked_files],
                    title="Untracked Files",
                    style="blue",
                )

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
            raise ValidationError(
                message="Commit message cannot be empty",
                field="commit_message",
            )

        # Strip leading/trailing whitespace
        message = message.strip()

        # Check length
        max_length = self.config.max_message_length
        if len(message) > max_length:
            raise ValidationError(
                message=f"Commit message too long ({len(message)} chars). Maximum is {max_length} characters.",
                field="commit_message",
            )

        # Remove or replace control characters (except newlines and tabs)
        # Control characters can cause display issues
        message = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', message)

        # Ensure no null bytes (can cause subprocess issues)
        if '\x00' in message:
            raise ValidationError(
                message="Commit message contains null bytes",
                field="commit_message",
            )

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
