# Rejected: no hard, writable uncertain-clique witness family

Paper: Arko Provo Mukherjee, Pan Xu, and Srikanta Tirthapura,
[*Mining Maximal Cliques from an Uncertain Graph*](https://arxiv.org/abs/1310.6780),
arXiv:1310.6780v3.

## Decision

No generator is shipped.  The paper supplies native exact witnesses and cheap
verification, so **G and V pass**, but the available bounded-answer families do
not pass **H on either track**:

- finding one alpha-maximal clique is polynomial by a direct greedy extension,
  so it cannot support Track A;
- enumerating all alpha-maximal cliques is the paper's genuinely exponential
  task, but its output violates G9(c)'s 256-atom answer cap in the hard regime;
- the attempted exact-probability compression family honestly declared Track B
  and passed every local gate, but every completed bare oracle call solved it:
  **11/11** across `easy`, `medium`, `hard`, and the first escalated level.

The final oracle attempt was interrupted when the OpenRouter account reached
its total key limit.  That does not weaken the rejection: a level is defeated
as soon as any oracle solves it, and the escalated level already had two scored
solutions before the infrastructure errors began.  The script-owned transcript
and metadata are retained, as are both experimental generators.

## What the paper actually defines

Section 2 defines an uncertain graph `G=(V,E,p)` as an undirected simple graph
whose possible edges occur independently.  Definition 3 defines the clique
probability of `C`; Observation 1 makes it the product of the probabilities of
the edges induced by `C`.  Definition 4 says `M` is alpha-maximal exactly when
its clique probability is at least alpha and no single outside vertex can be
adjoined while preserving that inequality.  Observation 2 proves downward
monotonicity under taking subsets.

Section 3, Theorem 1 proves that for `0 < alpha < 1` the largest possible number
of alpha-maximal cliques on `n` vertices is
`binom(n,floor(n/2))`.  Its lower-bound construction is a complete graph with a
uniform edge probability chosen so that **every** half-size set is maximal.
Section 4's MULE algorithm enumerates all alpha-maximal cliques; Theorem 2 proves
correctness and Theorem 3 gives worst-case time `O(n*2^n)`.  Section 4's
large-clique variant prunes by a requested size threshold but remains an
enumerator.  The output-size observation gives the matching obstruction:
enumeration can require `Omega(sqrt(n)*2^n)` output time.

## Step 0: what produces each certificate?

### One maximal clique

Start with the empty set (or any vertex) and scan the remaining vertices.  Add
`v` whenever the current set together with `v` has clique probability at least
alpha.  If `v` fails once, Observation 2 implies it cannot become eligible after
the current clique grows.  One pass therefore returns an alpha-maximal clique.
With incremental edge products this takes at most `binom(n,2)` exact
multiplications/comparisons, hence `O(n^2)` arithmetic (or `O(n^3)` if every
probability is recomputed from scratch).

There is no shorter hidden route on an unstructured instance: the compact route
also has to inspect the incident probabilities, so it is `Theta(n^2)`.  At the
509-vertex experimental shipping size that is at most 129,286 edge checks.  If
the plant is given a recognizable signature, the route becomes shorter only
because the planting leaks the answer.  Thus this family fails **H/Track A**, and
has no meaningful mechanical-versus-compact gap for Track B.

Theorem 1's construction is worse as a benchmark: once the required answer
size is stated, every candidate in the structure-aware language is valid, so
the guess success probability is one.

### All maximal cliques

MULE is the appropriate standard algorithm and its `O(n*2^n)` bound is honest,
but a witness must list the output.  Theorem 1 permits
`binom(n,floor(n/2))` cliques.  Already at `n=10`, its construction needs 252
five-vertex sets, or 1,260 atomic vertex entries, five times the G9(c) cap.
Larger hard instances only widen the violation.  Compressing that list to its
count would cease to be a witness: the checker could not validate the count by
inspection without reproducing the enumeration.  This route fails **G9(c)**.

### Requiring a large clique

Adding a size threshold avoids the greedy-one-maximal-clique argument in the
worst case, but the paper gives no average-case theorem for a planted
large-clique distribution.  Theorem 3 is an enumeration upper bound, not a
hardness theorem for recovering one planted clique.  Importing the usual
planted-clique conjecture would make the hardness belong to an external model,
and such a construction would require spectral and relaxation attacks that are
not justified by this paper.  Worst-case clique hardness alone would not meet
the prompt's distributional Track-A requirement.

## Track-B experiment and measured costs

The retained `rejected_gen_1310_6780.py` tests the paper's native Observation-1
product.  It defines a complete uncertain graph by exact rational edge factors.
Affine maps permute all edge ranks and layer ranks; neighboring factors
therefore telescope, and the layer endpoints telescope again.  The answer is a
single exact rational generated by composition of identities.

At its hard preset (`n=509`, 20 layers):

| quantity | measured value |
|---|---:|
| explicit edge-layer factors | 2,585,720 |
| exact cancellation/multiplication operations | 5,171,460 per instance |
| reference wall time | 1.877930 s mean over 8 seeds |
| reference success | 8/8 |
| compact route | 19 exact operations |
| structure-aware random guesses | 0/200,000 |
| bounded no-tool attacks | 0/8 for each of five attacks |
| answer size | 20 characters, 2 atoms |

This is the required mechanical/compact comparison.  The gap is large, so the
existence of the polynomial reference algorithm alone was **not** used to
reject it.  The problem is that the shortcut is too visible.  The bare
hardening transcript records:

| level | parameters | scored solves |
|---|---|---:|
| easy | `n=193`, 8 layers | 3/3 |
| medium | `n=353`, 14 layers | 3/3 |
| hard | `n=509`, 20 layers | 3/3 |
| escalated | `n=1019`, 28 layers | 2/2 completed calls |

Thus increasing the mechanical work did not increase model difficulty.  The
compact route—recognize two affine permutations, use the sums of the first
integers and squares, and cancel endpoints—was recovered every time.  This
fails **H/Track B**.

An earlier, more verbose opcode prototype is retained in the `g9_hinted/` and
`g9_placebo/` scratch directories together with its local report in
`selftest_report.json`.  It obscures the same invariant behind six explicitly
reversible index operations.  Repeating those operations increases prompt
length and mechanical work, but not the mathematical route: checking the six
opcode definitions once proves that every generated program is a permutation.
It therefore does not repair the failure shown by the scored experiment.

## Gate summary

| requirement | result |
|---|---|
| G — construction | Passed for the experiments: endpoint certificates were sampled/composed before the instances. |
| V — exact checking | Passed: exact integer arithmetic and rational cross multiplication. |
| H — Track A | **Failed** for one-maximal-clique recovery; the greedy algorithm is polynomial. |
| H — Track B | **Failed** for exact probability compression; 11/11 completed bare calls solved. |
| G9(c) | **Failed** for the paper's full enumeration problem because the witness can be exponentially long. |
| Overall | **Rejected; no family clears all gates simultaneously.** |

