"""dsdk.worlds (track W1): the datasets dsdk studies, as typed records and evidence-labelled graphs.

Builds on dsdk.core (Part/PxC record provenance; Judgment/Status keep "unknown", "not observed" and "invalid"
apart) and dsdk.graph (every world is turned into :class:`dsdk.graph.Graph` objects whose edges carry evidence).

Worlds
------
* ``lostlands`` / ``networks``  Sam's Lost Lands 2018 DJ-set corpus: loader, provenance, graphs, "six degrees".
* ``buildlog``                  ``ops/ledger.jsonl``: dsdk studying the agents that build it.
* Wumpus world                  DEFERRED (W1 note, 2026-10-09): ``fixtures/logic/wumpus_kb.json`` is already
                                consumed by dsdk.logic and A3 will weight it; a ``dsdk.worlds.wumpus`` module that
                                loads the JS world is a later card.

Read ``lostlands.py`` first (file format and epistemic stance), then ``networks.py`` (evidence vocabulary).
"""
from .buildlog import OUTCOMES, LEDGER_PATH, LedgerEntry, LedgerError, first_try_rate, load_ledger, models, parse_ledger
from .lostlands import (
    FIXTURE_PATH,
    PINNED_SHA256,
    SCHEMA,
    SOURCE_BRANCH,
    SOURCE_COMMIT,
    SOURCE_REPO,
    Artist,
    IntegrityError,
    LostLands,
    SelectorGroup,
    Selection,
    Track,
    Transition,
    WorldError,
    check_transitions,
    describe_provenance,
    load_lostlands,
    parse_lostlands,
    record_provenance,
    sha256_bytes,
)
from .networks import (
    COSELECTION_LABEL,
    DJ_MODES,
    TRANSITION_LABEL,
    Degrees,
    Hop,
    SixDegrees,
    coselection_graph,
    dj_graph,
    six_degrees,
    six_degrees_graph,
    transition_graph,
)

__all__ = [
    "Artist", "COSELECTION_LABEL", "DJ_MODES", "Degrees", "FIXTURE_PATH", "Hop", "IntegrityError", "LEDGER_PATH",
    "LedgerEntry", "LedgerError", "LostLands", "OUTCOMES", "PINNED_SHA256", "SCHEMA", "SOURCE_BRANCH",
    "SOURCE_COMMIT", "SOURCE_REPO", "SelectorGroup", "Selection", "SixDegrees", "TRANSITION_LABEL", "Track",
    "Transition", "WorldError", "check_transitions", "coselection_graph", "describe_provenance", "dj_graph",
    "first_try_rate", "load_ledger", "load_lostlands", "models", "parse_ledger", "parse_lostlands",
    "record_provenance", "sha256_bytes", "six_degrees", "six_degrees_graph", "transition_graph",
]
