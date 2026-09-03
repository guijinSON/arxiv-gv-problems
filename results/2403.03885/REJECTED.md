# Rejected: arXiv:2403.03885

Paper: Idael Martinez-Perez, *Generalization of Cycle Decompositions of Even
Dimensional Hypercubes on d-Dimensional Toruses*,
[arXiv:2403.03885](https://arxiv.org/abs/2403.03885).

## Decision

No problem family from the paper is shipped. The proposed cycle-decomposition
family fails requirement **H (hard)** in every parameter regime for which the
paper provides a way to generate a known witness. The remaining regime is an
open existence/classification problem and therefore does not provide the
answer-first construction required by **G (generatable)**.

Consequently, `gen_2403_03885.py`, `selftest_report.json`, and an oracle-loop
transcript were deliberately not created. Running the hardening harness on a
family already disqualified at Step 0 would not repair the missing hardness
claim and would create misleading evidence.

## What the paper actually defines

Section 3 defines a cycle decomposition of a graph `G` as subgraphs
`H_1, ..., H_k` whose edge sets are pairwise disjoint, whose union is `G`, and
which are all cycles of the requested length. It also defines Cartesian-product
tori and anchored products. Thus a natural witness would be the complete list
of cycles, and it could be checked by verifying adjacency, cycle closure,
length, edge-disjointness, and exact coverage of the host graph's edges.

This gives cheap, exact verification relative to the explicit graph and
witness, so **V is plausible**. It does not give hardness.

## Why the generated regimes are easy

- **Section 4, Theorem 2** gives the General Square Decomposition explicitly.
  If `d >= 2`, `lambda > 0`, and `2*lambda` divides every torus side length
  `y_i`, it gives a decomposition of
  `C_(y_1) square ... square C_(y_d)` into
  `(product y_i)/(2*lambda)` cycles, each of length `2*d*lambda`. The theorem is
  followed by a closed algebraic definition of every cycle's edge set and the
  ranges of all indexing parameters.

- **Section 4, Corollary 4** specializes that formula to the anchored products
  used for `Q_(2an)`, explicitly constructing cycles of length `a*2^alpha` for
  `1 <= alpha <= 2n`.

- **Section 5, Theorem 5** gives the General Lock-and-Key Decomposition under
  stated parity and divisibility conditions. Again, it supplies a closed
  algebraic edge-set definition, parameter ranges, the exact number of cycles,
  and their exact length.

- **Section 5, Corollary 7** specializes the Lock-and-Key construction to
  `Q_(2an)` for
  `2n <= alpha <= 2an - (d - 1) - sum(i_k)`.

- **Section 5, Corollary 8** explicitly covers all admissible power-of-two
  cycle lengths `2^beta`, `2 <= beta <= 2bn`, for `Q_(2bn)` when `b` is even.

- **Sections 6 and 7** are correctness proofs for these constructions. Theorem
  9 and Theorem 14 prove that two cycles from the respective formulas share an
  edge if and only if they are the same cycle. Theorems 13 and 18 establish the
  cycle lengths. These proofs make the formulas certified direct solvers, not
  evidence of computational hardness.

For the main odd-`a` setting, the introduction explicitly combines the two
methods into a constructive range

`1 <= alpha <= 2an - (d - 1) - sum(i_k)`.

Sampling parameters in this range and constructing a decomposition would meet
G, but a solver can reproduce the published formula. Randomly reordering input
edges or relabelling vertices would only obscure a formulaic instance; it would
not establish an intrinsically hard problem family.

The paper contains no NP-hardness, parameterized-hardness, exponential lower
bound, or other complexity result for finding these decompositions. It instead
emphasizes that its contribution is constructive and describes its edge-set
definitions as explicit algebraic closed forms (end of Section 5).

## Why the open regime cannot be planted honestly

At the end of Section 7, the paper asks for necessary-and-sufficient conditions
for decomposing `Q_(2an)` into cycles of length `a*2^alpha` in the longer range

`2an - (d - 1) - sum(i_k) < alpha <= 2an - ceil(log2(a))`

when `d >= 3` and odd `a` has at least three powers of two in its binary
expansion. This is an open existence/classification question. It is not a
hardness theorem, and the paper does not give a construction from which one can
sample a valid decomposition answer first. Using this regime would therefore
lose G; using the proved regimes loses H.

There is an additional practical mismatch: with a hypercube specified compactly
by its dimension, a full edge decomposition has size proportional to the
hypercube's exponentially many edges. Making the graph explicit would make the
witness polynomial in the rendered input size, but it would not remove the
paper's direct construction.

## Gate status

| Requirement | Status | Evidence |
|---|---:|---|
| G | Conditional only | Answer-first generation is available only in the explicitly solved parameter ranges. |
| H | **Fail** | Theorems 2 and 5 give closed edge-set constructions; Corollaries 4, 7, and 8 cover the relevant hypercube regimes. No computational-hardness result appears in the paper. |
| V | Plausible | An explicit list of cycles can be checked by exact adjacency and edge-partition tests. |
| Overall | **Rejected** | No regime supported by the paper satisfies G, H, and V simultaneously. |

No G1–G8 measurements are reported because the mandatory Step 0 acceptance
condition failed before a generator existed.
