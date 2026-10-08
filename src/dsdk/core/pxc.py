"""PxC: a write-once store of immutable Parts, composed by registered calculations.

Based on the owner's NEWER part-first kernel (pxcube main, 2026-09-28,
``vendor/studio/part-first-kernel/src/pxc.mjs``), NOT the older Wumpus
``pxc.js`` (2026-09-05). The older design had mutable slots + transactions; the
newer one has write-once Parts + receipts. Differences from the JS kernel are
marked DEVIATION.

Concepts
--------
Part         Immutable value wrapper. ``Part(v)`` has ``composition is None``.
             A Part produced by ``compose`` carries a :class:`Composition`
             (the calculation Part and the NAMED input Parts), so lineage is a
             DAG of Parts that track A5 (graphs) can traverse via
             ``part.composition.inputs`` / ``part.composition.calculation``.
Address      ``str`` of the form ``<namespace>.<rest>`` with namespace one of
             ``px`` (values), ``fn`` (calculations), ``sc`` (scratch) and a
             non-empty ``rest``. Non-``str`` -> ``TypeError``; any other string
             (``""``, ``"px."``, ``"x.a"``, ``"PX.a"``) -> ``ValueError``.
             What is enforced: the prefix, and ONE namespace rule: every Part
             bound at an ``fn.*`` address must hold a callable (else
             ``TypeError``, address stays free). NOT enforced (advisory only):
             ``px.*``/``sc.*`` may hold any value, even callables; ``sc.*`` is
             write-once like everything else (DEVIATION: JS has no namespaces).
Write-once   An address, once bound, is bound forever. ``set``/``compose`` into
             an occupied address raises :class:`AddressOccupiedError`. There is
             no replacement and no deletion. An address is also "occupied"
             while a compose into it is in flight (a calculation that
             re-enters the store to write its own ``into`` gets the error).
Capture      Values are deep-copied when a Part is created and again on every
             ``Part.value`` access, so nobody can mutate stored state through a
             reference. EXCEPTION: a value for which ``callable(value)`` is true
             is stored and returned BY REFERENCE (never copied), so a callable
             object with internal state (a counter, a spy, a closure) keeps its
             identity -- a calculation is behaviour, not data. Inputs handed to a calculation are fresh copies too.
             An uncopyable value (``threading.Lock``) makes ``Part(...)``
             raise the ``TypeError`` from ``copy.deepcopy``.
Compose      Synchronous (DEVIATION: JS is ``async``). See :meth:`PxC.compose`.
Tick         A minimal atomic group of composes (DEVIATION/addition: the JS
             kernel dropped transactions). KEPT because a Wumpus belief update
             is several dependent composes (percept -> constraints -> weights ->
             posterior) that must not leave a half-updated belief. The cost is
             small: write-once means rollback is just "do not bind", no undo
             log. See :meth:`PxC.tick`.
"""
from __future__ import annotations

import collections.abc
import copy
import re
from contextlib import AbstractContextManager
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Union


class PxCError(Exception):
    """Base class for store-state errors."""


class AddressOccupiedError(PxCError):
    """The address is bound, or a compose into it is in flight/staged."""


class MissingPartError(PxCError, KeyError):
    """A string reference / ``get`` named an address that is not bound."""


class TickInProgressError(PxCError):
    """``set``/``compose``/``tick`` on the store while a tick is open, or use of
    a tick scope after it exited."""


class Part:
    """An immutable value wrapper with optional lineage.

    * ``Part(value)``: deep-copies ``value``; ``composition`` is ``None``.
    * ``part.value``: a NEW deep copy on every access (mutating it never changes
      the Part). Callables (``callable(value)``) are NOT copied: ``Part(f).value
      is f``.
    * ``part.composition``: ``None`` or the :class:`Composition` that made it.
    * Immutable: assigning ANY attribute raises ``AttributeError``.
    * Equality/hash are by IDENTITY: ``Part(1) != Part(1)``. (Lineage graphs
      need identity; compare ``.value`` for value equality.)
    Only :class:`PxC` creates Parts that have a composition.
    """

    __slots__ = ("_value", "_composition")

    def __init__(self, value: Any) -> None:
        object.__setattr__(self, "_value", _capture(value))
        object.__setattr__(self, "_composition", None)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"Part is immutable; cannot set {name!r}")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"Part is immutable; cannot delete {name!r}")

    @property
    def value(self) -> Any:
        return _capture(self._value)

    @property
    def composition(self) -> "Composition | None":
        return self._composition


