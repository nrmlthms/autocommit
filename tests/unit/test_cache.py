"""Unit tests for commit message cache."""

import tempfile
import time
from pathlib import Path

import pytest

from lazycommit.cache import CommitMessageCache
from lazycommit.detector import ChangeSet, FileChange, FileStatus


@pytest.fixture
def temp_cache_dir() -> Path:
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestCommitMessageCache:
    """Test cases for CommitMessageCache."""

    def test_init_creates_cache_dir(self, temp_cache_dir: Path) -> None:
        """Test that cache directory is created."""
        cache_dir = temp_cache_dir / "cache"
        cache = CommitMessageCache(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert cache.cache_file == cache_dir / "commit_messages.json"

    def test_cache_miss(self, temp_cache_dir: Path) -> None:
        """Test getting non-existent cache entry."""
        cache = CommitMessageCache(cache_dir=temp_cache_dir)

        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        result = cache.get(changeset)
        assert result is None

    def test_cache_hit(self, temp_cache_dir: Path) -> None:
        """Test setting and getting cache entry."""
        cache = CommitMessageCache(cache_dir=temp_cache_dir)

        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        # Set cache
        cache.set(changeset, "feat: add new feature")

        # Get cache
        result = cache.get(changeset)
        assert result == "feat: add new feature"

    def test_different_changesets_different_cache(self, temp_cache_dir: Path) -> None:
        """Test that different changesets have different cache entries."""
        cache = CommitMessageCache(cache_dir=temp_cache_dir)

        changeset1 = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file1.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        changeset2 = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file2.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        cache.set(changeset1, "feat: add file1")
        cache.set(changeset2, "feat: add file2")

        assert cache.get(changeset1) == "feat: add file1"
        assert cache.get(changeset2) == "feat: add file2"

    def test_cache_persistence(self, temp_cache_dir: Path) -> None:
        """Test that cache persists across instances."""
        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        # Create first cache instance and set entry
        cache1 = CommitMessageCache(cache_dir=temp_cache_dir)
        cache1.set(changeset, "feat: persistent message")

        # Create second cache instance and verify entry exists
        cache2 = CommitMessageCache(cache_dir=temp_cache_dir)
        result = cache2.get(changeset)
        assert result == "feat: persistent message"

    def test_cache_expiration(self, temp_cache_dir: Path) -> None:
        """Test that old cache entries expire."""
        # Create cache with very short max age (0 days)
        cache = CommitMessageCache(cache_dir=temp_cache_dir, max_age_days=0)

        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        cache.set(changeset, "feat: expired message")

        # Wait a tiny bit for expiration
        time.sleep(0.1)

        # Entry should be expired
        result = cache.get(changeset)
        assert result is None

    def test_cache_size_limit(self, temp_cache_dir: Path) -> None:
        """Test that cache respects max entries limit."""
        cache = CommitMessageCache(cache_dir=temp_cache_dir, max_entries=3)

        # Add more entries than max
        for i in range(5):
            changeset = ChangeSet(
                staged_changes=[
                    FileChange(
                        path=Path(f"/test/file{i}.py"),
                        status=FileStatus.MODIFIED,
                        staged=True,
                    )
                ],
                unstaged_changes=[],
                untracked_files=[],
            )
            cache.set(changeset, f"feat: add file{i}")
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Cache should have at most max_entries
        assert cache.size() <= 3

    def test_cache_clear(self, temp_cache_dir: Path) -> None:
        """Test clearing the cache."""
        cache = CommitMessageCache(cache_dir=temp_cache_dir)

        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        cache.set(changeset, "feat: test")
        assert cache.size() == 1

        cache.clear()
        assert cache.size() == 0
        assert cache.get(changeset) is None

    def test_cache_stats(self, temp_cache_dir: Path) -> None:
        """Test getting cache statistics."""
        cache = CommitMessageCache(
            cache_dir=temp_cache_dir, max_entries=10, max_age_days=30
        )

        changeset = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        cache.set(changeset, "feat: test")

        stats = cache.get_stats()

        assert stats["total_entries"] == 1
        assert stats["valid_entries"] == 1
        assert stats["expired_entries"] == 0
        assert stats["max_entries"] == 10
        assert stats["max_age_days"] == 30

    def test_same_changeset_same_hash(self, temp_cache_dir: Path) -> None:
        """Test that identical changesets produce the same cache key."""
        cache = CommitMessageCache(cache_dir=temp_cache_dir)

        # Create two identical changesets
        changeset1 = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        changeset2 = ChangeSet(
            staged_changes=[
                FileChange(
                    path=Path("/test/file.py"),
                    status=FileStatus.MODIFIED,
                    staged=True,
                )
            ],
            unstaged_changes=[],
            untracked_files=[],
        )

        # Set with first changeset
        cache.set(changeset1, "feat: same message")

        # Should get with second changeset
        result = cache.get(changeset2)
        assert result == "feat: same message"
