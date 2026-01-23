"""File monitoring component using watchfiles library."""

import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Optional, Set, Union
from enum import Enum

from watchfiles import awatch, Change


class ChangeType(Enum):
    """Types of file changes."""

    ADDED = Change.added
    MODIFIED = Change.modified
    DELETED = Change.deleted


class FileMonitor:
    """Monitor file system changes in a directory."""

    def __init__(
        self,
        watch_path: Union[str, Path],
        recursive: bool = True,
        ignore_patterns: Optional[Set[str]] = None,
    ):
        """
        Initialize the file monitor.

        Args:
            watch_path: Directory path to monitor
            recursive: Whether to watch subdirectories
            ignore_patterns: Set of glob patterns to ignore (e.g., {'*.pyc', '__pycache__'})
        """
        self.watch_path = Path(watch_path).resolve()
        self.recursive = recursive
        self.ignore_patterns = ignore_patterns or {
            "*.pyc",
            "__pycache__",
            ".git",
            ".env",
            "*.swp",
            ".DS_Store",
        }
        self._running = False
        self._callback: Optional[
            Callable[[ChangeType, Path], Union[None, Awaitable[None]]]
        ] = None

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on patterns."""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False

    async def start(
        self,
        callback: Callable[[ChangeType, Path], Union[None, Awaitable[None]]],
        debounce: int = 1600,
    ) -> None:
        """
        Start monitoring for file changes.

        Args:
            callback: Function to call when changes are detected.
                     Receives (change_type, file_path) as arguments.
            debounce: Milliseconds to wait before processing changes (default: 1600ms)
        """
        self._running = True
        self._callback = callback

        print(f"Monitoring {self.watch_path} for changes...")

        async for changes in awatch(
            self.watch_path,
            recursive=self.recursive,
            debounce=debounce,
        ):
            if not self._running:
                break

            for change_type, path_str in changes:
                path = Path(path_str)

                if self._should_ignore(path):
                    continue

                change = ChangeType(change_type)

                try:
                    await self._handle_change(change, path)
                except Exception as e:
                    print(f"Error handling change for {path}: {e}")

    async def _handle_change(self, change_type: ChangeType, path: Path) -> None:
        """Handle a file change event."""
        if self._callback:
            if asyncio.iscoroutinefunction(self._callback):
                await self._callback(change_type, path)
            else:
                self._callback(change_type, path)

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        print("Stopping file monitor...")


class SyncFileMonitor:
    """Synchronous wrapper for FileMonitor."""

    def __init__(
        self,
        watch_path: Union[str, Path],
        recursive: bool = True,
        ignore_patterns: Optional[Set[str]] = None,
    ):
        """Initialize sync file monitor with same parameters as FileMonitor."""
        self.monitor = FileMonitor(watch_path, recursive, ignore_patterns)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(
        self,
        callback: Callable[[ChangeType, Path], None],
        debounce: int = 1600,
    ) -> None:
        """
        Start monitoring synchronously (blocks until stopped).

        Args:
            callback: Function to call when changes are detected
            debounce: Milliseconds to wait before processing changes
        """
        try:
            asyncio.run(self.monitor.start(callback, debounce))
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the monitor."""
        self.monitor.stop()


if __name__ == "__main__":
    # Example usage
    async def on_change(change_type: ChangeType, path: Path) -> None:
        """Example callback function."""
        print(f"{change_type.name}: {path}")

    # Async usage
    async def main() -> None:
        monitor = FileMonitor(".", recursive=True)
        try:
            await monitor.start(on_change)
        except KeyboardInterrupt:
            monitor.stop()

    # Run the example
    asyncio.run(main())
