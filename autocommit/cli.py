#!/usr/bin/env python3
"""CLI entry point for AutoCommit."""

import argparse
import sys

from .config import Config
from .core import AutoCommit


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LazyCommit - Automatic git commit and push tool with LLM-generated messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lazycommit                    # Auto-detect changes, generate message, commit, and push
  lazycommit --no-push          # Commit without pushing
  lazycommit -m "Fix bug"       # Use custom commit message
  lazycommit --dry-run          # See what would be done
  lazycommit -v                 # Verbose output
  lazycommit --model gpt-4      # Use GPT-4 for message generation
  lazycommit --safe-mode        # Create backup branch and enable rollback on push failure

Environment Variables:
  OPENAI_API_KEY               # Required: Your OpenAI API key
  BASE_URL                     # Optional: Custom API endpoint (e.g., for OpenRouter)
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
        help="OpenAI model to use (default: from config or gpt-4o-mini)",
        type=str,
    )

    parser.add_argument(
        "--api-key",
        help="OpenAI API key (default: reads from OPENAI_API_KEY env var)",
        type=str,
    )

    parser.add_argument(
        "--safe-mode",
        help="Create backup branch before pushing and enable rollback on push failure",
        action="store_true",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config.load()
    except Exception as e:
        print(f"Warning: Failed to load config: {e}", file=sys.stderr)
        config = Config()

    # Warn if API key is passed via CLI (security risk)
    if args.api_key:
        print(
            "WARNING: Passing API key via --api-key exposes it in the process list.",
            file=sys.stderr,
        )
        print(
            "WARNING: For better security, use the OPENAI_API_KEY environment variable instead.",
            file=sys.stderr,
        )
        print(file=sys.stderr)

    try:
        # Create AutoCommit instance with config
        autocommit = AutoCommit(
            config=config,
            repo_path=args.path,
            api_key=args.api_key,
            model=args.model,
        )

        # Determine push and safe_mode, using config defaults if not specified
        push = not args.no_push if args.no_push else config.push_by_default
        safe_mode = args.safe_mode or config.safe_mode_by_default
        verbose = args.verbose or config.verbose_by_default

        # Run the tool
        return autocommit.run(
            message=args.message,
            push=push,
            dry_run=args.dry_run,
            verbose=verbose,
            safe_mode=safe_mode,
        )
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
