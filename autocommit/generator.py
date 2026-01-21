"""Commit message generation using LLM."""

import os
import sys
from typing import Optional

from openai import OpenAI

from .detector import ChangeDetector, ChangeSet


class LLMCommitMessageGenerator:
    """Generate commit messages using LLM via OpenAI client."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM commit message generator.

        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: OpenAI model to use for generation
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

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

        # Build context for LLM
        context = self._build_context(changeset, detector)

        # Generate commit message using LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that generates concise, "
                            "conventional commit messages based on git diffs. "
                            "Follow the conventional commits format: "
                            "<type>: <description>. "
                            "Types: feat, fix, docs, style, refactor, test, chore. "
                            "Keep the message under 72 characters if possible. "
                            "Be specific but concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Generate a commit message for these changes:\n\n{context}",
                    },
                ],
                temperature=0.7,
                max_tokens=100,
            )

            message = response.choices[0].message.content.strip()
            # Remove quotes if LLM added them
            message = message.strip('"\'')
            return message

        except Exception as e:
            print(f"Warning: LLM generation failed ({e}). Using fallback.", file=sys.stderr)
            return self._fallback_message(changeset)

    def _build_context(self, changeset: ChangeSet, detector: ChangeDetector) -> str:
        """Build context string for LLM prompt."""
        lines = []

        # Add file changes summary
        lines.append(f"Total files changed: {changeset.total_changes}\n")

        # Process staged and unstaged changes
        all_changes = changeset.staged_changes + changeset.unstaged_changes

        if all_changes:
            lines.append("Modified/Added/Deleted files:")
            for change in all_changes[:10]:  # Limit to first 10 files
                relative_path = change.path.relative_to(detector.repo_path)
                lines.append(f"  {change.status.value} {relative_path}")

                # Add diff for modified/added files (truncated)
                if change.diff and len(change.diff) > 0:
                    diff_lines = change.diff.split('\n')[:20]  # First 20 lines of diff
                    lines.append("    " + "\n    ".join(diff_lines))

        # Add untracked files
        if changeset.untracked_files:
            lines.append("\nUntracked files:")
            for path in changeset.untracked_files[:10]:  # Limit to first 10
                relative_path = path.relative_to(detector.repo_path)
                lines.append(f"  ?? {relative_path}")

        return "\n".join(lines)

    def _fallback_message(self, changeset: ChangeSet) -> str:
        """Generate a simple fallback message if LLM fails."""
        total = changeset.total_changes
        if total == 1:
            return "chore: update file"
        return f"chore: update {total} files"
