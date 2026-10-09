"""dsdk.prob (track A3): exact and sampled probability over possible worlds, belief updates with lineage, Bayes nets, next-track model.

Builds on four earlier tracks:

* dsdk.logic  -- possible worlds ARE ``logic.models``; evidence and queries are ``logic.Formula``;
* dsdk.core   -- answers are ``Judgment`` (INVALID for impossible evidence, UNKNOWN when the belief cannot answer) and
                 belief updates are PxC ``tick``s, so every update leaves lineage;
* dsdk.lang   -- questions and evidence can be written as text (``ask``): ``parse_formula`` turns them into logic formulas;
* dsdk.graph  -- a Bayes-net structure is a ``Graph`` DAG (cycle check, ancestors by BFS, forward sampling in topological order);
                 the next-track model reads a weighted transition ``Graph``.

Start with ``worlds.py`` (conventions), then ``bayesnet.py``, ``sampling.py``, ``updates.py``, ``transitions.py``.
"""
from .ask import ask, ask_net, compare_text, observe_text, parse_text
from .bayesnet import BayesNet, ancestors, ancestral_net, bayes_net, joint_belief
from .exact import to_prob, to_weight
from .sampling import (
    Comparison,
    Estimate,
    Z95,
    compare_with_exact,
    exact_interval,
    estimate_probability,
    forward_sample,
    inverse_cdf_draws,
    make_comparison,
    make_estimate,
    sample_worlds,
    standard_error,
    wilson_interval,
)
from .transitions import (
    NextTrackModel,
    compare_next_track,
    fit_next_track,
    held_out_log_loss,
    model_from_graph,
    next_track_distribution,
    sample_next_tracks,
    top_next,
)
from .updates import belief_history, current_belief, observe, start_series
from .worlds import (
    MAX_VARIABLES,
    Belief,
    UnmodelledVariableError,
    WeightedWorld,
    condition,
    marginals,
    normalise,
    prior_belief,
    probability,
    reweight,
)

__all__ = [
    "ask", "ask_net", "compare_text", "observe_text", "parse_text",
    "Belief", "BayesNet", "Comparison", "Estimate", "MAX_VARIABLES", "NextTrackModel", "UnmodelledVariableError",
    "WeightedWorld", "Z95", "ancestors", "ancestral_net", "bayes_net", "belief_history", "compare_next_track",
    "compare_with_exact", "exact_interval", "condition", "current_belief", "estimate_probability", "fit_next_track", "forward_sample",
    "held_out_log_loss", "inverse_cdf_draws", "joint_belief", "make_comparison", "make_estimate", "marginals",
    "model_from_graph", "next_track_distribution", "normalise", "observe", "prior_belief", "probability", "reweight",
    "sample_next_tracks", "sample_worlds", "standard_error", "start_series", "to_prob", "to_weight", "top_next",
    "wilson_interval",
]