@dataclass(frozen=True)
class Composition:
    """How a Part was made. ``calculation`` is the function-valued Part that
    was run; ``inputs`` is a READ-ONLY mapping (``types.MappingProxyType``;
    item assignment raises ``TypeError``) from input name to the very Part
    objects used (identity preserved, in the order the caller gave them)."""

    calculation: Part
    inputs: Mapping[str, Part]


class ReceiptStatus(Enum):
    PRODUCED = "produced"
    FAILED = "failed"


@dataclass(frozen=True)
class Receipt:
    """Immutable record of one compose attempt that passed preflight.

    * ``status``      PRODUCED or FAILED.
    * ``into``        the target address.
    * ``composition`` the Composition (resolved Parts) that was/would be run.
    * ``output``      the produced Part (the very object bound at ``into``) if
                      PRODUCED, else ``None``.
    * ``error``       ``None`` if PRODUCED, else the exception object.
    * ``tick``        the tick id if the compose was made inside a tick, else
                      ``None``.
    Preflight failures (bad address, occupied, missing reference, non-callable
    calculation, bad inputs) raise WITHOUT a receipt: nothing was attempted.
    """

    status: ReceiptStatus
    into: str
    composition: Composition
    output: Part | None
    error: BaseException | None
    tick: str | None = None


Reference = Union[str, Part]


class TickScope:
    """What ``with store.tick(id) as tx`` yields. Valid only inside the block;
    afterwards every method raises ``TickInProgressError``.

    * ``compose(into, calculation, inputs=None)`` -- same signature, preflight
      and return value as :meth:`PxC.compose`, except the produced Part is only
      STAGED: it is visible to ``tx.get``/``tx.has`` (so later composes in the
      same tick can read it by address string) and its address is occupied for
      this tick, but nothing is bound in the store until the block exits
      normally.
    * ``get(address) -> Part`` / ``has(address) -> bool`` -- committed bindings
      plus this tick's staged ones.
    """

    def compose(
        self, into: str, calculation: Reference, inputs: Mapping[str, Reference] | None = None
    ) -> Part:
        raise NotImplementedError

    def get(self, address: str) -> Part:
        raise NotImplementedError

    def has(self, address: str) -> bool:
        raise NotImplementedError


_ADDRESS = re.compile(r"(?:px|fn|sc)\..+")


def _capture(value: Any) -> Any:
    """Callables are kept by reference; everything else is deep-copied."""
    if callable(value):
        return value
    return copy.deepcopy(value)


def _check_address(address: Any) -> None:
    """TypeError for non-str; ValueError unless ``<px|fn|sc>.<non-empty>``.
    ``fullmatch`` (not ``$``) so a trailing newline is rejected."""
    if not isinstance(address, str):
        raise TypeError(f"address must be str, not {type(address).__name__}")
    if _ADDRESS.fullmatch(address) is None:
        raise ValueError(f"malformed address {address!r}: expected '<px|fn|sc>.<name>'")


def _lineage_part(value: Any, composition: Composition) -> Part:
    """Build a composed Part. Only the store uses this (the public ``Part(value)``
    signature stays unchanged)."""
    part = Part(value)
    object.__setattr__(part, "_composition", composition)
    return part


