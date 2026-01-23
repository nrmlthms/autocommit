"""Unit tests for retry utilities."""

import pytest

from lazycommit.retry import (
    exponential_backoff,
    retry_on_api_error,
    should_retry_api_error,
)


class TestExponentialBackoff:
    """Test cases for exponential_backoff decorator."""

    def test_succeeds_on_first_try(self) -> None:
        """Test function that succeeds on first attempt."""
        call_count = 0

        @exponential_backoff(max_retries=3)
        def succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeeds()

        assert result == "success"
        assert call_count == 1

    def test_succeeds_after_retry(self) -> None:
        """Test function that succeeds after retries."""
        call_count = 0

        @exponential_backoff(max_retries=3, initial_delay=0.01)
        def succeeds_after_two_tries() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"

        result = succeeds_after_two_tries()

        assert result == "success"
        assert call_count == 2

    def test_fails_after_max_retries(self) -> None:
        """Test function that exhausts all retries."""

        @exponential_backoff(max_retries=2, initial_delay=0.01)
        def always_fails() -> str:
            raise ValueError("Permanent failure")

        with pytest.raises(ValueError, match="Permanent failure"):
            always_fails()

    def test_respects_exception_filter(self) -> None:
        """Test that only specified exceptions are retried."""

        @exponential_backoff(max_retries=3, exceptions=ValueError)
        def raises_type_error() -> str:
            raise TypeError("Wrong exception type")

        # Should not retry on TypeError
        with pytest.raises(TypeError):
            raises_type_error()

    def test_exponential_delay(self) -> None:
        """Test that delay increases exponentially."""
        delays: list[float] = []

        def on_retry(e: Exception, attempt: int, delay: float) -> None:
            delays.append(delay)

        @exponential_backoff(
            max_retries=3,
            initial_delay=0.1,
            backoff_factor=2.0,
            on_retry=on_retry,
        )
        def always_fails() -> str:
            raise Exception("Fail")

        with pytest.raises(Exception):
            always_fails()

        # Verify delays increase exponentially
        assert len(delays) == 3
        assert delays[0] == 0.1
        assert delays[1] == 0.2
        assert delays[2] == 0.4

    def test_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        delays: list[float] = []

        def on_retry(e: Exception, attempt: int, delay: float) -> None:
            delays.append(delay)

        @exponential_backoff(
            max_retries=5,
            initial_delay=10.0,
            max_delay=15.0,
            backoff_factor=2.0,
            on_retry=on_retry,
        )
        def always_fails() -> str:
            raise Exception("Fail")

        with pytest.raises(Exception):
            always_fails()

        # All delays should be capped at max_delay
        for delay in delays:
            assert delay <= 15.0


class TestShouldRetryApiError:
    """Test cases for should_retry_api_error function."""

    def test_retryable_timeout_error(self) -> None:
        """Test that timeout errors are retryable."""
        error = Exception("Request timeout")
        assert should_retry_api_error(error) is True

    def test_retryable_connection_error(self) -> None:
        """Test that connection errors are retryable."""
        error = Exception("Connection refused")
        assert should_retry_api_error(error) is True

    def test_retryable_rate_limit_error(self) -> None:
        """Test that rate limit errors are retryable."""
        error = Exception("Rate limit exceeded - 429")
        assert should_retry_api_error(error) is True

    def test_retryable_5xx_errors(self) -> None:
        """Test that 5xx errors are retryable."""
        assert should_retry_api_error(Exception("500 Internal Server Error"))
        assert should_retry_api_error(Exception("502 Bad Gateway"))
        assert should_retry_api_error(Exception("503 Service Unavailable"))
        assert should_retry_api_error(Exception("504 Gateway Timeout"))

    def test_non_retryable_auth_error(self) -> None:
        """Test that authentication errors are not retryable."""
        error = Exception("Invalid API key")
        assert should_retry_api_error(error) is False

    def test_non_retryable_validation_error(self) -> None:
        """Test that validation errors are not retryable."""
        error = Exception("Invalid request parameters")
        assert should_retry_api_error(error) is False


class TestRetryOnApiError:
    """Test cases for retry_on_api_error decorator."""

    def test_succeeds_without_retry(self) -> None:
        """Test successful API call without retry."""
        call_count = 0

        @retry_on_api_error(max_retries=3)
        def api_call() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = api_call()

        assert result == "success"
        assert call_count == 1

    def test_retries_on_retryable_error(self) -> None:
        """Test retry on retryable errors."""
        call_count = 0

        @retry_on_api_error(max_retries=3, initial_delay=0.01)
        def api_call_with_timeout() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Timeout error")
            return "success"

        result = api_call_with_timeout()

        assert result == "success"
        assert call_count == 2

    def test_no_retry_on_non_retryable_error(self) -> None:
        """Test that non-retryable errors fail immediately."""
        call_count = 0

        @retry_on_api_error(max_retries=3)
        def api_call_with_auth_error() -> str:
            nonlocal call_count
            call_count += 1
            raise Exception("Invalid API key")

        with pytest.raises(Exception, match="Invalid API key"):
            api_call_with_auth_error()

        # Should not retry on auth error
        assert call_count == 1

    def test_on_retry_callback(self) -> None:
        """Test that on_retry callback is called."""
        retry_events: list[tuple[Exception, int, float]] = []

        def on_retry(e: Exception, attempt: int, delay: float) -> None:
            retry_events.append((e, attempt, delay))

        @retry_on_api_error(max_retries=2, initial_delay=0.01, on_retry=on_retry)
        def api_call() -> str:
            if len(retry_events) < 2:
                raise Exception("Timeout")
            return "success"

        result = api_call()

        assert result == "success"
        assert len(retry_events) == 2
        assert retry_events[0][1] == 1  # First retry attempt
        assert retry_events[1][1] == 2  # Second retry attempt
