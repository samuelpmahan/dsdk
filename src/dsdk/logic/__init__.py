"""dsdk.logic (track A1): formulas, semantics, proofs, discrete structures.

Builds on dsdk.core: ``evaluate_partial`` returns a ``dsdk.core.Judgment``, and ``record_proof`` stores a checked proof as kernel Parts
(one tick, one Part per step) that ``replay_proof`` rebuilds from the lineage.
"""
from .formula import And, Const, Formula, Iff, Implies, Not, Or, Var, size, to_str, variables
from .proof import CheckResult, Proof, Rule, Step, check
from .recorded import ProofStepError, RecordedProof, record_proof, replay_proof
from .semantics import (
    UnassignedVariableError,
    countermodel,
    entails,
    evaluate,
    evaluate_partial,
    is_satisfiable,
    is_valid,
    models,
    truth_table,
)
from .structures import Leaf, Node, Tree, mirror, tree_height, tree_size, triangular

__all__ = [
    "ProofStepError", "RecordedProof", "record_proof", "replay_proof",
    "And", "CheckResult", "Const", "Formula", "Iff", "Implies", "Leaf", "Node", "Not",
    "Or", "Proof", "Rule", "Step", "Tree", "UnassignedVariableError", "Var", "check",
    "countermodel", "entails", "evaluate", "evaluate_partial", "is_satisfiable",
    "is_valid", "mirror", "models", "size", "to_str", "tree_height", "tree_size",
    "triangular", "truth_table", "variables",
]
