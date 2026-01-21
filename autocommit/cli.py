#!/usr/bin/env python3
"""CLI entry point for AutoCommit."""

import argparse
import sys

from .core import AutoCommit


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AutoCommit - Automatic git commit and push tool with LLM-generated messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  autocommit                    # Auto-detect changes, generate message, commit, and push
  autocommit --no-push          # Commit without pushing
  autocommit -m "Fix bug"       # Use custom commit message
  autocommit --dry-run          # See what would be done
  autocommit -v                 # Verbose output
  autocommit --model gpt-4      # Use GPT-4 for message generation

Environment Variables:
  OPENAI_API_KEY               # Required: Your OpenAI API key
        """,
    )

    parser.add_argument(
        "-m",
        "--message",
        help="Custom commit message (auto-generated with LLM if not provided)",
        type=str,
    )

    parser.add_argument(
        "--no-push",
        help="Don't push after commit",
        action="store_true",
    )

    parser.add_argument(
        "--dry-run",
        help="Show what would be done without actually doing it",
        action="store_true",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="Show detailed output",
        action="store_true",
    )

    parser.add_argument(
        "--path",
        help="Path to git repository (default: current directory)",
        type=str,
    )

    parser.add_argument(
        "--model",
        help="OpenAI model to use (default: gpt-4o-mini)",
        type=str,
        default="gpt-4o-mini",
    )

    parser.add_argument(
        "--api-key",
        help="OpenAI API key (default: reads from OPENAI_API_KEY env var)",
        type=str,
    )

    args = parser.parse_args()

    try:
        # Create AutoCommit instance
        autocommit = AutoCommit(
            repo_path=args.path,
            api_key=args.api_key,
            model=args.model,
        )

        # Run the tool
        return autocommit.run(
            message=args.message,
            push=not args.no_push,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
