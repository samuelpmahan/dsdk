"""The real diagonal rule: packages must CALL earlier work and be CALLED by later work.

test_reuse.py checks imports, which our own contracts satisfied while barely using
each other. These tests count actual call sites (tools/evidence/stack.py).
A package that nothing later calls must name, in tracks.toml, the package that owes
it a consumer (`owed_to`); that is recorded as an expected failure, and the test turns
red (strict xfail) the moment the debt is paid so the waiver gets removed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "evidence"))
import stack  # noqa: E402

SUMMARY = {e["package"]: e for e in stack.summary()["packages"]}
ORDERED = sorted(SUMMARY, key=lambda p: SUMMARY[p]["order"])
LAST = ORDERED[-1]
MIN_CALLED = 3  # distinct earlier functions/classes a package must actually call


def _thin_params():
    reg = stack.registry()
    out = []
    for p in ORDERED:
        if SUMMARY[p]["order"] == 0:
            continue
        why = reg[p].get("thin_owed", "")
        marks = [pytest.mark.xfail(strict=True, reason=why)] if why else []
        out.append(pytest.param(p, marks=marks, id=p))
    return out


@pytest.mark.parametrize("package", _thin_params())
def test_package_calls_enough_earlier_functions(package):
    """Each package past the kernel calls at least three distinct earlier functions, so it stands on earlier work rather than just importing it."""
    called = sum(len(v) for v in SUMMARY[package]["calls"].values())
    assert called >= MIN_CALLED, f"{package} calls only {called} earlier functions: {SUMMARY[package]['calls']}"


def _consumed_params():
    out = []
    for p in ORDERED:
        if p == LAST:
            continue
        owed = SUMMARY[p]["owed_to"]
        marks = [pytest.mark.xfail(strict=True, reason=f"nothing calls {p} yet; owed to {owed}")] if owed else []
        out.append(pytest.param(p, marks=marks, id=p))
    return out


@pytest.mark.parametrize("package", _consumed_params())
def test_package_is_called_by_later_work(package):
    """Every package except the newest is actually called by some later package; a package nobody uses is building wide, not up."""
    assert SUMMARY[package]["used_by"], f"no later package calls {package}"
