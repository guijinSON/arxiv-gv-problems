# arXiv 1802.10566 — SLSN blueprint generator (parked)

**Status:** `cap_bound`, not rejected and not shipped. The module and both hardening transcripts are retained so the decision can be replayed.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (a compact subgraph blueprint) |
| Intuition | invariant: find the single additive gauge consistent around every color triangle |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 4.2.3, Lemmas 4.10–4.11 and Theorem 4.4 |

## What the problem is

[Babay, Dinitz, and Zhang, *Characterizing Demand Graphs for the (Fixed-Parameter) Shallow-Light Steiner Network Problem*](https://arxiv.org/abs/1802.10566) defines SLSN as follows: given an undirected graph with positive edge costs and lengths, a common distance bound, and demand pairs, find a minimum-cost subgraph in which every demand pair is connected within that bound (Definition 1.1).

This generator starts with a cyclically encoded multicolored-clique instance and applies the paper's central two-root reduction. The solver receives a succinct weighted version of the resulting SLSN graph, with the paper's degree-two unit paths contracted. It must return one candidate vertex per color; that tuple denotes the exact proof subgraph. `verify` checks every modular edge, expands the selected macro-edges, sums their integer costs, and runs exact Dijkstra searches from both demand roots. It never reads `inst["answer"]`.

This is representational rather than native-domain coverage: the SLSN graph and demands remain explicit, but the search is carried by the Multicolored Clique surrogate licensed by the paper.

## Why Track B, and why it is parked

The paper's easy regimes matter. Theorem 2.2 gives an `n^{O(p^4)}` algorithm when the number of demands `p` is constant, and Theorem 2.3 gives an FPT algorithm for star demands. The generated demand graph is the growing two-root complete-bipartite graph from Section 4.2.3, so neither easy regime applies; Theorem 2.4 and Theorem 4.4 establish W[1]-hardness for the corresponding unrestricted parameter regime. That worst-case result does **not** establish hardness of this planted distribution, hence Track B rather than Track A.

For this distribution, sparse path consistency is an exact polynomial reference algorithm, `O(k^3 d^2)`. At the named hard preset it solved 8/8 local test instances in about 0.05 seconds and 141,608 modular support tests. Recognizing the additive gauge reduces this to at most 282 exact operations, but the model pool found and executed that route anyway: it solved 3/3 hard instances and 3/3 escalated `k=60` instances. Increasing `k` again would exceed the 300-operation G9 cap, so the harness returned `cap_bound`. This is a harness/format limit, not evidence against the paper, and `REJECTED.md` is intentionally absent.

The first discarded ladder kept `k=12` and increased only the modulus; every instance through modulus 521 was solved. That evidence is preserved in `initial_budget_bound_transcript.jsonl`. It motivated the final group-count ladder.

## Worked demo

For `make_instance(n=4, modulus=11, offsets_per_pair=2, seed=0)`, `render` returns this complete instance (without a hint):

```text
Shallow-Light Steiner Network subgraph blueprint

All indices and residues below are zero-based. Arithmetic in the D table is
modulo m=11. There are k=4 color groups. Group i has candidate vertices
V(i,a), one for every residue 0 <= a < m. Its global vertex ID is i*m+a.
For i<j, V(i,a) and V(j,b) are compatible exactly when (b-a) mod m belongs
to D[i,j]. The complete table is:

  D[0,2] = {10, 8}
  D[1,3] = {1, 9}
  D[1,2] = {10, 0}
  D[0,1] = {4, 10}
  D[0,3] = {0, 1}
  D[2,3] = {5, 1}

This table compactly defines the following UNDIRECTED weighted graph. Every
displayed edge has both length and cost equal to its weight; weight w denotes
an internally unique w-hop unit-length/unit-cost path.

Vertices:
  roots R1,R2;
  Z(i,j) for i<j;
  ZE(i,a,j,b) for every compatible i<j pair;
  Y(i) and YV(i,a);
  X(i,a,j) and terminal L(i,j) for every ordered i!=j.

Edges (and no others):
  R1--Z(i,j) [1];
  Z(i,j)--ZE(i,a,j,b) [1] for compatible pairs;
  ZE(i,a,j,b)--X(i,a,j) [1] and --X(j,b,i) [1];
  R2--Y(i) [1], Y(i)--YV(i,a) [1];
  YV(i,a)--X(i,a,j) [1] for i!=j;
  X(i,a,j)--L(i,j) [4].

There are 24 demands: for every ordered pair i!=j, both {R1,L(i,j)} and
{R2,L(i,j)} must be connected in the chosen subgraph by a path of length at
most 7. The subgraph's total edge cost must be exactly 92.

Choose exactly one V(i,a_i) from every group in increasing group order.
Normalize global translation by choosing V(0,0), ID 0. The checker expands
the canonical proof subgraph, requiring every chosen pair to be compatible,
exact cost 92, and every demand to meet the closed distance bound.

Give the final answer inside <answer></answer> tags as four comma-separated
global vertex IDs, with no brackets. Output nothing else inside the tags.

<answer>0, 21, 32, 33</answer>
```

`verify(inst, [0, 21, 32, 33])` returns `(True, "ok")`; dropping the final representative returns `(False, "wrong representative count")`. This demo is hand-solvable: normalize the first residue to zero and test the two offsets from group 0 to group 1 against the remaining triangle relations.

## Difficulty and hardening

| Preset | `k` | Modulus | Offsets/pair | Demands | Oracle result |
|---|---:|---:|---:|---:|---|
| demo | 4 | 11 | 2 | 24 | skipped; hand example |
| easy | 24 | 97 | 2 | 1,104 | solved 3/3 |
| medium | 40 | 193 | 2 | 3,120 | solved 2/3; one invalid tuple |
| hard | 58 | 389 | 2 | 6,612 | solved 3/3 |
| escalated | 60 | 491 | 2 | 7,080 | solved 3/3; then `cap_bound` |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted certificates verified |
| G2 | drop, swap, duplicate, empty, and out-of-range rejected with five distinct reasons |
| G3 | tagged prose round-trip and JSON-native answer both passed |
| G4 | 0/200,000 normalized, structure-aware guesses valid; language size is `389^57` |
| G5 | exactly one normalized answer by construction; strongest failed attack was 2,048 random restarts in 1.106 s |
| G6 | five attacks at 0/8; path consistency solved 8/8, as expected for Track B |
| G7 | doubled `k=116` instance built and verified; demands grew from 6,612 to 26,680 |
| G8 | 100/100 affine/color relabellings preserved the key and carried witness; 20/20 unrelated keys distinct |
| G9(c) | 319 characters, 117 measured tokens, 58 atomic elements, 282 intended-route operations |

The bare hardening transcript contains the 12 calls summarized above. Since the terminal verdict was `cap_bound`, the hinted and placebo arms were not run. Their difference is therefore undefined, and no conclusion about hint effectiveness is claimed.

## Use

```python
import importlib.util

spec = importlib.util.spec_from_file_location("slsn", "results/1802.10566/gen_1802_10566.py")
slsn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slsn)

inst = slsn.make_instance(seed=7, **slsn.DIFFICULTY["demo"])
question = slsn.render(inst)
answer = slsn.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert slsn.verify(inst, answer) == (True, "ok")
```

The normal emission command would be `bash scripts/emit.sh 1802.10566 20 hard`, but it should **not** be used for release while `.meta.json` records `cap_bound`.

## Caveats

- The additive gauge is deliberately recoverable; a solver with scripting support dispatches the family quickly. This is exactly why the claim is Track B.
- G4 samples uniformly after the freely visible global-translation normalization. Its zero hits bound random guessing under that prior; it does not prove computational hardness or model hardness.
- The generator rejection-samples decoys to rule out a second triangle-consistent gauge. It never derives the planted certificate by solving, but this conditioning is not the paper's input distribution.
- The canonical key covers color permutation, relation-order changes, independent cyclic translations, and a global nonzero affine multiplier. It is a strong cheap invariant, not a complete graph-isomorphism canonical form.
- The attack panel does not include SAT/ILP packages or SDP relaxations. It includes uniform-degree outlier, greedy, first-anchor, diagonal, 256-restart, and exact path-consistency probes.
- The succinct weighted graph contracts internally unique paths from the paper's unit-length/unit-cost construction. Expanding them preserves cost and every terminal distance.
