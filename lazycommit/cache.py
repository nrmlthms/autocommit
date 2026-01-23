"""Caching system for commit messages."""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

from .detector import ChangeSet


class CommitMessageCache:
    """Cache for LLM-generated commit messages."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_age_days: int = 30,
        max_entries: int = 100,
    ):
        """
        Initialize commit message cache.

        Args:
            cache_dir: Directory to store cache (default: ~/.lazycommit/cache)
            max_age_days: Maximum age of cache entries in days
            max_entries: Maximum number of cache entries to keep
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".lazycommit" / "cache"

        self.cache_dir = cache_dir
        self.cache_file = cache_dir / "commit_messages.json"
        self.max_age_days = max_age_days
        self.max_entries = max_entries

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load cache
        self._cache: dict[str, dict[str, str | float]] = self._load_cache()

    def _load_cache(self) -> dict[str, dict[str, str | float]]:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, "r") as f:
                data: dict[str, dict[str, str | float]] = json.load(f)
                return data
        except (json.JSONDecodeError, IOError):
            # If cache is corrupted, start fresh
            return {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self._cache, f, indent=2)
        except IOError:
            # Silently fail if we can't write cache
            pass

    def _compute_changeset_hash(self, changeset: ChangeSet) -> str:
        """
        Compute a hash of the changeset for cache key.

        Args:
            changeset: The changeset to hash

        Returns:
            SHA256 hash of the changeset
        """
        # Create a deterministic string representation of the changeset
        parts = []

        # Add file statuses and paths (sorted for determinism)
        for change in sorted(
            changeset.staged_changes + changeset.unstaged_changes,
            key=lambda c: str(c.path),
        ):
            parts.append(f"{change.status.value}:{change.path.name}")

            # Include abbreviated diff if available
            if change.diff:
                # Take first 500 chars of diff for hashing
                parts.append(change.diff[:500])

        for path in sorted(changeset.untracked_files, key=lambda p: str(p)):
            parts.append(f"??:{path.name}")

        # Compute hash
        content = "|".join(parts)
        return hashlib.sha256(content.encode()).hexdigest()

    def _is_expired(self, timestamp: float) -> bool:
        """Check if a cache entry is expired."""
        max_age_seconds = self.max_age_days * 24 * 60 * 60
        return (time.time() - timestamp) > max_age_seconds

    def _cleanup_old_entries(self) -> None:
        """Remove expired and excess cache entries."""
        # Remove expired entries
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if self._is_expired(float(entry["timestamp"]))
        ]
        for key in expired_keys:
            del self._cache[key]

        # If still too many entries, remove oldest
        if len(self._cache) > self.max_entries:
            # Sort by timestamp and keep only newest
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: float(x[1]["timestamp"]),
                reverse=True,
            )
            self._cache = dict(sorted_entries[: self.max_entries])

    def get(self, changeset: ChangeSet) -> Optional[str]:
        """
        Get cached commit message for a changeset.

        Args:
            changeset: The changeset to look up

        Returns:
            Cached commit message or None if not found/expired
        """
        cache_key = self._compute_changeset_hash(changeset)

        if cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]

        # Check if expired
        if self._is_expired(float(entry["timestamp"])):
            del self._cache[cache_key]
            return None

        return str(entry["message"])

    def set(self, changeset: ChangeSet, message: str) -> None:
        """
        Cache a commit message for a changeset.

        Args:
            changeset: The changeset
            message: The commit message to cache
        """
        cache_key = self._compute_changeset_hash(changeset)

        self._cache[cache_key] = {
            "message": message,
            "timestamp": time.time(),
        }

        # Cleanup old entries
        self._cleanup_old_entries()

        # Save to disk
        self._save_cache()

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

    def size(self) -> int:
        """Get number of cache entries."""
        return len(self._cache)

    def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_entries = len(self._cache)
        expired_entries = sum(
            1
            for entry in self._cache.values()
            if self._is_expired(float(entry["timestamp"]))
        )

        return {
            "total_entries": total_entries,
            "valid_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "max_entries": self.max_entries,
            "max_age_days": self.max_age_days,
        }
