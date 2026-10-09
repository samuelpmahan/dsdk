"""dsdk.worlds (track W1): the datasets dsdk studies, as typed records and evidence-labelled graphs.

Builds on dsdk.core (Part/PxC record provenance; Judgment/Status keep "unknown", "not observed" and "invalid"
apart) and dsdk.graph (every world is turned into :class:`dsdk.graph.Graph` objects whose edges carry evidence).

Worlds
------
* ``lostlands`` / ``networks``  Sam's Lost Lands 2018 DJ-set corpus: loader, provenance, graphs, "six degrees".
* ``buildlog``                  ``ops/ledger.jsonl``: dsdk studying the agents that build it.
* ``wumpus``                    the Logic Cave: caves identical to the Lab page's, the logic-only agent, and the probability
                                rung (exact P(pit) and P(Wumpus) per frontier square, asked as text of dsdk.prob).

Read ``lostlands.py`` first (file format and epistemic stance), then ``networks.py`` (evidence vocabulary).
"""
from .buildlog import (
    LEDGER_PATH, OUTCOMES, FirstTry, LedgerEntry, LedgerError, RoundStats, first_try_rate, first_try_summary, load_ledger, models,
    parse_ledger, round_throughput,
)
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
    next_track_model,
    six_degrees,
    six_degrees_graph,
    transition_graph,
)

__all__ = [
    "Artist", "COSELECTION_LABEL", "DJ_MODES", "Degrees", "FIXTURE_PATH", "Hop", "IntegrityError", "LEDGER_PATH",
    "LedgerEntry", "LedgerError", "LostLands", "OUTCOMES", "PINNED_SHA256", "SCHEMA", "SOURCE_BRANCH",
    "SOURCE_COMMIT", "SOURCE_REPO", "SelectorGroup", "Selection", "SixDegrees", "TRANSITION_LABEL", "Track",
    "Transition", "WorldError", "check_transitions", "coselection_graph", "describe_provenance", "dj_graph",
    "first_try_rate", "first_try_summary", "FirstTry", "RoundStats", "round_throughput", "load_ledger", "next_track_model", "load_lostlands", "models", "parse_ledger", "parse_lostlands",
    "record_provenance", "sha256_bytes", "six_degrees", "six_degrees_graph", "transition_graph",
]
