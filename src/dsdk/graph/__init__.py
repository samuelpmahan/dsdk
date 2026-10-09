"""dsdk.graph (track A5): graphs, traversal with witnesses, evidence-aware reachability, relational duals.

Builds on dsdk.core (Status/Judgment label edges and answers; Part lineage is a graph) and dsdk.logic
(a formula is a tree; see ``bridges``). Read ``model.py`` first: it holds the construction rules.
"""
from .bridges import (
    CALCULATION_LABEL,
    FORMULA_CHILD_LABELS,
    formula_graph,
    formula_labels,
    import_graph,
    lineage_graph,
    store_lineage_graph,
)
from .evidence import UNCERTAIN, candidate_path, known_subgraph, reachable
from .model import EDGE_STATUSES, EVIDENCE_RANK, Edge, Graph, GraphError, MissingNodeError
from .proofs import (
    Countermodel,
    GraphProof,
    entailed_by_known_edges,
    known_premises,
    node_var,
    unreachability_countermodel,
    witness_proof,
)
from .relational import (
    two_hop_counts_graph,
    two_hop_join,
    two_hop_matrix,
    two_hop_pairs,
    two_hop_pairs_graph,
)
from .traverse import (
    BFSResult,
    CycleError,
    bfs,
    components,
    dfs_postorder,
    dfs_preorder,
    find_cycle,
    shortest_path,
    strongly_connected_components,
    topological_order,
)

__all__ = [
    "Countermodel", "GraphProof", "entailed_by_known_edges", "known_premises", "node_var", "unreachability_countermodel", "witness_proof",
    "BFSResult", "CALCULATION_LABEL", "CycleError", "EDGE_STATUSES", "EVIDENCE_RANK", "Edge",
    "FORMULA_CHILD_LABELS", "Graph", "GraphError", "MissingNodeError", "UNCERTAIN", "bfs",
    "candidate_path", "components", "dfs_postorder", "dfs_preorder", "find_cycle", "formula_graph",
    "formula_labels", "import_graph", "known_subgraph", "lineage_graph", "reachable", "shortest_path",
    "store_lineage_graph", "strongly_connected_components", "topological_order", "two_hop_counts_graph",
    "two_hop_join", "two_hop_matrix", "two_hop_pairs", "two_hop_pairs_graph",
]
