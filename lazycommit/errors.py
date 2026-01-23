"""Error formatting and display utilities using Rich."""

import sys
from typing import Optional, TextIO

from rich.console import Console

from .exceptions import AutoCommitError

# Create console instances for different outputs
console_stderr = Console(stderr=True)
console_stdout = Console()


def format_error(
    error: Exception,
    show_suggestion: bool = True,
    use_colors: bool = True,
) -> str:
    """
    Format an error message with optional colors and suggestions.

    Args:
        error: The exception to format
        show_suggestion: Whether to show actionable suggestions
        use_colors: Whether to use colors

    Returns:
        Formatted error message
    """
    # Create a temporary console for rendering to string
    temp_console = Console(force_terminal=use_colors, width=80)

    with temp_console.capture() as capture:
        if isinstance(error, AutoCommitError):
            error_type = error.__class__.__name__.replace("Error", "")

            # Build error message
            parts = []
            parts.append(f"[bold red]✗ {error_type} Error:[/bold red] {error.message}")

            # Show suggestion if available
            if show_suggestion and error.suggestion:
                parts.append("")
                parts.append("[bold cyan]💡 Suggestion:[/bold cyan]")
                for line in error.suggestion.split("\n"):
                    parts.append(f"   {line}")

            # Show additional context for specific error types
            if hasattr(error, "stderr") and error.stderr:
                parts.append("")
                parts.append("[dim]Git output:[/dim]")
                parts.append(f"   {error.stderr}")

            temp_console.print("\n".join(parts))
        else:
            # Generic error formatting
            temp_console.print(f"[bold red]✗ Error:[/bold red] {str(error)}")

    return capture.get().rstrip()


def print_error(
    error: Exception,
    show_suggestion: bool = True,
    use_colors: bool = True,
    file: Optional[TextIO] = None,
) -> None:
    """
    Print a formatted error message to stderr.

    Args:
        error: The exception to print
        show_suggestion: Whether to show actionable suggestions
        use_colors: Whether to use colors
        file: File to write to (default: sys.stderr)
    """
    if file is not None:
        # If specific file provided, use string formatting
        formatted = format_error(error, show_suggestion, use_colors)
        print(formatted, file=file)
    else:
        # Use rich console for stderr
        if isinstance(error, AutoCommitError):
            error_type = error.__class__.__name__.replace("Error", "")

            # Build error message
            parts = []
            parts.append(f"[bold red]✗ {error_type} Error:[/bold red] {error.message}")

            # Show suggestion if available
            if show_suggestion and error.suggestion:
                parts.append("")
                parts.append("[bold cyan]💡 Suggestion:[/bold cyan]")
                for line in error.suggestion.split("\n"):
                    parts.append(f"   {line}")

            # Show additional context for specific error types
            if hasattr(error, "stderr") and error.stderr:
                parts.append("")
                parts.append("[dim]Git output:[/dim]")
                parts.append(f"   {error.stderr}")

            console_stderr.print("\n".join(parts))
        else:
            # Generic error formatting
            console_stderr.print(f"[bold red]✗ Error:[/bold red] {str(error)}")


def print_warning(message: str, use_colors: bool = True) -> None:
    """
    Print a warning message.

    Args:
        message: Warning message
        use_colors: Whether to use colors
    """
    console_stderr.print(
        f"[bold yellow]⚠[/bold yellow]  {message}",
        style="yellow" if use_colors else None,
    )


def print_success(message: str, use_colors: bool = True) -> None:
    """
    Print a success message.

    Args:
        message: Success message
        use_colors: Whether to use colors
    """
    console_stdout.print(
        f"[bold green]✓[/bold green]  {message}",
        style="green" if use_colors else None,
    )


# Legacy compatibility for Colors class (for tests)
class Colors:
    """
    Compatibility class for existing tests.

    Note: This is kept for backward compatibility but all new code
    should use rich directly via the prompts module.
    """

    RESET = ""
    BOLD = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    GRAY = ""

    @staticmethod
    def is_tty() -> bool:
        """Check if output is a TTY (terminal)."""
        return sys.stderr.isatty()

    @classmethod
    def disable_if_not_tty(cls) -> None:
        """No-op for compatibility."""
        pass
