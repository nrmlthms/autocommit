"""Error formatting and display utilities."""

import sys
from typing import Any, Optional, TextIO

from .exceptions import AutoCommitError


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

    @staticmethod
    def is_tty() -> bool:
        """Check if output is a TTY (terminal)."""
        return sys.stderr.isatty()

    @classmethod
    def disable_if_not_tty(cls) -> None:
        """Disable colors if not outputting to a terminal."""
        if not cls.is_tty():
            cls.RESET = ""
            cls.BOLD = ""
            cls.RED = ""
            cls.GREEN = ""
            cls.YELLOW = ""
            cls.BLUE = ""
            cls.MAGENTA = ""
            cls.CYAN = ""
            cls.GRAY = ""


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
        use_colors: Whether to use ANSI colors

    Returns:
        Formatted error message
    """
    if use_colors:
        Colors.disable_if_not_tty()
    else:
        Colors.disable_if_not_tty()
        Colors.RESET = ""
        Colors.BOLD = ""
        Colors.RED = ""
        Colors.YELLOW = ""
        Colors.CYAN = ""
        Colors.GRAY = ""

    lines = []

    # Error header
    if isinstance(error, AutoCommitError):
        error_type = error.__class__.__name__.replace("Error", "")
        lines.append(
            f"{Colors.BOLD}{Colors.RED}✗ {error_type} Error:{Colors.RESET} {error.message}"
        )

        # Show suggestion if available
        if show_suggestion and error.suggestion:
            lines.append("")
            lines.append(f"{Colors.CYAN}💡 Suggestion:{Colors.RESET}")
            # Indent suggestion lines
            for line in error.suggestion.split("\n"):
                lines.append(f"   {line}")

        # Show additional context for specific error types
        if hasattr(error, "stderr") and error.stderr:
            lines.append("")
            lines.append(f"{Colors.GRAY}Git output:{Colors.RESET}")
            lines.append(f"   {error.stderr}")

    else:
        # Generic error formatting
        lines.append(f"{Colors.BOLD}{Colors.RED}✗ Error:{Colors.RESET} {str(error)}")

    return "\n".join(lines)


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
        use_colors: Whether to use ANSI colors
        file: File to write to (default: sys.stderr)
    """
    output_file: TextIO = file if file is not None else sys.stderr

    formatted = format_error(error, show_suggestion, use_colors)
    print(formatted, file=output_file)


def print_warning(message: str, use_colors: bool = True) -> None:
    """
    Print a warning message.

    Args:
        message: Warning message
        use_colors: Whether to use ANSI colors
    """
    if use_colors:
        Colors.disable_if_not_tty()
    else:
        Colors.disable_if_not_tty()
        Colors.RESET = ""
        Colors.BOLD = ""
        Colors.YELLOW = ""

    print(
        f"{Colors.BOLD}{Colors.YELLOW}⚠ Warning:{Colors.RESET} {message}",
        file=sys.stderr,
    )


def print_success(message: str, use_colors: bool = True) -> None:
    """
    Print a success message.

    Args:
        message: Success message
        use_colors: Whether to use ANSI colors
    """
    if use_colors:
        Colors.disable_if_not_tty()
    else:
        Colors.disable_if_not_tty()
        Colors.RESET = ""
        Colors.BOLD = ""
        Colors.GREEN = ""

    print(f"{Colors.BOLD}{Colors.GREEN}✓{Colors.RESET} {message}")
