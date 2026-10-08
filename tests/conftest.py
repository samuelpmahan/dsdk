"""Shared pytest/Hypothesis settings: deterministic, no wall-clock flakiness."""
from hypothesis import settings

settings.register_profile("dsdk", max_examples=100, deadline=None, derandomize=True)
settings.load_profile("dsdk")
