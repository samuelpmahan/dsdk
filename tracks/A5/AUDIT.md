# Audit of the graph proofs (tracks/A5/PROOFS.md)

Auditor: the foundations manager (Sonnet). The proofs were written by the worlds manager's track, so this is an independent review.
`P` means tracks/A5/PROOFS.md, `T` means src/dsdk/graph/traverse.py, `M` means src/dsdk/graph/model.py. I did not edit the proofs or the code.
Every claim below was either checked by reading the real code line by line or by running the real code in tracks/A5/audit/ (commands at the end).

## Verdicts

| Proof | Verdict |
|---|---|
| 1. BFS computes shortest hop distances, parent pointers trace a shortest path | SOUND WITH GAPS. The theorem is true and the main induction is correct. The statement of the queue-order lemma is weaker than what its own proof uses (P35-38), and its maintenance step skips the case where the front of the queue changes. |
| 2. Kahn's algorithm: loop invariant, termination, exit | SOUND WITH GAPS. All four invariant clauses hold on every traced iteration. One step is not justified (P82-84), the witness depends on a function with no proof (P94-95), and the cost claim (P87) is false for the shipped code. |
| 3. Relabelling preserves BFS distances | SOUND, one ambiguous sentence (P117-118). The stronger remark (parents, order and witnesses also correspond) is true and I ran it on every small graph. |
| 4. Deliberately broken: "depth-first search finds shortest paths" | SOUND AS AN EXHIBIT. The claim is false, the counter-example is right, and the diagnosis names the real flaw. Two details about what the tests pin are overstated (P139-141). |

## Findings

1. **The queue-order lemma is stated more weakly than the induction step needs (Proof 1, P35-38, used at P47-49).**
   The lemma says the queue has non-decreasing distances and that consecutive entries differ by at most 1. The sentence that proves it then uses a stronger fact: that every entry still in the queue has distance d or d+1, where d is the distance of the front. Those are not the same. A queue with distances 0, 1, 2 satisfies the stated lemma but not the one used (the audit script asserts this on the example). The code never produces such a queue, so nothing is wrong with the algorithm, but a reader checking the lemma as stated could not derive the step. Suggested fix: state the lemma as "all entries lie in {d, d+1} and are in non-decreasing order".
2. **The lemma's maintenance step skips one case (P36-38).**
   After the front is removed, the new front can have distance d+1, so the set {d, d+1} must be re-read as {d+1, d+2}. This works because the new entries are all d+1, but the proof only says "appending d+1 keeps the order". It is a two-line gap.
3. **Proof 2 uses a fact it never proves (P82-84).**
   Maintenance says that a successor whose in-degree reaches 0 is pushed, and then that clause 4 holds. For that, the successor must not already be in the output. It cannot be: the node just emitted was a predecessor of the successor and was not yet in the output, so by clause 2 the successor cannot have been emitted. One sentence is missing.
4. **The cycle witness depends on a function that has no proof (P94-95).**
   The proof shows Kahn comes up short exactly when a cycle exists, then says the witness "comes from `find_cycle`". Nothing in the file shows that `find_cycle` finds a cycle whenever Kahn comes up short. If it returned `None`, building the error would crash (T35 joins the cycle; a planted mutant made Kahn short on an acyclic graph and the result was a TypeError, which the audit script observed). I checked the dependency by running both on every directed graph with up to 4 nodes (66,066 graphs, self-loops included): `find_cycle` finds a cycle exactly on the cyclic graphs, and every witness is a closed walk of real arrows. So the dependency holds on all small graphs, but it is an unproved assumption for larger ones. Suggested fix: either prove `find_cycle` (a back edge to a node on the current path exists iff there is a cycle) or state the dependency as an assumption.
5. **The cost claim in Proof 2 was false for the code as committed when I started (P87); an uncommitted edit to model.py has since made it near-linear.**
   The proof says the cost is O((|V|+|E|) log |V|) with a heap. On a path graph, doubling |V| multiplied the time by 4.0 to 4.2 for both the Kahn function and BFS (|V| 1000 to 4000). The reason is in model.py, not in the algorithm: `Graph.neighbors` and `Graph.predecessors` scan every edge and rebuild the node-to-position table on each call (M, `_positions`), so each of the |V| calls costs about |V|+|E|. The correctness proofs are unaffected. (Status at the end of the audit: someone changed model.py in the working tree while I was working, and re-running the timing now gives ratios of 1.9 to 2.1, so the finding is closed once that edit is committed; the two ratios above are what I measured on the committed code.) Until then, either the proof should say "for the algorithm, given constant-time neighbour lookups" or the graph should keep an adjacency index.
