import threading
import time
from collections.abc import Callable


class RateLimiter:
    """Spaces request starts evenly so at most ``requests_per_minute`` start per minute.

    Thread-safe; shared by all requests of the process for one provider/model, because
    vendor quotas (e.g. Gemini's free tier) are per project and model, not per HTTP request.
    """

    def __init__(
        self,
        requests_per_minute: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self.interval = 60.0 / requests_per_minute
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def acquire(self) -> None:
        """Block until the caller may start a request."""
        with self._lock:
            now = self._clock()
            start = max(now, self._next_slot)
            self._next_slot = start + self.interval
        if start > now:
            self._sleep(start - now)
