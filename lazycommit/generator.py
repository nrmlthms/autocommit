"""Commit message generation using LLM."""

import os
import subprocess
import sys
from typing import Any, Callable, List, Optional

from openai import OpenAI
from rich.console import Console

from .cache import CommitMessageCache
from .config import Config
from .detector import ChangeDetector, ChangeSet
from .exceptions import APIError, ConfigurationError
from .retry import retry_on_api_error

console = Console()


class LLMCommitMessageGenerator:
    """Generate commit messages using LLM via OpenAI client."""

    def __init__(
        self,
        config: Optional[Config] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the LLM commit message generator.

        Args:
            config: Config object (if None, loads default config)
            api_key: OpenAI API key (overrides config if provided)
            model: OpenAI model to use (overrides config if provided)
        """
        # Load config if not provided
        if config is None:
            config = Config.load()

        self.config = config

        # Override config with explicit parameters
        self.api_key = api_key or config.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ConfigurationError(
                message="API key not found",
                config_key="api_key",
            )

        # Initialize OpenAI client with optional base_url for OpenRouter support
        if config.base_url:
            self.client = OpenAI(api_key=self.api_key, base_url=config.base_url)
        else:
            self.client = OpenAI(api_key=self.api_key)

        self.model = model or config.model

        # Initialize cache if enabled
        self.cache: Optional[CommitMessageCache] = None
        if config.cache_enabled:
            self.cache = CommitMessageCache(
                max_age_days=config.cache_max_age_days,
                max_entries=config.cache_max_entries,
            )

        # Validate parameters
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate configuration parameters.

        Raises:
            ValueError: If parameters are out of bounds
        """
        # Validate temperature (0.0 to 2.0 for most OpenAI models)
        if not 0.0 <= self.config.temperature <= 2.0:
            from .exceptions import ValidationError

            raise ValidationError(
                message=f"Temperature must be between 0.0 and 2.0, got {self.config.temperature}",
                field="temperature",
            )

        # Validate max_tokens (must be positive, typical range 1-4096)
        if self.config.max_tokens <= 0:
            from .exceptions import ValidationError

            raise ValidationError(
                message=f"max_tokens must be positive, got {self.config.max_tokens}",
                field="max_tokens",
            )

        if self.config.max_tokens > 4096:
            from .errors import print_warning

            print_warning(
                f"max_tokens={self.config.max_tokens} is unusually high. "
                "This may result in high API costs."
            )

        # Validate max_message_length
        if self.config.max_message_length <= 0:
            from .exceptions import ValidationError

            raise ValidationError(
                message=f"max_message_length must be positive, got {self.config.max_message_length}",
                field="max_message_length",
            )

    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for a given text.

        Uses a rough approximation: ~4 characters per token.
        For more accurate counting, consider using tiktoken library.

        Args:
            text: Input text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        # This is conservative (overestimates slightly)
        return len(text) // 4 + 1

    def generate_from_changeset(
        self, changeset: ChangeSet, detector: ChangeDetector, learn_style: bool = False
    ) -> str:
        """
        Generate a commit message using LLM based on the changeset.

        Args:
            changeset: The detected changes
            detector: ChangeDetector instance for getting diffs
            learn_style: Whether to analyze recent commits to learn user's style

        Returns:
            Generated commit message
        """
        if not changeset.has_changes:
            return "No changes to commit"

        # Check cache first
        if self.cache:
            cached_message = self.cache.get(changeset)
            if cached_message:
                return cached_message

        # If offline mode, use fallback
        if self.config.offline_mode:
            from .errors import print_warning

            print_warning("Offline mode: Using fallback commit message")
            return self._fallback_message(changeset)

        # Build context for LLM
        context = self._build_context(changeset, detector)

        # Analyze commit history to learn user's style
        style_context = ""
        if learn_style:
            history = self.get_commit_history(str(detector.repo_path))
            style_context = self.analyze_commit_style(history)

        # Estimate token count before API call
        system_message = """You are an expert at writing clear, professional commit messages following the Conventional Commits specification.

Your task is to analyze CURRENT git changes (not commit history) and create ONE commit message that is:
- Clear and descriptive
- Follows best practices
- Easy to understand at a glance

CRITICAL: You are writing ONE commit message for the CURRENT uncommitted changes only. Do NOT try to summarize multiple commits or reference past commits.

RULES:
1. Format: <type>(<scope>): <description>
   - type: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert
   - scope: optional, use when changes affect specific component/module
   - description: imperative mood, lowercase, no period at end

2. Subject line (first line):
   - Maximum 72 characters (ideally 50)
   - Explain WHAT changed, not HOW
   - Use imperative mood: "add" not "added" or "adds"
   - Be specific but concise

3. Type selection guide:
   - feat: New feature or capability for the user
   - fix: Bug fix that resolves an issue
   - docs: Documentation changes only
   - style: Code style/formatting (no logic change)
   - refactor: Code restructuring (no behavior change)
   - perf: Performance improvements
   - test: Adding or updating tests
   - chore: Maintenance tasks, dependencies, config
   - ci: CI/CD pipeline changes
   - build: Build system or external dependency changes

4. Body (if multiple significant changes):
   - Leave blank line after subject
   - Use bullet points with "- " prefix
   - Explain WHY the change was needed, not HOW it was implemented
   - Reference issue numbers if mentioned in code/comments (e.g., "Fixes #123")
   - Keep lines under 72 characters

5. Breaking changes:
   - Add "BREAKING CHANGE:" in body or append "!" after type
   - Explain the breaking change and migration path

EXAMPLES:

Good:
feat(auth): add OAuth2 authentication flow
fix(parser): resolve crash when handling empty input
docs: update installation instructions for Python 3.12
refactor(api): simplify error handling logic
perf(database): optimize query performance with indexes

With body:
feat(api): add user profile endpoint

- Implement GET /api/users/:id endpoint
- Add profile photo upload support
- Include privacy settings in response

Fixes #456

Bad (avoid):
fix: bug fix (too vague)
feat: added new stuff (past tense, vague)
update files (no type, unclear)
Fixed the thing that was broken (past tense, unclear)

OUTPUT FORMAT:
Return ONLY ONE commit message for the CURRENT changes, nothing else.
- No explanations, no quotes, no markdown formatting
- Do NOT generate multiple commit messages
- Do NOT describe past commits or commit history
- Focus on what is being changed RIGHT NOW in this commit
If the changes are too complex to summarize in one commit, focus on the primary/most significant change."""

        user_message = f"""Analyze these CURRENT UNCOMMITTED changes and generate ONE commit message:

{context}{style_context}

IMPORTANT: Generate ONE commit message for these current changes ONLY.
Do NOT describe multiple separate commits or reference commit history.

Remember:
- Use conventional commits format
- Subject line under 72 characters
- Focus on WHAT and WHY, not HOW
- Be specific and actionable
- Use imperative mood
- Generate ONLY ONE commit message"""

        # Estimate tokens for cost awareness
        estimated_input_tokens = self._estimate_token_count(
            system_message
        ) + self._estimate_token_count(user_message)
        estimated_output_tokens = self.config.max_tokens
        estimated_total_tokens = estimated_input_tokens + estimated_output_tokens

        # Warn if token usage exceeds configured threshold
        if estimated_total_tokens > self.config.max_input_tokens:
            from .errors import print_warning

            print_warning(
                f"Estimated token usage (~{estimated_total_tokens} tokens) exceeds "
                f"configured limit ({self.config.max_input_tokens} tokens). "
                "This may result in significant API costs. "
                "Consider reducing max_context_files or max_diff_lines in config."
            )

        # Generate commit message using LLM with retry
        try:
            # Show progress indicator if enabled
            if self.config.show_progress:
                with console.status(
                    "[cyan]Generating commit message...[/cyan]", spinner="dots"
                ):
                    # Wrap API call with retry decorator
                    if self.config.api_retry_enabled:
                        generate_fn = self._create_retryable_generate(
                            system_message, user_message
                        )
                        message_str: str = generate_fn()
                    else:
                        message_str = self._call_api(system_message, user_message)
            else:
                # No progress indicator
                if self.config.api_retry_enabled:
                    generate_fn = self._create_retryable_generate(
                        system_message, user_message
                    )
                    message_str = generate_fn()
                else:
                    message_str = self._call_api(system_message, user_message)

            # Cache the result
            if self.cache and message_str:
                self.cache.set(changeset, message_str)

            return message_str

        except Exception as e:
            # Log API errors and use fallback
            from .errors import print_warning

            print_warning(f"LLM generation failed: {e}. Using fallback message.")
            if hasattr(e, "__class__"):
                print(f"  Error type: {e.__class__.__name__}", file=sys.stderr)
            return self._fallback_message(changeset)

    def _call_api(self, system_message: str, user_message: str) -> str:
        """
        Make the actual API call to OpenAI.

        Args:
            system_message: System prompt
            user_message: User prompt

        Returns:
            Generated commit message
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        message = response.choices[0].message.content
        if message is None:
            raise APIError("API returned empty response")

        # Clean up message
        message_str: str = message.strip()
        message_str = message_str.strip("\"'")

        # Check for truncation (incomplete output)
        self._check_truncation(message_str, response)

        return message_str

    def _check_truncation(self, message: str, response: Any) -> None:
        """
        Check if the generated message appears to be truncated.

        Args:
            message: Generated message text
            response: API response object
        """
        from .errors import print_warning

        # Check if finish_reason indicates truncation
        finish_reason = response.choices[0].finish_reason
        if finish_reason == "length":
            print_warning(
                f"⚠️  Generated commit message was truncated due to max_tokens limit ({self.config.max_tokens}).\n"
                f"   Consider increasing max_tokens in your config file (~/.lazycommitrc).\n"
                f"   Recommended: max_tokens=400 or higher for messages with bullet points."
            )
            return

        # Check for common truncation patterns
        lines = message.split("\n")
        last_line = lines[-1].strip() if lines else ""

        # Check if last line seems incomplete (ends mid-word or with incomplete bullet)
        truncation_indicators = [
            last_line.endswith("- "),  # Incomplete bullet point
            last_line.endswith("-"),  # Cut off hyphen
            last_line.endswith("for"),  # Cut off mid-phrase
            last_line
            and last_line[-1] not in ".!?)'\""  # Doesn't end with punctuation
            and len(last_line.split()) > 3  # But is substantial enough to need it
            and not last_line.startswith("- "),  # And is not a bullet point
        ]

        if any(truncation_indicators):
            print_warning(
                f"⚠️  Generated commit message may be incomplete.\n"
                f"   Last line: '{last_line}'\n"
                f"   Consider increasing max_tokens in config (current: {self.config.max_tokens})."
            )

    def _create_retryable_generate(
        self, system_message: str, user_message: str
    ) -> Callable[[], str]:
        """
        Create a retryable version of API call.

        Args:
            system_message: System prompt
            user_message: User prompt

        Returns:
            Callable that makes API call with retry
        """

        def on_retry(exception: Exception, attempt: int, delay: float) -> None:
            """Callback for retry events."""
            from .errors import print_warning

            print_warning(
                f"API call failed (attempt {attempt}). Retrying in {delay:.1f}s..."
            )

        @retry_on_api_error(
            max_retries=self.config.api_max_retries,
            initial_delay=self.config.api_initial_retry_delay,
            on_retry=on_retry,
        )
        def generate() -> str:
            return self._call_api(system_message, user_message)

        return generate

    def _build_context(self, changeset: ChangeSet, detector: ChangeDetector) -> str:
        """Build context string for LLM prompt."""
        lines = []

        # Add file changes summary with types
        lines.append("Repository changes summary:")
        lines.append(f"  Total files: {changeset.total_changes}")

        # Categorize files by type for better scope understanding
        file_types: dict[str, list[Any]] = {}
        all_changes = changeset.staged_changes + changeset.unstaged_changes

        for change in all_changes:
            ext = change.path.suffix.lower()
            if ext not in file_types:
                file_types[ext] = []
            file_types[ext].append(change)

        if file_types:
            type_summary = ", ".join(
                [f"{len(files)}{ext or ' no-ext'}" for ext, files in file_types.items()]
            )
            lines.append(f"  File types: {type_summary}")

        lines.append("")  # Blank line

        # Process staged and unstaged changes with better organization
        if all_changes:
            lines.append("File changes with diffs:")
            for i, change in enumerate(all_changes[: self.config.max_context_files]):
                if i > 0:
                    lines.append("")  # Separator between files

                relative_path = change.path.relative_to(detector.repo_path)
                status_symbol = {
                    "MODIFIED": "M",
                    "ADDED": "A",
                    "DELETED": "D",
                    "RENAMED": "R",
                }.get(change.status.value, "?")

                lines.append(f"[{status_symbol}] {relative_path}")

                # Add diff for modified/added files (truncated)
                if change.diff and len(change.diff) > 0:
                    diff_lines = change.diff.split("\n")[: self.config.max_diff_lines]
                    # Add indentation for readability
                    formatted_diff = "\n".join(f"  {line}" for line in diff_lines)
                    lines.append(formatted_diff)

                    # Indicate if truncated
                    full_diff_lines = len(change.diff.split("\n"))
                    if full_diff_lines > self.config.max_diff_lines:
                        lines.append(
                            f"  ... ({full_diff_lines - self.config.max_diff_lines} more lines)"
                        )

        # Add untracked files with better formatting
        if changeset.untracked_files:
            lines.append("\nNew untracked files:")
            for path in changeset.untracked_files[: self.config.max_context_files]:
                relative_path = path.relative_to(detector.repo_path)
                lines.append(f"  [NEW] {relative_path}")

            if len(changeset.untracked_files) > self.config.max_context_files:
                remaining = (
                    len(changeset.untracked_files) - self.config.max_context_files
                )
                lines.append(f"  ... and {remaining} more files")

        return "\n".join(lines)

    def _fallback_message(self, changeset: ChangeSet) -> str:
        """Generate a simple fallback message if LLM fails."""
        total = changeset.total_changes
        if total == 1:
            return "chore: update file"
        return f"chore: update {total} files"

    def get_commit_history(self, repo_path: str, limit: int = 20) -> List[str]:
        """
        Get recent commit messages from the repository.

        Args:
            repo_path: Path to the git repository
            limit: Maximum number of commits to retrieve

        Returns:
            List of recent commit messages
        """
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    repo_path,
                    "log",
                    f"-{limit}",
                    "--pretty=format:%s",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            messages = [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            return messages
        except subprocess.CalledProcessError:
            return []

    def analyze_commit_style(self, messages: List[str]) -> str:
        """
        Analyze commit messages to determine the user's style.

        Args:
            messages: List of recent commit messages

        Returns:
            A summary of the user's commit style for the LLM
        """
        if not messages:
            return ""

        # Analyze patterns
        uses_conventional = 0
        uses_emoji = 0
        common_types: dict[str, int] = {}
        avg_length = 0

        for msg in messages:
            avg_length += len(msg)

            # Check for conventional commits pattern
            if any(
                msg.startswith(f"{t}:") or msg.startswith(f"{t}(")
                for t in [
                    "feat",
                    "fix",
                    "docs",
                    "style",
                    "refactor",
                    "test",
                    "chore",
                    "perf",
                    "ci",
                    "build",
                ]
            ):
                uses_conventional += 1
                # Extract type
                commit_type = msg.split(":")[0].split("(")[0]
                common_types[commit_type] = common_types.get(commit_type, 0) + 1

            # Check for emoji usage
            if any(ord(c) > 127 for c in msg[:5]):
                uses_emoji += 1

        avg_length = avg_length // len(messages) if messages else 0
        conventional_ratio = uses_conventional / len(messages) if messages else 0
        emoji_ratio = uses_emoji / len(messages) if messages else 0

        # Build style summary
        style_notes = []

        if conventional_ratio > 0.5:
            style_notes.append("User follows conventional commits format")
            if common_types:
                top_types = sorted(common_types.items(), key=lambda x: -x[1])[:3]
                types_str = ", ".join([f"{t}" for t, _ in top_types])
                style_notes.append(f"Commonly used types: {types_str}")

        if emoji_ratio > 0.3:
            style_notes.append("User often includes emojis in commit messages")

        if avg_length < 50:
            style_notes.append("User prefers short, concise commit messages")
        elif avg_length > 100:
            style_notes.append("User often writes detailed commit messages")

        if style_notes:
            # Keep style notes very brief to avoid context bloat
            # Only include the most relevant information
            brief_notes = style_notes[:2]  # Max 2 style observations
            return "\n\nStyle preference: " + "; ".join(brief_notes)

        return ""
