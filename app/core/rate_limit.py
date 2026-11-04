import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Small in-process login limiter.

    This is intentionally dependency-free and suitable for a single-process
    deployment. For multi-worker production deployments, back it with Redis.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> int | None:
        """Return None when allowed, otherwise seconds until retry is allowed."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._attempts[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_attempts:
                return max(1, int(self.window_seconds - (now - bucket[0])) + 1)
        return None

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._attempts[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


class LoginRateLimiter:
    def __init__(self) -> None:
        self._limiter: SlidingWindowRateLimiter | None = None
        self._config: tuple[int, int] | None = None
        self._lock = threading.Lock()

    def _get(self, max_attempts: int, window_seconds: int) -> SlidingWindowRateLimiter:
        with self._lock:
            config = (max_attempts, window_seconds)
            if self._limiter is None or self._config != config:
                self._limiter = SlidingWindowRateLimiter(max_attempts, window_seconds)
                self._config = config
            return self._limiter

    def check(self, key: str, max_attempts: int, window_seconds: int) -> int | None:
        return self._get(max_attempts, window_seconds).check(key)

    def record_failure(self, key: str, max_attempts: int, window_seconds: int) -> None:
        self._get(max_attempts, window_seconds).record_failure(key)

    def reset(self, key: str, max_attempts: int, window_seconds: int) -> None:
        self._get(max_attempts, window_seconds).reset(key)

    def clear(self) -> None:
        with self._lock:
            if self._limiter is not None:
                self._limiter.clear()


login_limiter = LoginRateLimiter()
password_reset_limiter = LoginRateLimiter()