class PxC:
    """The store. See the module docstring for the shared rules."""

    def __init__(self) -> None:
        self._bindings: dict[str, Part] = {}
        self._receipts: list[Receipt] = []
        self._in_flight: set[str] = set()
        self._tick_open = False  # set by the tick machinery (T03); always False until then

    def set(self, address: str, part: Part) -> Part:
        """Bind an existing :class:`Part` (not a raw value: ``TypeError``) at a
        free address and return it (the same object). No receipt is recorded.
        Order of checks: tick open (``TickInProgressError``), address validity,
        ``part`` type, ``fn.*`` callable rule, occupied."""
        self._check_no_tick()
        _check_address(address)
        if not isinstance(part, Part):
            raise TypeError(f"set() takes a Part, not {type(part).__name__}")
        if address.startswith("fn.") and not callable(part._value):
            raise TypeError(f"{address!r} is an fn.* address and must hold a callable")
        if self._is_occupied(address):
            raise AddressOccupiedError(f"address {address!r} is already bound")
        self._bindings[address] = part
        return part

    def get(self, address: str) -> Part:
        """The bound Part (the same object every time). ``MissingPartError``
        if unbound; address validity rules apply."""
        _check_address(address)
        if address not in self._bindings:
            raise MissingPartError(f"no Part bound at {address!r}")
        return self._bindings[address]

    def has(self, address: str) -> bool:
        """True iff bound (in-flight/staged addresses are not bound yet)."""
        _check_address(address)
        return address in self._bindings

    def entries(self) -> tuple[tuple[str, Part], ...]:
        """All bindings as ``(address, part)`` in BINDING order (the order in
        which they were successfully set/composed; a tick's bindings appear in
        its compose order). Committed state only. Immutable snapshot."""
        return tuple(self._bindings.items())

    def receipts(self) -> tuple[Receipt, ...]:
        """All receipts in the order recorded, as an immutable snapshot. A
        tick's receipts are recorded together when the tick exits, in the
        order the composes were attempted; none are visible while it is open."""
        return tuple(self._receipts)

    def compose(
        self, into: str, calculation: Reference, inputs: Mapping[str, Reference] | None = None
    ) -> Part:
        """Run ``calculation`` on ``inputs`` and bind the result at ``into``.

        ``calculation`` is a function-valued Part, or a string address of one.
        ``inputs`` maps names to Parts or string addresses (``None`` = ``{}``).

        PREFLIGHT -- all checked BEFORE anything runs, in this order; any
        failure raises and records no receipt, and ``into`` stays free:
          0. ``TickInProgressError`` if a tick is open.
          1. ``into``: address validity (TypeError/ValueError), then
             ``AddressOccupiedError``.
          2. ``calculation``: str -> resolved with ``get`` (``MissingPartError``);
             otherwise must be a Part (``TypeError``); its value must be
             callable (``TypeError``).
          3. ``inputs``: must be a ``Mapping`` (``TypeError``) with non-empty
             ``str`` names (``TypeError``); each reference resolved like the
             calculation (``MissingPartError`` / ``TypeError`` for non-Part,
             non-str).
        EXECUTION: ``fn(values)`` is called exactly once with ONE positional
        argument, a new ``dict`` ``{name: part.value}`` in the caller's order.
        The result is wrapped in a new Part carrying the Composition. If
        ``into`` is ``fn.*`` the result must be callable (``TypeError``).
        If anything in execution raises (the calculation, copying its output,
        the ``fn.*`` rule): a FAILED receipt is recorded, ``into`` stays free,
        and the SAME exception object is re-raised. On success: bind, record a
        PRODUCED receipt, return the Part.
        """
        self._check_no_tick()
        _check_address(into)
        if self._is_occupied(into):
            raise AddressOccupiedError(f"address {into!r} is already bound or in flight")
        calc = self._resolve_calculation(calculation)
        input_parts = self._resolve_inputs(inputs)
        receipt = self._attempt(into, calc, input_parts)
        self._receipts.append(receipt)
        if receipt.status is ReceiptStatus.FAILED:
            raise receipt.error  # type: ignore[misc]  # the same exception object
        self._bindings[into] = receipt.output  # type: ignore[assignment]
        return receipt.output  # type: ignore[return-value]

    # ---- shared internals (compose now; TickScope.compose reuses them in T03) ----

    def _check_no_tick(self) -> None:
        if self._tick_open:
            raise TickInProgressError("a tick is open; use its scope instead")

    def _is_occupied(self, address: str) -> bool:
        """Bound, or reserved by a compose currently running into it."""
        return address in self._bindings or address in self._in_flight

    def _resolve_calculation(self, calculation: Reference) -> Part:
        """Preflight step 2: resolve to a Part whose value is callable."""
        if isinstance(calculation, str):
            calc = self.get(calculation)
        elif isinstance(calculation, Part):
            calc = calculation
        else:
            raise TypeError(f"calculation must be a Part or address, not {type(calculation).__name__}")
        if not callable(calc._value):
            raise TypeError("calculation Part must hold a callable")
        return calc

    def _resolve_inputs(self, inputs: Mapping[str, Reference] | None) -> dict[str, Part]:
        """Preflight step 3: a mapping of non-empty str names to Parts/addresses.
        Returns a NEW dict in the caller's order."""
        if inputs is None:
            return {}
        if not isinstance(inputs, collections.abc.Mapping):
            raise TypeError(f"inputs must be a Mapping, not {type(inputs).__name__}")
        resolved: dict[str, Part] = {}
        for name, ref in inputs.items():
            if not isinstance(name, str) or not name:
                raise TypeError(f"input names must be non-empty str, not {name!r}")
            if isinstance(ref, str):
                part = self.get(ref)
            elif isinstance(ref, Part):
                part = ref
            else:
                raise TypeError(f"input {name!r} must be a Part or address, not {type(ref).__name__}")
            resolved[name] = part
        return resolved

    def _attempt(
        self, into: str, calc: Part, input_parts: Mapping[str, Part], tick: str | None = None
    ) -> Receipt:
        """Run one compose that has already passed preflight. ``into`` is reserved
        (in flight) while the calculation runs. Calculation or output failures are
        NOT raised: they come back as a FAILED Receipt holding the exception, and
        the caller decides whether to re-raise or roll back. A PRODUCED receipt's
        output is returned UNBOUND; the caller binds it."""
        composition = Composition(calculation=calc, inputs=MappingProxyType(dict(input_parts)))
        self._in_flight.add(into)
        try:
            values = {name: part.value for name, part in input_parts.items()}
            result = calc.value(values)
            if into.startswith("fn.") and not callable(result):
                raise TypeError(f"{into!r} is an fn.* address and its output must be callable")
            output = _lineage_part(result, composition)
        except BaseException as exc:
            return Receipt(ReceiptStatus.FAILED, into, composition, None, exc, tick)
        finally:
            self._in_flight.discard(into)
        return Receipt(ReceiptStatus.PRODUCED, into, composition, output, None, tick)

    def tick(self, id: str) -> AbstractContextManager[TickScope]:
        """Open an atomic group of composes: ``with store.tick("t") as tx:``.

        ``id`` must be a non-empty ``str`` (``TypeError`` / ``ValueError``,
        raised when the ``with`` is entered, leaving the store usable).
        ``TickInProgressError`` if a tick is already open. While open, the
        store's ``set``/``compose``/``tick`` raise ``TickInProgressError``;
        its ``get``/``has``/``entries``/``receipts`` work and show committed
        state only.

        Normal exit: all staged Parts are bound atomically (in compose order)
        and one PRODUCED receipt per successful compose is recorded.
        Exception leaving the block (any ``BaseException``): NOTHING is bound,
        and every compose attempted in the tick gets a FAILED receipt -- the
        one whose calculation raised keeps its own error; the ones that had
        succeeded (now discarded) carry the exception that left the block as
        ``error``, ``output=None``. The exception is re-raised unchanged.
        A compose failure that the block CATCHES does not abort the tick: its
        FAILED receipt (own error) is still recorded, in attempt order,
        between the PRODUCED ones when the tick commits. Preflight failures
        inside the tick raise without a receipt, like outside.
        Every receipt of a tick has ``tick == id``.
        """
        raise NotImplementedError
