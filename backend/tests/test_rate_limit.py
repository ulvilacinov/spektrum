import threading

import pytest

from app.services.ai.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


def test_spaces_requests_evenly() -> None:
    clock = FakeClock()
    limiter = RateLimiter(5, clock=clock, sleep=clock.sleep)

    for _ in range(3):
        limiter.acquire()

    assert clock.sleeps == [12.0, 24.0]


def test_no_wait_after_idle_time() -> None:
    clock = FakeClock()
    limiter = RateLimiter(60, clock=clock, sleep=clock.sleep)
    limiter.acquire()
    clock.now += 5

    limiter.acquire()

    assert clock.sleeps == []


def test_concurrent_callers_get_distinct_slots() -> None:
    clock = FakeClock()
    limiter = RateLimiter(6, clock=clock, sleep=clock.sleep)
    threads = [threading.Thread(target=limiter.acquire) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(clock.sleeps) == [10.0, 20.0, 30.0]


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError):
        RateLimiter(0)
