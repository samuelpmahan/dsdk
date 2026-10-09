# A5 written proofs

The code in `dsdk.graph.traverse` is the executable counterpart of Proofs 1-3. `tests/graph/test_graph_traverse.py`
only samples behaviour (and checks it against Floyd-Warshall); the proofs establish the claims for ALL finite graphs.
Proof 4 is **deliberately wrong**: find the flaw before you read the diagnosis.

**Conventions.** A graph is finite, `G = (V, E)`. For an undirected graph read each edge `{u, v}` as the two arrows
`u -> v` and `v -> u`; duplicate edges are merged and self-loops are allowed (neither changes anything below).
A *walk* from `s` to `v` is a sequence of nodes where consecutive nodes are joined by an arrow; its *length* is the
number of arrows. `delta(s, v)` is the length of the shortest walk from `s` to `v`, or "infinity" if there is none.
Layer `L_k = { v : delta(s, v) = k }`. Weights are ignored: everything here counts hops.

---

## Proof 1 -- BFS computes `delta(s, v)` (and its parent pointers trace a shortest path)

**Algorithm** (`bfs`). `dist[s] = 0`, `parent[s] = None`, queue `Q = [s]`. While `Q` is non-empty: dequeue `u`; for each
out-neighbour `v` of `u` with no `dist` yet, set `dist[v] = dist[u] + 1`, `parent[v] = u`, enqueue `v`.

**Assumptions.** `s` is a node of `G` (else `MissingNodeError`); `G` is finite; "distance" means hops, not weights
(with weights BFS is simply the wrong algorithm); an undirected edge is usable both ways.

**Claim.** When BFS stops: (a) `dist[v] = delta(s, v)` for every `v` with `delta(s, v) < infinity`, and no other node has a
`dist`; (b) following `parent` from any reached `v` gives a walk to `s` of length `dist[v]`.

*Termination.* A node is enqueued only when it first receives a `dist`, so each node is enqueued at most once. The
measure "number of nodes not yet enqueued" never increases and the loop dequeues once per enqueued node: at most
`|V|` iterations.

*Lemma A (sound).* Every node with a `dist` is reachable and `dist[v] >= delta(s, v)`. Induction on the order of
assignment: `s` has `dist 0 = delta(s,s)`. If `v` is assigned from `u`, then `u` was assigned earlier, so by
hypothesis `dist[u] >= delta(s, u)`, and `u -> v` is an arrow, so `delta(s, v) <= delta(s, u) + 1 <= dist[u] + 1 = dist[v]`.
In particular nodes with `delta = infinity` never receive a `dist` (their absence is how unreachability is reported).

*Lemma B (queue order).* The queue, read in order of enqueueing, has non-decreasing `dist`, and consecutive entries differ
by at most 1. Induction on enqueue operations: the first entry is `s` (0). When `u` (the front, with the smallest `dist`
`d` in the queue) is dequeued, everything it enqueues gets `d + 1`, and the entries still in the queue have `dist`
in `{d, d+1}`, so appending `d + 1` keeps the order. QED.

*Main induction on `k`.* `P(k)`: every node of `L_k` gets `dist = k` and is enqueued, and no node of `L_{<k}` is assigned
anything else.
* **Base `k = 0`.** `L_0 = {s}` (a walk of length 0 ends where it started) and `dist[s] = 0`.
* **Step.** Assume `P(0..k)`. Take `v` in `L_{k+1}`. A shortest walk to `v` has a penultimate node `u`; the prefix to `u` is a
  shortest walk to `u` (if there were a shorter one, extending it would give a walk to `v` shorter than `k + 1`), so
  `u` is in `L_k`. By `P(k)`, `u` is enqueued with `dist k` and is eventually dequeued; at that moment `v` either already
  has a `dist` or receives `k + 1` from `u`. Suppose `v` already has a `dist`; it was assigned by some earlier
  dequeued node `w`, as `dist[w] + 1`. By Lemma A `dist[v] >= delta(s, v) = k + 1`. By Lemma B `w` was dequeued
  no later than `u` and `dist[w] <= dist[u] = k` (the queue is ordered by `dist`, and `u` is not earlier than `w`), so
  `dist[v] = dist[w] + 1 <= k + 1`. Hence `dist[v] = k + 1 = delta(s, v)`. No node of a lower layer is
  changed, because a `dist` is assigned once. This proves `P(k + 1)`.

