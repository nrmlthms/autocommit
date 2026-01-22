"""Retry utilities with exponential backoff."""

import functools
import time
from typing import Any, Callable, Optional, Type, TypeVar, Union

F = TypeVar("F", bound=Callable[..., Any])


def exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable[[F], F]:
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        backoff_factor: Multiplier for delay after each retry
        exceptions: Exception type(s) to catch and retry
        on_retry: Optional callback called on each retry (exception, attempt, delay)

    Returns:
        Decorated function that retries on failure

    Example:
        @exponential_backoff(max_retries=3, initial_delay=1.0)
        def api_call():
            return requests.get("https://api.example.com")
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt == max_retries:
                        break

                    # Calculate next delay with exponential backoff
                    current_delay = min(delay, max_delay)

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt + 1, current_delay)

                    # Wait before retrying
                    time.sleep(current_delay)

                    # Increase delay for next retry
                    delay *= backoff_factor

            # If we get here, all retries failed
            if last_exception:
                raise last_exception

            # This shouldn't happen, but just in case
            raise RuntimeError("Retry logic failed unexpectedly")

        return wrapper  # type: ignore

    return decorator


def should_retry_api_error(exception: Exception) -> bool:
    """
    Determine if an API error should be retried.

    Args:
        exception: The exception to check

    Returns:
        True if the error is retryable (network/timeout), False otherwise
    """
    # Import here to avoid circular dependency
    error_message = str(exception).lower()

    # Retryable network/timeout errors
    retryable_patterns = [
        "timeout",
        "connection",
        "network",
        "rate limit",
        "429",  # Too Many Requests
        "500",  # Internal Server Error
        "502",  # Bad Gateway
        "503",  # Service Unavailable
        "504",  # Gateway Timeout
    ]

    return any(pattern in error_message for pattern in retryable_patterns)


def retry_on_api_error(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable[[F], F]:
    """
    Decorator to retry API calls with exponential backoff on retryable errors.

    Only retries on network/timeout errors, not on authentication or validation errors.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        on_retry: Optional callback for retry events

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if error is retryable
                    if not should_retry_api_error(e):
                        # Don't retry on non-retryable errors
                        raise

                    # Don't retry on last attempt
                    if attempt == max_retries:
                        break

                    # Calculate delay
                    current_delay = min(delay, 60.0)

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt + 1, current_delay)

                    # Wait before retrying
                    time.sleep(current_delay)

                    # Increase delay for next retry
                    delay *= 2.0

            # If we get here, all retries failed
            if last_exception:
                raise last_exception

            raise RuntimeError("Retry logic failed unexpectedly")

        return wrapper  # type: ignore

    return decorator
