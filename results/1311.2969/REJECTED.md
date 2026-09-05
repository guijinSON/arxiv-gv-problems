# Rejected at Step 0: arXiv 1311.2969

Paper: Henning Bruhn, Richard Lang, and Maya Stein,
[*List edge-colouring and total colouring in graphs of low treewidth*](https://arxiv.org/abs/1311.2969).

## Decision

No module is shipped. The natural planted-colouring family passes **G** and **V**,
but it has no defensible **H** claim on either track.

- **Track A fails:** the paper proves existence in a low-treewidth/high-degree
  regime; it does not prove distributional hardness for planted compatible-list
  instances. The proof recursively constructs a colouring from local reductions and
  a bipartite list-edge-colouring extension. Planting a colouring and then deriving
  its lists supplies a certificate, not an average-case hardness result.
- **Track B fails:** in the paper's native problem the witness contains one colour
  for every edge (and, for total colouring, every vertex as well). The paper supplies
  no invariant, change of variables, or symmetry that compresses this output. For
  the strongest structured candidate considered below, the standard construction
  and the compact route are literally the same one-formula-per-edge computation:
  **256 modular colour evaluations versus 256 modular colour evaluations** at the
  maximum permitted 256-atom answer size. There is no mechanical/compact gap.

This is an **H rejection**, not a witness-rule rejection. A proposed colouring is a
perfectly good concrete witness: membership in each edge list and all incident-colour
conflicts can be checked exactly in linear time.

## What the paper actually proves

Section 3 fixes the exact native object. An assignment is a function
`L:E(G) -> P(N)`, and an `L`-edge-colouring is a function `gamma:E(G) -> N` with
`gamma(e) in L(e)` such that incident edges have different colours.

Theorem 1 states that a graph of treewidth `k` and maximum degree

```text
Delta(G) >= (k+3)^2 / 2
```

has list chromatic index `Delta(G)`. Its proof is an induction/minimal-counterexample
argument. A low degree-sum edge is deleted and greedily reinserted; otherwise Lemma 3
finds sets `U,W`, Lemma 4 finds a choosable subset `C` of `W`, the proof recursively
colours `G-C`, and Theorem 5 (Borodin--Kostochka--Woodall) supplies the bipartite
list-edge-colouring used to extend it.

Section 4 defines total colouring and proves Theorem 2: for treewidth `k >= 3` and
`Delta(G) >= 3k-3`, the total chromatic number is `Delta(G)+1`. The proof again starts
from a colouring with an edge removed and extends it by inspecting missing colours,
performing local recolourings, and finally colouring the low-degree vertices in `W`.
Remark 10 explicitly identifies the easier regime `Delta(G) >= 3k-1`, where the
remaining recolouring argument is unnecessary.

The Introduction also points to Meeks and Scott's fixed-parameter algorithms for
list edge and list total chromatic number parameterised by treewidth. Thus declaring
Track A merely from general graph-colouring hardness would contradict the paper's
own algorithmic context and, more importantly, would say nothing about the generated
distribution.

## Certificate-producing method and costs

For the native edge-colouring search task, the certificate-producing method exposed
by Section 3 is:

1. repeatedly delete a low degree-sum edge or a choosable set obtained from the tree
   decomposition;
2. colour the reduced graph;
3. restore each deleted part, using greedy insertion or the bipartite
   Borodin--Kostochka--Woodall extension.

The method necessarily writes `m=|E(G)|` colours. Verification also reads those `m`
colours. Under G9(c), `m <= 256`, so even a hypothetical formula-based native answer
must be expanded to at most 256 atomic colour values before it can be submitted.

The most favourable concrete Track B attempt was a theorem-backed low-treewidth
subgraph of an even complete graph. Restricting the standard round-robin
one-factorisation gives a known proper edge-colouring without solving the instance.
For an edge with finite round-robin coordinates `a,b`, its colour is computed by one
modular expression; an edge incident with the distinguished infinity vertex uses its
other endpoint's coordinate. At the 256-edge cap:

| route | measured/countable work at the cap |
|---|---:|
| standard round-robin construction | 256 edge-colour evaluations |
| purported compact route | 256 edge-colour evaluations |
| exact verifier | 256 list/conflict insertions, plus membership checks |

The compact route is **no shorter** than the mechanical route. Both are `Theta(m)`,
and both are dominated by writing the witness. This is precisely the case in which
Track B tests nothing beyond carrying out the standard construction.

For a planted compatible-list variant, there are only two outcomes:

- Preserve the round-robin or planted signature in the lists: a frequency, position,
  common-palette, or formula attack recovers a colouring in the same `Theta(m)` work.
- Draw plants and decoys from the same distribution strongly enough to remove that
  signature: the paper offers no short way to recover the planted colouring. The
  task becomes the generic list-edge-colouring search performed by the recursive
  method, so there is no compact Track B route to report.

The prior-triage proposal therefore establishes inverse generation only. It does not
establish hardness.

### Measured adversarial prototype

A second Track B prototype used the paper's Theorem 5 directly.  On `K_{r,d}` every
edge list was a translate of one hidden `d`-element subset of a cyclic colour group:

```text
L(i,j) = x_i + y_j + S.
```

Every fixed `s in S` gives the valid colouring `gamma(i,j)=x_i+y_j+s`, so generation
is theorem-backed and plants and decoys have exactly the same distribution.  The
generic reference implementation was Galvin's kernel method, with each kernel found
as a stable matching in the induced bipartite graph.

The prototype exposed the unavoidable tradeoff:

| regime tested | obvious greedy results | consequence |
|---|---:|---|
| `K_{2,32}`, `K_{2,64}`, `K_{2,80}`, colour universe about `4d` | 100/100 solved at every size | Sparse/high-degree instances fail G6 immediately. |
| `K_{6,40}`, 41 colours | 96/100 random-order greedy solves | Random restart is decisive. |
| `K_{16,16}` minus four random edges, 17 colours | 1/200 random-order greedy solves | Tight enough to resist one greedy run, but the answer has 252 atoms and the common-translate Latin-square ansatz solves deterministically. |

On 100 tight `K_{16,16}` instances, the Galvin/stable-matching reference used
**2,703--2,991 counted membership, proposal, comparison, and assignment operations**.
The shared-translate route requires about **268 modular additions** (precompute one
row shift, then emit one colour per edge).  This is only one order of magnitude, and
252 of those 268 operations merely produce the 252 required output atoms.  More
importantly, the shared-translate formula is the obvious in-context ansatz that G6
requires us to run, and it succeeds on every instance.  Hiding that ansatz requires
extra coordinate/circuit encoding not present in the paper; once added, that encoding
rather than list edge-colouring is the source of difficulty.

## Other native-looking variants considered

| candidate | result |
|---|---|
| Plant an `L`-edge-colouring and add compatible decoys | G and V pass; Track A has no distributional theorem, while visible planting signatures make the family easy. |
| Plant a `Delta+1` total colouring | Same issue, with a longer witness because vertices and edges must both be coloured. |
| Restrict a round-robin colouring of an even complete graph | G and V pass; mechanical and compact costs are both one formula evaluation per output edge (256 versus 256 at the cap). |
| Give a partial total colouring and ask for one missing edge colour | A standard missing-colour set difference is already the paper's local method. Making it look hard requires a large artificial encoding of the colour permutation. |
| Encode millions of star edges by an algebraic/permutation circuit and ask for the omitted colour | This can manufacture a Track B circuit-evaluation puzzle, but the difficulty is entirely in the added succinct encoding. The graph is a trivial star and Section 4 contributes only the word “missing”; this would be `reduction_kind="convenience"`, `reduction_source="benchmark_convenience"`, and not native coverage of the paper. |
| Ask for the numerical list chromatic index | Theorem 1 gives `Delta` directly, while certifying the universal statement over all list assignments is not a locally checkable witness. |
| Ask for a “choosable” subset from Lemma 4 | Choosability quantifies over every admissible list assignment; a subset alone is not an executable witness, so V fails. |

## Gate summary

| requirement | outcome |
|---|---|
| G -- generatable | Passes for planted or round-robin candidates. |
| V -- exact verification | Passes for an explicit colouring by list membership and incident-colour checks. |
| H -- Track A | **Fails:** no average-case/distributional hardness theorem for the generated instances; the paper instead gives constructive reductions in the guaranteed regime. |
| H -- Track B | **Fails:** the best native compact route is the same `Theta(m)` construction as the mechanical route, concretely 256 versus 256 evaluations at the answer cap. |
| Overall | **Rejected before implementation.** |

No generator had been written before this Step 0 decision, so there is no
`rejected_gen_1311_2969.py` to retain. No oracle hardening run was made: running it
after H already failed would spend oracle calls without creating a shippable family.