6. **"Swap b and c" is ambiguous (Proof 3, P117-118).**
   If you rename b to c and c to b with `Graph.relabel`, nodes keep their positions, so the witness for (a, d) maps along with them: (a, b, d) becomes (a, c, d), the image of the old path. The witness changes to the other branch only if the node LIST is reordered, which is a different operation. The sentence says "a renaming that reorders nodes", which is the second reading, but "swap b and c" suggests the first. The audit script confirms both readings.
7. **The tests do not pin what P139-141 says they pin (Proof 4).**
   P says the search "records `parent[t] = b`" and that the test pins this. The graph package does not expose depth-first parent pointers at all (`dfs_preorder` returns only the visit order), and the test asserts the visit order (s, a, b, t) and the breadth-first path (s, t), not a parent. The counter-example is correct: the audit reconstructed the parent with an independent recursive search and got b, with a tree path of 3 arrows against a distance of 1.
8. **Minor wording: "the empty walk" (P56).** For the source equal to the target, `shortest_path` returns the one-node tuple (s,), which is a walk of length 0. Correct, but "empty" suggests an empty tuple.

## What was shown mechanically (all runs use the real code)

* **Breadth-first search, layer by layer (tracks/A5/audit/check_bfs_layers.py).**
  The real `bfs` was run unmodified under a tracer that copies `queue`, `distance`, `parent` and `order` every time the loop test is reached.
  Graphs: every directed graph on up to 3 nodes with self-loops (512), every loop-free directed graph on 4 nodes (4,096), every undirected graph on up to 4 nodes with self-loops (1,024 for 4 nodes plus the smaller ones), every source, plus 1,500 random directed graphs on 5 nodes: 23,760 runs and 98,377 loop-test states.
  At every state: queue distances are non-decreasing and lie in {d, d+1} (the strong form), every assigned node already has its exact Floyd-Warshall distance (stronger than the proof's lemma that it is at least that), and every node whose true distance is at most d is already assigned (the layers fill in order). At the end the distance map equals the independent oracle, every parent arrow exists, and the parent is the first dequeued in-neighbour (which is also a shallowest one, so the tie-break remark at P60-61 is true).
  Non-vacuity: a copy of `bfs` that uses a stack instead of a queue was rejected on 3,072 of 16,384 loop-free 4-node runs.
* **Kahn invariant (tracks/A5/audit/check_kahn_invariant.py).** The real `topological_order` was traced on all 66,066 directed graphs with up to 4 nodes (self-loops included), 87,064 loop-test states. Asserted at each state: no repeated node in the output, every predecessor of each output node sits earlier, each in-degree equals the number of predecessors not yet emitted, the ready heap is exactly the set of un-emitted nodes with in-degree zero (no duplicates), and exactly one node is added per iteration. At exit it emits every node exactly when an independent transitive-closure test says the graph is acyclic; otherwise it raises with a witness that is a closed walk of real arrows; and `find_cycle` agrees with the independent test on every graph. Non-vacuity: a copy that decrements twice was rejected on 138 of 512 three-node graphs.
* **Relabelling (tracks/A5/audit/check_relabel.py).** 1,628 graphs (all directed graphs up to 3 nodes, all undirected up to 4) times every permutation of names times every source: distances, parents, discovery order and every shortest-path witness correspond under `relabel`. The diamond example and the two error cases (non-injective mapping, missing key) behave as stated.
* **The broken proof (tracks/A5/audit/check_dfs_counterexample.py).** The counter-example holds. Over every loop-free directed graph on 4 nodes, the depth-first tree path is longer than the shortest in 8,448 of 53,248 reachable (graph, source, target) triples, while the breadth-first tree path was exactly shortest in all of them. The depth-first post-order is a reverse topological order on every acyclic graph tried.
* **Cost (tracks/A5/audit/check_cost.py)** prints the doubling ratios behind finding 5.

## What is still not shown

* Everything is exhaustive only for graphs up to 3 or 4 nodes (5 nodes sampled). The proofs themselves cover all finite graphs; the runs only confirm the code and the statements on small ones.
* Proof 1 and Proof 2 cover the algorithms as described. The tracer checks the invariants of the code, not the Python implementation of `Graph.neighbors`; the cost finding shows that layer is not as the proof assumes for complexity.
* `find_cycle` and the strongly-connected-components function have no proof in this file (the file does not claim any). Only the agreement with Kahn on up to 4 nodes was checked.
* Weighted behaviour is out of scope (the proofs explicitly ignore weights).

## How to re-run

    .venv/bin/python tracks/A5/audit/check_bfs_layers.py          # about 4 s
    .venv/bin/python tracks/A5/audit/check_kahn_invariant.py      # about 11 s
    .venv/bin/python tracks/A5/audit/check_relabel.py
    .venv/bin/python tracks/A5/audit/check_dfs_counterexample.py
    .venv/bin/python tracks/A5/audit/check_cost.py                # timing, prints ratios
