"""Commit message generation using LLM."""

import os
import sys
from typing import Callable, Optional

from openai import OpenAI

from .cache import CommitMessageCache
from .config import Config
from .detector import ChangeDetector, ChangeSet
from .exceptions import APIError, ConfigurationError
from .retry import retry_on_api_error


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
        self, changeset: ChangeSet, detector: ChangeDetector
    ) -> str:
        """
        Generate a commit message using LLM based on the changeset.

        Args:
            changeset: The detected changes
            detector: ChangeDetector instance for getting diffs

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

        # Estimate token count before API call
        system_message = (
            "You are a helpful assistant that generates concise, "
            "conventional commit messages based on git diffs. "
            "Follow the conventional commits format: "
            "<type>: <description>. "
            "Types: feat, fix, docs, style, refactor, test, chore. "
            "Keep the message under 72 characters if possible. "
            "Be specific but concise."
        )
        user_message = f"Generate a commit message for these changes:\n\n{context}"

        # Estimate tokens for cost awareness
        estimated_input_tokens = (
            self._estimate_token_count(system_message) +
            self._estimate_token_count(user_message)
        )
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
            # Wrap API call with retry decorator
            if self.config.api_retry_enabled:
                generate_fn = self._create_retryable_generate(
                    system_message, user_message
                )
                message_str: str = generate_fn()
            else:
                message_str = self._call_api(system_message, user_message)

            # Cache the result
            if self.cache and message_str:
                self.cache.set(changeset, message_str)

            return message_str

        except Exception as e:
            # Wrap API errors
            api_error = APIError(
                message=f"LLM generation failed: {str(e)}",
                original_error=e,
            )
            from .errors import print_warning

            print_warning(f"LLM generation failed. Using fallback message.")
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
        message_str = message_str.strip('"\'')
        return message_str

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

        # Add file changes summary
        lines.append(f"Total files changed: {changeset.total_changes}\n")

        # Process staged and unstaged changes
        all_changes = changeset.staged_changes + changeset.unstaged_changes

        if all_changes:
            lines.append("Modified/Added/Deleted files:")
            for change in all_changes[:self.config.max_context_files]:
                relative_path = change.path.relative_to(detector.repo_path)
                lines.append(f"  {change.status.value} {relative_path}")

                # Add diff for modified/added files (truncated)
                if change.diff and len(change.diff) > 0:
                    diff_lines = change.diff.split('\n')[:self.config.max_diff_lines]
                    lines.append("    " + "\n    ".join(diff_lines))

        # Add untracked files
        if changeset.untracked_files:
            lines.append("\nUntracked files:")
            for path in changeset.untracked_files[:self.config.max_context_files]:
                relative_path = path.relative_to(detector.repo_path)
                lines.append(f"  ?? {relative_path}")

        return "\n".join(lines)

    def _fallback_message(self, changeset: ChangeSet) -> str:
        """Generate a simple fallback message if LLM fails."""
        total = changeset.total_changes
        if total == 1:
            return "chore: update file"
        return f"chore: update {total} files"
