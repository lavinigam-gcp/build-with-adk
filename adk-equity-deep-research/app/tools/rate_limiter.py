# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Rate limiting utilities for external API calls (yfinance, etc.)."""

import time
from collections import deque
from threading import Lock, Semaphore


class RateLimiter:
    """Simple sliding window rate limiter for API requests.

    Uses a sliding window algorithm to enforce rate limits. Thread-safe.

    Example:
        limiter = RateLimiter(max_requests=30, window_seconds=60)

        def make_api_call():
            limiter.acquire()  # Blocks if rate limit exceeded
            return api.call()
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: deque = deque()
        self.lock = Lock()

    def acquire(self) -> None:
        """Block until a request slot is available.

        Thread-safe. Will sleep if rate limit is exceeded, then retry.
        """
        with self.lock:
            now = time.time()

            # Remove old requests outside the current window
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()

            if len(self.requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                sleep_time = self.window - (now - self.requests[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # Recursive retry after sleeping
                return self.acquire()

            # Record this request
            self.requests.append(now)

    def try_acquire(self) -> bool:
        """Attempt to acquire a slot without blocking.

        Returns:
            True if slot acquired, False if rate limited
        """
        with self.lock:
            now = time.time()

            # Remove old requests
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()

            if len(self.requests) >= self.max_requests:
                return False

            self.requests.append(now)
            return True

    def get_remaining(self) -> int:
        """Get remaining request slots in current window.

        Returns:
            Number of remaining requests allowed
        """
        with self.lock:
            now = time.time()

            # Remove old requests
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()

            return max(0, self.max_requests - len(self.requests))


# =============================================================================
# Global Rate Limiters
# =============================================================================

# yfinance rate limiter: 30 requests per minute (conservative)
# Yahoo Finance has no official rate limits but can throttle aggressive usage
YFINANCE_RATE_LIMITER = RateLimiter(max_requests=30, window_seconds=60)

# Semaphore to limit concurrent yfinance requests
# Prevents overwhelming the API when 4 fetchers run in parallel
YFINANCE_SEMAPHORE = Semaphore(2)  # Max 2 concurrent requests