Every node with finite `delta` is in some layer `L_k`, so (a) follows with Lemma A for the unreachable ones.

*(b)* If `parent[v] = u` then `u -> v` is an arrow and `dist[u] = dist[v] - 1`. Following parents strictly decreases `dist`,
so it ends after `dist[v]` steps at a node with `dist 0`, which is only `s`. The reversed chain is a walk from `s` to
`v` of length `dist[v] = delta(s, v)`: a shortest path (`shortest_path` returns it; `s == t` gives the empty walk).
QED.

*Where the tests fit.* `test_bfs_matches_floyd_warshall_and_witness_length_equals_distance` samples (a) and (b) on random
graphs; the proof covers the rest. The tie-break (a node's parent is the first dequeued among its shallowest
in-neighbours) is NOT needed for correctness, only for determinism.

---

## Proof 2 -- Kahn's algorithm: loop invariant and termination measure

**Algorithm** (`topological_order`, directed graph). `indeg[v]` = number of distinct arrows into `v` (a self-loop counts).
`R` = nodes with `indeg 0`, kept as a min-heap by node-order index. `E = []`. While `R` is non-empty: pop the smallest `v`; append `v`
to `E`; for each successor `w` of `v`, decrement `indeg[w]` and push `w` when it reaches 0. After the loop, if `|E| < |V|` there is a cycle.

**Loop invariant `I`** (true before every iteration and after the last):
1. `E` has no repeated node;
2. for every position `i` in `E`, all predecessors of `E[i]` appear at positions `< i`;
3. for every node `v`: `indeg[v] = |{ u in pred(v) : u not in E }|`;
4. `R = { v not in E : indeg[v] = 0 }`.

*Initialisation.* `E` is empty, so 1 and 2 hold vacuously; 3 is the definition of the initial in-degree; 4 is how `R` is built.

*Maintenance.* Let `v` be popped. By 4, `v not in E` (so 1 survives appending) and `indeg[v] = 0`; by 3 every
predecessor of `v` is in `E`, hence earlier than the new last position: 2 holds. Appending `v` to `E` removes the arrows
`v -> w` from the counted set for each successor `w` (and only those; duplicate arrows were merged so each is counted once),
which is exactly what the decrements do: 3 is restored. A successor reaching 0 is pushed, `v` leaves `R`, and no node
with `indeg > 0` is in `R`: 4 is restored. (If `v` has a self-loop then `v in pred(v)`, `v not in E`, so `indeg[v] >= 1`
and `v` was never in `R` -- consistent with 4.)

**Termination measure.** `m = |V| - |E|`, a natural number. Each iteration appends one node, so `m` decreases by exactly 1 and
stays `>= 0` (by invariant 1, `|E| <= |V|`). The loop therefore runs at most `|V|` times; with a heap the cost is `O((|V| + |E|) log |V|)`.

**Correctness at exit.** `R` is empty. *Case `|E| = |V|`:* by invariant 2 every arrow `u -> v` has `u` before `v`: `E` is a
topological order. *Case `|E| < |V|`:* let `U = V \ E`, non-empty. By 4 and `R = empty`, every `v in U` has `indeg[v] >= 1`, and by 3
that means a predecessor in `U`. Starting anywhere in `U` and repeatedly stepping to such a predecessor produces an infinite backward
walk inside the finite set `U`, so some node repeats: a cycle exists. Conversely, if a cycle exists, no node of it is ever
emitted: the first cycle node to be emitted would need its cycle-predecessor emitted earlier (invariant 2). So
**Kahn emits all nodes if and only if the graph is acyclic**, and the `CycleError` is raised exactly for cyclic graphs
(the witness itself comes from `find_cycle`, whose output is checked edge by edge in the tests).

