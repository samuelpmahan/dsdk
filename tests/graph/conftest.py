"""Hang guard for tests/graph: an implementation with an infinite loop must FAIL a test, not freeze the suite.

Uses SIGALRM (POSIX, main thread). Where it is unavailable the guard silently does nothing.
"""
import signal

import pytest

LIMIT_SECONDS = 30


@pytest.fixture(autouse=True)
def _hang_guard():
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def on_alarm(signum, frame):
        raise TimeoutError(f"test exceeded {LIMIT_SECONDS}s: probably an infinite loop in the implementation")

    previous = signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(LIMIT_SECONDS)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
