"""Rate limiter for API calls using token bucket algorithm."""

import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Tuple


class RateLimiter:
    """Token bucket rate limiter for API calls.

    Prevents exceeding API provider rate limits by tracking both:
    - Tokens per minute (for token-based limits)
    - Requests per minute (for request-based limits)

    Uses sliding window approach for accurate limiting.
    """

    def __init__(
        self,
        tokens_per_minute: int = 40000,
        requests_per_minute: int = 50
    ):
        """Initialize rate limiter.

        Args:
            tokens_per_minute: Maximum tokens allowed per minute
            requests_per_minute: Maximum requests allowed per minute
        """
        self.tokens_per_minute = tokens_per_minute
        self.requests_per_minute = requests_per_minute

        # Deques store (timestamp, value) tuples
        self.token_timestamps = deque()  # (timestamp, token_count)
        self.request_timestamps = deque()  # timestamp

        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """Wait until rate limit allows this request.

        Args:
            estimated_tokens: Estimated token count for this request
        """
        async with self.lock:
            while True:
                now = datetime.now()
                minute_ago = now - timedelta(minutes=1)

                # Remove timestamps older than 1 minute
                self._cleanup_old_timestamps(minute_ago)

                # Calculate current usage
                tokens_used = sum(t[1] for t in self.token_timestamps)
                requests_made = len(self.request_timestamps)

                # Check if we can proceed
                tokens_available = tokens_used + estimated_tokens <= self.tokens_per_minute
                requests_available = requests_made < self.requests_per_minute

                if tokens_available and requests_available:
                    # Record this request
                    self.token_timestamps.append((now, estimated_tokens))
                    self.request_timestamps.append(now)
                    break

                # Need to wait - calculate how long
                wait_time = self._calculate_wait_time(
                    minute_ago,
                    tokens_used,
                    estimated_tokens,
                    requests_made
                )

                # Wait and try again
                await asyncio.sleep(wait_time)

    def _cleanup_old_timestamps(self, cutoff: datetime) -> None:
        """Remove timestamps older than cutoff."""
        while self.token_timestamps and self.token_timestamps[0][0] < cutoff:
            self.token_timestamps.popleft()
        while self.request_timestamps and self.request_timestamps[0] < cutoff:
            self.request_timestamps.popleft()

    def _calculate_wait_time(
        self,
        minute_ago: datetime,
        tokens_used: int,
        estimated_tokens: int,
        requests_made: int
    ) -> float:
        """Calculate how long to wait before retrying.

        Returns:
            Wait time in seconds
        """
        wait_times = []

        # If we're over token limit, wait until oldest tokens expire
        if tokens_used + estimated_tokens > self.tokens_per_minute:
            if self.token_timestamps:
                oldest_token_time = self.token_timestamps[0][0]
                wait_for_tokens = (oldest_token_time - minute_ago).total_seconds() + 1
                wait_times.append(wait_for_tokens)

        # If we're over request limit, wait until oldest request expires
        if requests_made >= self.requests_per_minute:
            if self.request_timestamps:
                oldest_request_time = self.request_timestamps[0]
                wait_for_requests = (oldest_request_time - minute_ago).total_seconds() + 1
                wait_times.append(wait_for_requests)

        # Wait for the longer of the two
        return max(wait_times) if wait_times else 0.1

    def get_current_usage(self) -> Tuple[int, int]:
        """Get current rate limit usage.

        Returns:
            Tuple of (tokens_used_last_minute, requests_made_last_minute)
        """
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean up old timestamps
        while self.token_timestamps and self.token_timestamps[0][0] < minute_ago:
            self.token_timestamps.popleft()
        while self.request_timestamps and self.request_timestamps[0] < minute_ago:
            self.request_timestamps.popleft()

        tokens_used = sum(t[1] for t in self.token_timestamps)
        requests_made = len(self.request_timestamps)

        return tokens_used, requests_made

    def reset(self) -> None:
        """Reset rate limiter (for testing or new session)."""
        self.token_timestamps.clear()
        self.request_timestamps.clear()