*Determinism.* Ties are only ever between members of `R`; always popping the smallest index makes the whole run a function of
the graph and its node order.

---

## Proof 3 -- relabelling nodes preserves BFS distances

**Claim.** Let `pi : V -> V'` be a bijection and `G' = pi(G)` the graph with `u -> v` in `G` iff `pi(u) -> pi(v)` in `G'`
(`Graph.relabel` builds exactly this). Then `dist'(pi(s), pi(v)) = dist(s, v)` for all `s, v`, and `v` is unreachable from `s`
in `G` iff `pi(v)` is unreachable from `pi(s)` in `G'`.

**Proof.** Apply `pi` node by node to a walk `s = x_0, ..., x_k = v` of `G`: since `x_i -> x_{i+1}` is an arrow of `G`,
`pi(x_i) -> pi(x_{i+1})` is an arrow of `G'`, so we get a walk of the same length `k` from `pi(s)` to `pi(v)`. Applying `pi^{-1}`
(which exists because `pi` is a bijection) maps walks of `G'` back to walks of `G` the same way. So `pi` is a length-preserving
bijection between the set of walks `s -> v` in `G` and the set of walks `pi(s) -> pi(v)` in `G'`. The two sets of lengths
are equal, hence so are their minima and their emptiness. By Proof 1, BFS distance is that minimum. QED.

**What is and is not invariant.** Distances and reachability are properties of the graph's *structure* and survive any bijection.
Parent pointers, discovery order and witness paths depend on the *tie-break*, which is "smaller position in `nodes`". `Graph.relabel`
keeps every node at its position, so by induction on dequeued nodes the BFS run on `G'` is the run on `G` with names mapped by
`pi`, and even parents/orders/witnesses correspond. A renaming that *reorders* nodes can change which of several shortest paths is
reported (swap `b` and `c` in the diamond `a->b, a->c, b->d, c->d`: the witness for `(a, d)` moves from `b` to `c`) but never its length.
*Tests:* `test_bfs_distances_are_invariant_under_relabelling` (random permutations) and the fixed example next to it.

---

## Proof 4 -- "DFS finds shortest paths"  (**DELIBERATELY BROKEN**)

**Claim (false).** Let `T` be the tree of parent pointers produced by depth-first search from `s` (`dfs_preorder`). For every reachable `v`,
the tree path from `s` to `v` is a shortest path.

**"Proof".** Induction on `delta(s, v)`. If `delta = 0` then `v = s` and the tree path is empty. Suppose the claim holds for all nodes at distance
`k`, and let `v` have `delta(s, v) = k + 1`. Then `v` has an in-neighbour `u` with `delta(s, u) = k`. By the induction hypothesis
the tree path to `u` is a shortest path of length `k`. DFS explores every out-neighbour of `u`, so it reaches `v` from `u`, and the tree path to `v` is
the tree path to `u` plus the arrow `u -> v`, of length `k + 1 = delta(s, v)`. QED.

**Where it breaks.** The last sentence assumes DFS reaches `v` *from `u`*. DFS marks a node the first time it is touched, from whichever
node it happens to be exploring, and it explores one branch to the bottom before trying the next. If `v` is reached earlier along a different (longer)
branch, it is already marked when `u`'s turn comes, and the arrow `u -> v` is never used for the tree. Equivalently, the induction hypothesis is
used for "all nodes at distance `k`" at once, but DFS does not finish the nodes of one distance before starting the next -- the layer structure
that Proof 1 gets from the FIFO queue (Lemma B) does not exist for a stack.

**Counter-example** (in the tests): arrows `s->a, a->b, b->t, s->t`, nodes ordered `s, a, b, t`. `delta(s, t) = 1`, but DFS goes
`s, a, b, t` and records `parent[t] = b`: the tree path has length 3.
(`test_dfs_does_not_find_shortest_paths` pins this; `shortest_path` uses BFS for that reason.) What DFS *does* give, and
what `find_cycle` and the SCC algorithm rely on, is the finishing-order structure, not distance.
