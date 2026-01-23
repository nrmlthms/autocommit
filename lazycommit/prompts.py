"""Interactive prompts and user input handling."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.text import Text

console = Console()
console_stderr = Console(stderr=True)


def get_editor() -> str:
    """
    Get the user's preferred editor.

    Returns:
        Editor command to use
    """
    # Try environment variables in order of preference
    for var in ["VISUAL", "EDITOR"]:
        editor = os.environ.get(var)
        if editor:
            return editor

    # Try common editors
    for editor in ["nano", "vim", "vi", "emacs", "code", "subl"]:
        result = subprocess.run(
            ["which", editor],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return editor

    # Fall back to nano if nothing else works
    return "nano"


def edit_in_editor(initial_text: str) -> Optional[str]:
    """
    Open an editor for the user to edit text.

    Args:
        initial_text: Initial text to populate the editor with

    Returns:
        Edited text, or None if editing was cancelled
    """
    editor = get_editor()

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
    ) as f:
        f.write(initial_text)
        temp_path = f.name

    try:
        # Open editor
        result = subprocess.run([editor, temp_path])

        if result.returncode != 0:
            console.print(
                "[yellow]⚠[/yellow] Editor exited with non-zero status",
                style="yellow",
            )
            return None

        # Read edited content
        with open(temp_path, "r") as f:
            edited_text = f.read().strip()

        return edited_text if edited_text else None

    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)


def prompt_commit_message_review(
    message: str,
    allow_edit: bool = True,
) -> tuple[Literal["yes", "no", "edit"], Optional[str]]:
    """
    Prompt user to review and approve/edit a commit message.

    Args:
        message: The commit message to review
        allow_edit: Whether to allow editing

    Returns:
        Tuple of (action, edited_message)
        - action: "yes" (accept), "no" (reject), or "edit" (edit message)
        - edited_message: The edited message if action is "edit", else None
    """
    # Display the commit message in a nice panel
    console.print()
    message_text = Text(message, style="bold cyan")
    panel = Panel(
        message_text,
        title="[bold yellow]📝 Generated Commit Message[/bold yellow]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)

    # Build prompt options
    if allow_edit:
        options = "[bold green]y[/bold green]es / [bold red]n[/bold red]o / [bold cyan]e[/bold cyan]dit"
        valid_responses = ["y", "yes", "n", "no", "e", "edit"]
    else:
        options = "[bold green]y[/bold green]es / [bold red]n[/bold red]o"
        valid_responses = ["y", "yes", "n", "no"]

    # Prompt for response
    console.print()
    response = Prompt.ask(
        f"Use this message? ({options})",
        choices=valid_responses,
        default="y",
        show_choices=False,
    ).lower()

    # Handle response
    if response in ["y", "yes"]:
        return "yes", None
    elif response in ["n", "no"]:
        return "no", None
    elif response in ["e", "edit"]:
        console.print()
        console.print("[cyan]Opening editor...[/cyan]")
        edited = edit_in_editor(message)
        if edited:
            return "edit", edited
        else:
            console.print("[yellow]⚠[/yellow] No changes made", style="yellow")
            return "no", None

    # Should never reach here due to prompt validation
    return "no", None


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user to confirm an action.

    Args:
        message: The confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if confirmed, False otherwise
    """
    return Confirm.ask(message, default=default)


def display_changes_summary(
    staged: int = 0,
    unstaged: int = 0,
    untracked: int = 0,
) -> None:
    """
    Display a summary of changes in a formatted way.

    Args:
        staged: Number of staged changes
        unstaged: Number of unstaged changes
        untracked: Number of untracked files
    """
    console.print()

    # Build summary text
    parts = []
    if staged > 0:
        parts.append(f"[green]{staged} staged[/green]")
    if unstaged > 0:
        parts.append(f"[yellow]{unstaged} unstaged[/yellow]")
    if untracked > 0:
        parts.append(f"[blue]{untracked} untracked[/blue]")

    summary = " • ".join(parts) if parts else "[dim]no changes[/dim]"

    panel = Panel(
        summary,
        title="[bold]📊 Changes Summary[/bold]",
        border_style="blue",
    )
    console.print(panel)


def display_file_list(
    files: list[str],
    title: str = "Files",
    style: str = "cyan",
    max_display: int = 10,
) -> None:
    """
    Display a list of files in a formatted way.

    Args:
        files: List of file paths
        title: Title for the display
        style: Color style to use
        max_display: Maximum number of files to display
    """
    if not files:
        return

    console.print()
    console.print(f"[bold {style}]{title}:[/bold {style}]")

    display_files = files[:max_display]
    for file in display_files:
        console.print(f"  [dim]•[/dim] {file}", style=style)

    if len(files) > max_display:
        remaining = len(files) - max_display
        console.print(f"  [dim]... and {remaining} more[/dim]")


def display_error(message: str, suggestion: Optional[str] = None) -> None:
    """
    Display an error message with optional suggestion.

    Args:
        message: Error message
        suggestion: Optional suggestion for fixing the error
    """
    console_stderr.print()

    # Format error message
    error_text = f"[bold red]✗ Error:[/bold red] {message}"

    if suggestion:
        error_text += f"\n\n[bold cyan]💡 Suggestion:[/bold cyan]\n{suggestion}"

    panel = Panel(
        error_text,
        border_style="red",
        padding=(1, 2),
    )
    console_stderr.print(panel, style="red")


def display_warning(message: str) -> None:
    """
    Display a warning message.

    Args:
        message: Warning message
    """
    console_stderr.print(f"[bold yellow]⚠[/bold yellow]  {message}", style="yellow")


def display_success(message: str) -> None:
    """
    Display a success message.

    Args:
        message: Success message
    """
    console.print(f"[bold green]✓[/bold green]  {message}", style="green")


def display_info(message: str) -> None:
    """
    Display an informational message.

    Args:
        message: Info message
    """
    console.print(f"[cyan]ℹ[/cyan]  {message}", style="cyan")


def display_diff(diff_text: str, max_lines: int = 20) -> None:
    """
    Display a git diff with syntax highlighting.

    Args:
        diff_text: The diff text
        max_lines: Maximum number of lines to display
    """
    if not diff_text:
        return

    console.print()

    # Split into lines and truncate if needed
    lines = diff_text.split("\n")
    if len(lines) > max_lines:
        display_lines = lines[:max_lines]
        display_text = "\n".join(display_lines)
        truncated = True
    else:
        display_text = diff_text
        truncated = False

    # Use syntax highlighting for diff
    syntax = Syntax(
        display_text,
        "diff",
        theme="monokai",
        line_numbers=False,
        word_wrap=True,
    )

    panel = Panel(
        syntax,
        title="[bold]📄 Diff Preview[/bold]",
        border_style="blue",
    )
    console.print(panel)

    if truncated:
        console.print(f"[dim]... {len(lines) - max_lines} more lines truncated[/dim]")


def display_status(message: str) -> None:
    """
    Display a status message (for ongoing operations).

    Args:
        message: Status message
    """
    console.print(f"[dim]→[/dim] {message}", style="dim")


def print_separator(char: str = "─", style: str = "dim") -> None:
    """
    Print a horizontal separator line.

    Args:
        char: Character to use for the line
        style: Style to apply
    """
    width = console.width
    console.print(char * width, style=style)
