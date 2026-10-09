"""Probability questions asked as TEXT: the language package feeds the probability package (tracks A2 -> A3).

A question is two strings in the RELAXED formula syntax of ``dsdk.lang.parse_formula`` (``~`` binds tightest, then ``&``, ``|``, ``->``
right-associative, ``<->``; redundant parentheses allowed; ``true``/``false`` are constants)::

    ask(belief, "P22 | P31")                       # P(P22 or P31)
    ask(belief, "P22", "B21 & ~B11")               # P(P22 | B21 and not B11)

The text is parsed by ``dsdk.lang.parse_formula(text, relaxed=True)`` into a ``dsdk.logic.Formula`` and then answered by the exact
functions of ``dsdk.prob.worlds``. Every function here returns a ``dsdk.core.Judgment`` and follows the package convention: it never
raises for a problem with the user's TEXT or with the question's meaning, only ``TypeError`` for an argument of the wrong Python type.

Text that cannot be parsed is INVALID, never a guess
----------------------------------------------------
A ``LexError`` or ``ParseError`` from the language package becomes ``Judgment(Status.INVALID, None, reason)`` where ``reason`` is exactly::

    "unparseable " + role + ": " + str(error)  [+ "; expected one of: " + ", ".join(sorted(error.expected))]

``role`` is ``"query text"`` or ``"evidence text"``; ``str(error)`` is the language package's own message and ends with
``(at offset N)``, so the 0-based offset of the first offending character or token is in the reason; the ``expected`` suffix is added only
for a ``ParseError`` whose ``expected`` set is non-empty. The query text is parsed first: when both texts are bad the reason is about the
query. An empty or whitespace-only text is a parse error at offset 0 (empty) or at ``len(text)`` (whitespace only), so INVALID too.
This INVALID is told apart from "impossible evidence" by its reason starting with ``"unparseable"``.
"""
from __future__ import annotations

from dsdk.core import Judgment, PxC, Status
from dsdk.lang import LangError, ParseError, parse_formula
from dsdk.logic import Formula

from .bayesnet import BayesNet, joint_belief
from .sampling import compare_with_exact
from .updates import observe
from .worlds import Belief, probability


def parse_text(text: str, role: str = "query text") -> Judgment:
    """Parse relaxed formula text: ``KNOWN`` with the ``Formula`` as value, or ``INVALID`` with the reason described in the module docstring.

    ``TypeError`` if ``text`` is not a ``str`` (a Python type error, not a text error). ``role`` is only used in the reason.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, not {type(text).__name__}")
    try:
        formula = parse_formula(text, relaxed=True)
    except LangError as exc:
        reason = f"unparseable {role}: {exc}"
        if isinstance(exc, ParseError) and exc.expected:
            reason += "; expected one of: " + ", ".join(sorted(exc.expected))
        return Judgment(Status.INVALID, None, reason)
    return Judgment(Status.KNOWN, formula, "")


def _parse_pair(query_text: str, given_text: str | None) -> tuple[Formula | None, Formula | None, Judgment | None]:
    """(query, given, failure). ``failure`` is the INVALID Judgment of the first text that does not parse (query first), else None."""
    if not isinstance(query_text, str):
        raise TypeError(f"query text must be a str, not {type(query_text).__name__}")
    if given_text is not None and not isinstance(given_text, str):
        raise TypeError(f"evidence text must be a str or None, not {type(given_text).__name__}")
    q = parse_text(query_text, "query text")
    if q.status is not Status.KNOWN:
        return None, None, q
    if given_text is None:
        return q.value, None, None
    g = parse_text(given_text, "evidence text")
    if g.status is not Status.KNOWN:
        return None, None, g
    return q.value, g.value, None


def ask(belief: Belief, query_text: str, given_text: str | None = None) -> Judgment:
    """Exact ``P(query)`` or ``P(query | given)`` for questions written as text.

    ``TypeError`` for a non-Belief, or texts that are not ``str`` (``given_text`` may be ``None``). Parse failures give the INVALID
    Judgment described in the module docstring (query text checked first). Otherwise the answer is exactly
    ``probability(belief, query, given)`` for the parsed formulas: KNOWN ``Fraction``, UNKNOWN for variables the belief does not model,
    INVALID (reason mentions "probability zero" or "zero total weight") for impossible evidence.
    """
    if not isinstance(belief, Belief):
        raise TypeError(f"belief must be a Belief, not {type(belief).__name__}")
    query, given, failure = _parse_pair(query_text, given_text)
    if failure is not None:
        return failure
    return probability(belief, query, given)


def ask_net(net: BayesNet, query_text: str, given_text: str | None = None) -> Judgment:
    """Like :func:`ask` on the exact joint distribution of a Bayes net (``joint_belief(net)``), so the variables are the net's node names.

    ``TypeError`` for a non-BayesNet. A net with more than ``MAX_VARIABLES`` nodes gives ``INVALID`` with a reason starting
    ``"cannot enumerate"`` (the ``ValueError`` of ``joint_belief`` is reported as a Judgment because the user's question cannot be answered
    exactly; the texts are still parsed first so a parse error takes priority).
    """
    if not isinstance(net, BayesNet):
        raise TypeError(f"net must be a BayesNet, not {type(net).__name__}")
    query, given, failure = _parse_pair(query_text, given_text)
    if failure is not None:
        return failure
    try:
        belief = joint_belief(net)
    except ValueError as exc:
        return Judgment(Status.INVALID, None, f"cannot enumerate this network: {exc}")
    return probability(belief, query, given)


def compare_text(belief: Belief, query_text: str, n: int, seed: int, given_text: str | None = None) -> Judgment:
    """Exact answer next to the seeded sampled estimate, for text questions: parse both texts (failures as in :func:`ask`), then
    ``compare_with_exact(belief, query, n, seed, given)`` unchanged (KNOWN ``Comparison``, or its INVALID/UNKNOWN verdicts).
    Argument errors for ``n``/``seed`` raise as in ``compare_with_exact`` but only after the texts parsed."""
    if not isinstance(belief, Belief):
        raise TypeError(f"belief must be a Belief, not {type(belief).__name__}")
    query, given, failure = _parse_pair(query_text, given_text)
    if failure is not None:
        return failure
    return compare_with_exact(belief, query, n, seed, given)


def observe_text(store: PxC, name: str, evidence_text: str) -> Judgment:
    """Record an observation written as text in a belief series (see ``dsdk.prob.updates``): parse ``evidence_text``, then
    ``observe(store, name, formula)``. A text that does not parse is INVALID (reason as in :func:`parse_text` with role
    ``"evidence text"``) and the store is NOT touched (no Part, no receipt). Everything else is ``observe``'s verdict unchanged.
    ``TypeError`` for non-str text; the store/name errors of ``observe`` are raised only after the text parsed."""
    if not isinstance(evidence_text, str):
        raise TypeError(f"evidence text must be a str, not {type(evidence_text).__name__}")
    parsed = parse_text(evidence_text, "evidence text")
    if parsed.status is not Status.KNOWN:
        return parsed
    return observe(store, name, parsed.value)
