"""Hang guard for tests/worlds (SIGALRM, POSIX main thread) plus the shared fixtures.

An implementation with an infinite loop must FAIL a test, not freeze the suite. The real-world fixtures are
session-scoped: the corpus is decoded once and the (slow) graph indexes are built once.
"""
import json
import signal
from pathlib import Path

import pytest

LIMIT_SECONDS = 240
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "worlds"


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


@pytest.fixture(scope="session")
def real_world():
    from dsdk.worlds import load_lostlands

    return load_lostlands()


@pytest.fixture(scope="session")
def slices():
    """fixtures/worlds/lostlands_slices.json: written by the independent script fixtures/worlds/gen_slices.py."""
    return json.loads((FIXTURES / "lostlands_slices.json").read_text("utf-8"))


@pytest.fixture(scope="session")
def real_degrees(real_world):
    from dsdk.worlds import SixDegrees

    return SixDegrees(real_world)
