#!/usr/bin/env python3
"""CLI entry point for LazyCommit."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Config
from .core import AutoCommit

# Create Typer app
app = typer.Typer(
    name="lazycommit",
    help="Automatic git commit and push tool with LLM-generated messages",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command(name="commit")
def commit_cmd(
    message: Optional[str] = typer.Option(
        None,
        "--message",
        "-m",
        help="Custom commit message (auto-generated with LLM if not provided)",
    ),
    no_push: bool = typer.Option(
        False,
        "--no-push",
        help="Don't push after commit",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without actually doing it",
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Preview changes and generated message without committing",
    ),
    amend: bool = typer.Option(
        False,
        "--amend",
        help="Amend the last commit instead of creating a new one",
    ),
    scope: Optional[str] = typer.Option(
        None,
        "--scope",
        "-s",
        help="Scope for conventional commit (e.g., 'auth' for feat(auth): ...)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Path to git repository (default: current directory)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="OpenAI model to use (default: from config or gpt-4o-mini)",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="OpenAI API key (default: reads from OPENAI_API_KEY env var)",
    ),
    safe_mode: bool = typer.Option(
        False,
        "--safe-mode",
        help="Create backup branch before pushing and enable rollback on push failure",
    ),
) -> None:
    """
    Auto-detect changes, generate commit message, and push to remote.

    This is the main functionality of LazyCommit - automatically staging all changes,
    generating an appropriate commit message using an LLM, and optionally pushing to the remote.

    Examples:
        lazycommit commit                    # Auto-detect, commit, and push
        lazycommit commit --no-push          # Commit without pushing
        lazycommit commit -m "Fix bug"       # Use custom commit message
        lazycommit commit --dry-run          # See what would be done
        lazycommit commit --preview          # Preview changes without committing
        lazycommit commit --amend            # Amend the last commit
        lazycommit commit --scope auth       # Add scope: feat(auth): ...
        lazycommit commit -v                 # Verbose output
        lazycommit commit --safe-mode        # Create backup branch
    """
    # Load configuration
    try:
        config = Config.load()
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load config: {e}[/yellow]")
        config = Config()

    # Warn if API key is passed via CLI (security risk)
    if api_key:
        console.print(
            "[bold yellow]⚠ WARNING:[/bold yellow] Passing API key via --api-key exposes it in the process list.",
            style="yellow",
        )
        console.print(
            "For better security, use the OPENAI_API_KEY environment variable instead.\n",
            style="yellow",
        )

    try:
        # Create AutoCommit instance with config
        autocommit = AutoCommit(
            config=config,
            repo_path=path,
            api_key=api_key,
            model=model,
        )

        # Determine push and safe_mode, using config defaults if not specified
        push = not no_push if no_push else config.push_by_default
        safe_mode_enabled = safe_mode or config.safe_mode_by_default
        verbose_enabled = verbose or config.verbose_by_default

        # Run the tool
        exit_code = autocommit.run(
            message=message,
            push=push,
            dry_run=dry_run,
            preview=preview,
            amend=amend,
            scope=scope,
            verbose=verbose_enabled,
            safe_mode=safe_mode_enabled,
        )
        raise typer.Exit(code=exit_code)
    except ValueError as e:
        console.print(f"[bold red]Configuration error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)


@app.command(name="config")
def config_cmd(
    show: bool = typer.Option(
        False,
        "--show",
        "-s",
        help="Show current configuration",
    ),
    edit: bool = typer.Option(
        False,
        "--edit",
        "-e",
        help="Edit configuration file in default editor",
    ),
    get: Optional[str] = typer.Option(
        None,
        "--get",
        help="Get value of a specific config key",
    ),
    set_key: Optional[str] = typer.Option(
        None,
        "--set",
        help="Set a config key (use with --value)",
    ),
    value: Optional[str] = typer.Option(
        None,
        "--value",
        help="Value to set (use with --set)",
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Reset configuration to defaults",
    ),
) -> None:
    """
    Manage LazyCommit configuration.

    The configuration file is located at ~/.lazycommitrc and uses JSON format.

    Examples:
        lazycommit config --show              # Show current config
        lazycommit config --edit              # Edit config file
        lazycommit config --get model         # Get specific value
        lazycommit config --set model --value gpt-4  # Set specific value
        lazycommit config --reset             # Reset to defaults
    """
    config_file = Path.home() / ".lazycommitrc"

    # Show current config
    if show or (not edit and not get and not set_key and not reset):
        try:
            config = Config.load()

            # Create a table to display config
            table = Table(title="Current Configuration", show_header=True)
            table.add_column("Setting", style="cyan", no_wrap=True)
            table.add_column("Value", style="green")

            # Add config values
            config_dict = {
                "model": config.model,
                "temperature": str(config.temperature),
                "max_tokens": str(config.max_tokens),
                "max_message_length": str(config.max_message_length),
                "push_by_default": str(config.push_by_default),
                "safe_mode_by_default": str(config.safe_mode_by_default),
                "interactive_mode": str(config.interactive_mode),
                "show_progress": str(config.show_progress),
                "cache_enabled": str(config.cache_enabled),
                "offline_mode": str(config.offline_mode),
            }

            for key, val in config_dict.items():
                table.add_row(key, val)

            console.print()
            console.print(table)
            console.print()
            console.print(f"[dim]Config file: {config_file}[/dim]")

        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            raise typer.Exit(code=1)

    # Edit config file
    elif edit:
        # Create default config if doesn't exist
        if not config_file.exists():
            default_config = Config()
            default_config_dict: dict[str, str | int | float | bool] = {
                "model": default_config.model,
                "temperature": default_config.temperature,
                "max_tokens": default_config.max_tokens,
                "push_by_default": default_config.push_by_default,
            }
            with open(config_file, "w") as f:
                json.dump(default_config_dict, f, indent=2)

        # Open in editor
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
        try:
            subprocess.run([editor, str(config_file)], check=True)
            console.print(f"[green]✓[/green] Configuration updated: {config_file}")
        except subprocess.CalledProcessError:
            console.print(f"[red]Error opening editor: {editor}[/red]")
            raise typer.Exit(code=1)

    # Get specific value
    elif get:
        try:
            config = Config.load()
            if hasattr(config, get):
                value = getattr(config, get)
                console.print(f"{get} = [green]{value}[/green]")
            else:
                console.print(f"[red]Unknown config key: {get}[/red]")
                raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

    # Set specific value
    elif set_key:
        if not value:
            console.print("[red]Error: --value is required when using --set[/red]")
            raise typer.Exit(code=1)

        try:
            # Load existing config or create new dict
            set_config_dict: dict[str, str | int | float | bool | None] = {}
            if config_file.exists():
                with open(config_file, "r") as f:
                    set_config_dict = json.load(f)

            # Try to parse value as appropriate type
            parsed_value: str | int | float | bool
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value  # Keep as string if not valid JSON

            set_config_dict[set_key] = parsed_value

            # Save config
            with open(config_file, "w") as f:
                json.dump(set_config_dict, f, indent=2)

            console.print(
                f"[green]✓[/green] Set {set_key} = [green]{parsed_value}[/green]"
            )

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

    # Reset to defaults
    elif reset:
        if config_file.exists():
            config_file.unlink()
            console.print("[green]✓[/green] Configuration reset to defaults")
        else:
            console.print("[yellow]No config file to reset[/yellow]")


@app.command(name="stats")
def stats_cmd(
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Path to git repository (default: current directory)",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of recent commits to analyze",
    ),
) -> None:
    """
    Show commit statistics for the repository.

    Displays information about recent commits, including author, date, and message.

    Examples:
        lazycommit stats              # Show stats for last 10 commits
        lazycommit stats -n 20        # Show stats for last 20 commits
        lazycommit stats --path /repo # Show stats for specific repo
    """
    repo_path = Path(path) if path else Path.cwd()

    try:
        # Get commit log
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "log",
                f"-{limit}",
                "--pretty=format:%h|%an|%ar|%s",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout:
            console.print("[yellow]No commits found[/yellow]")
            return

        # Parse commits
        commits = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    }
                )

        # Create table
        table = Table(title=f"Recent Commits ({len(commits)} shown)", show_header=True)
        table.add_column("Hash", style="cyan", no_wrap=True)
        table.add_column("Author", style="green")
        table.add_column("Date", style="blue")
        table.add_column("Message", style="white")

        for commit in commits:
            # Truncate long messages
            message = commit["message"]
            if len(message) > 60:
                message = message[:57] + "..."

            table.add_row(
                commit["hash"],
                commit["author"],
                commit["date"],
                message,
            )

        console.print()
        console.print(table)
        console.print()

        # Get repository stats
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-list", "--all", "--count"],
            capture_output=True,
            text=True,
            check=True,
        )
        total_commits = result.stdout.strip()

        result = subprocess.run(
            ["git", "-C", str(repo_path), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip() or "detached HEAD"

        stats_panel = Panel(
            f"[cyan]Repository:[/cyan] {repo_path}\n"
            f"[cyan]Branch:[/cyan] {current_branch}\n"
            f"[cyan]Total commits:[/cyan] {total_commits}",
            title="Repository Stats",
            border_style="green",
        )
        console.print(stats_panel)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error: {e}[/red]")
        if e.stderr:
            console.print(f"[dim]{e.stderr}[/dim]")
        raise typer.Exit(code=1)


@app.command(name="undo")
def undo_cmd(
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Path to git repository (default: current directory)",
    ),
    hard: bool = typer.Option(
        False,
        "--hard",
        help="Hard reset (discard changes). Default is soft reset (keep changes)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Undo the last commit.

    By default, performs a soft reset keeping your changes staged.
    Use --hard to discard all changes from the last commit.

    Examples:
        lazycommit undo              # Undo last commit (keep changes)
        lazycommit undo --hard       # Undo last commit (discard changes)
        lazycommit undo -f           # Skip confirmation
    """
    repo_path = Path(path) if path else Path.cwd()

    try:
        # Get last commit info
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "log",
                "-1",
                "--pretty=format:%h - %s",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        last_commit = result.stdout.strip()

        if not last_commit:
            console.print("[yellow]No commits to undo[/yellow]")
            return

        # Show what will be undone
        reset_type = "hard" if hard else "soft"
        warning_panel = Panel(
            f"[bold]Last commit:[/bold] {last_commit}\n"
            f"[bold]Reset type:[/bold] {reset_type}\n\n"
            + (
                "[bold red]⚠ Warning:[/bold red] --hard will discard all changes from this commit!"
                if hard
                else "[green]Changes will be kept staged[/green]"
            ),
            title="Undo Last Commit",
            border_style="red" if hard else "yellow",
        )
        console.print()
        console.print(warning_panel)
        console.print()

        # Confirm unless --force
        if not force:
            confirm = typer.confirm("Do you want to proceed?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Perform reset
        reset_flag = "--hard" if hard else "--soft"
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "reset",
                reset_flag,
                "HEAD~1",
            ],
            check=True,
        )

        console.print("[green]✓[/green] Successfully undone last commit")
        if not hard:
            console.print(
                "[dim]Changes are still staged. Use 'git status' to see them.[/dim]"
            )

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error: {e}[/red]")
        if e.stderr:
            console.print(f"[dim]{e.stderr}[/dim]")
        raise typer.Exit(code=1)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
