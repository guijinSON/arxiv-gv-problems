# Rejected at Step 0: inverse planting does not inherit the paper's hardness

Paper: Ali Civril, [*Sparse Approximation is Hard*](https://arxiv.org/abs/1108.4664), arXiv:1108.4664. The last substantive text is [version 2](https://arxiv.org/pdf/1108.4664v2); version 3 was withdrawn with the note that its results were subsumed by another straightforward reduction.

## Decision

No generator is shipped. The proposed family—choose a sparse coefficient vector `x`, choose a dictionary `Phi`, and publish `y = Phi x`—passes **G (inverse generation)** and **V (exact matrix multiplication)** but fails **H**. The paper proves a worst-case inapproximability result for a very specific randomized reduction from Label Cover. It does not prove, or even claim, hardness for inverse-planted random dictionaries or for the completeness side of that reduction conditioned on a known labeling.

This is exactly the distinction required by Step 0: a worst-case NP-hard problem class does not make an answer-first distribution hard. Running attacks and the LLM loop could provide useful negative evidence, but could not turn the missing distributional hardness argument into a Track A theorem. Track B also has no honest basis here: the proposed construction specifies no compact hidden route distinct from ordinary sparse recovery. I therefore stopped before writing `gen_1108_4664.py`, `selftest_report.json`, or any oracle transcript.

## What the paper actually defines

Section 1 defines `Sparse`. Given a real `M x N` dictionary matrix `Phi`, a target `y` in `R^M`, and a sparsity budget `k`, choose `k` columns (equivalently a `k`-sparse coefficient vector) minimizing `||y - Phi x||_2`. It then defines `Diff-Sparse`, which chooses the same optimal supports but maximizes the squared norm of the orthogonal projection of `y` onto their span.

Theorem 2 states that `Diff-Sparse` cannot be approximated within

`(3 + 1/e)/4 + epsilon`

in polynomial time unless `ZPP = NP`. Corollary 3 translates that gap to the usual residual objective. These are worst-case gap statements, not average-case or planted-distribution statements.

The hard instances in Section 3 are not arbitrary dictionaries. The reduction:

1. starts from the parallel-repeated Label-Cover instance of Theorem 6;
2. independently keeps each edge with probability `1 / 5^ell`;
3. creates one column per vertex-label pair;
4. fills edge blocks with binary vectors derived from a Sylvester Hadamard matrix; and
5. fixes `k = |V'| + |W'|` and takes `y` to be the all-ones vector.

Theorem 10's soundness depends on the Label-Cover instance having value at most `2^(-alpha ell)` and on the random edge sampling. Its probability statement is over that reduction. Replacing its input with an independently planted satisfiable instance discards the premise that creates the gap.

## Certificate-production test

There are two natural ways to obtain a witness, and neither supplies H.

### The prior-triage inverse construction

Sample `x` first and compute `y = Phi x`. Certificate production is one matrix-vector product, `O(MN)` arithmetic in a dense representation (or `O(Mk)` when only the selected columns are used). Verification repeats the multiplication, counts the nonzero coefficients, and compares with `y` exactly. A zero residual also certifies optimality because a squared norm cannot be negative.

That establishes G and V only. Theorem 2 says nothing about this distribution. In the regimes normally chosen for inverse planting—random or incoherent columns and sufficiently small `k`—the paper itself points to Orthogonal Matching Pursuit and the incoherence/RIP literature as the tractable side of sparse recovery. In other parameter regimes, the generator would still need a distributional argument and measured resistance to the standard sparse-recovery algorithms; the paper provides neither.

### The paper's completeness construction

Theorem 9 says that if the Label-Cover instance has a labeling satisfying every edge, selecting the column for that label at every vertex gives `k` mutually orthogonal columns whose span contains the all-ones target. Its proof then says to choose the corresponding scaling coefficients. Thus, given the labeling, the sparse witness is produced directly in polynomial time by the proof.

This is a valid theorem-backed certificate construction, but it still does not produce a hard distribution. Generating satisfiable Label-Cover instances by first planting the labeling only yields completeness instances. Theorems 2, 6, and 10 are reductions distinguishing worst-case completeness instances from worst-case low-value soundness instances; none asserts that recovering a labeling from the planted completeness distribution is hard. The module would have to make that unsupported leap to claim Track A.

## Why neither track is supportable

| Track | Result | Reason |
|---|---|---|
| A — structural hardness | **Fails** | The only hardness theorem concerns the worst-case Label-Cover reduction and its soundness regime. It does not cover the answer-first distribution, and the prompt expressly forbids substituting worst-case NP-hardness for distributional hardness. |
| B — no-tool compression | **Fails for the proposed family** | No compact invariant, symmetry, or change of variables is supplied. The only known route is the same matrix/dictionary recovery task posed to the solver. Choosing an easy structured dictionary merely makes a standard algorithm the solution; choosing a generic planted dictionary supplies no paper-backed compact route. |

A contrived Track B problem could be invented by replacing `Phi` with, for example, a Walsh-Hadamard dictionary and hiding a transform identity. That would be a new compressed-transform puzzle, not a consequence of this paper's hardness theorem, and it would need its own oracle and attack evidence. It is not a valid rescue of the prior triage.

## Other candidate formulations

| Candidate task | G | H | V | Outcome |
|---|---:|---:|---:|---|
| Find an exact `k`-sparse `x` with `Phi x = y` in an inverse-planted dictionary | pass | **fail / unsupported** | pass | The planted distribution is not covered by the theorem and commonly lies in recovery-friendly regimes. |
| Recover the satisfying Label-Cover labeling from a Theorem 9 matrix | pass | **fail / unsupported** | pass | Planting a labeling does not inherit Theorem 10 soundness or establish average-case search hardness. |
| Return a support achieving a stated `Diff-Sparse` approximation ratio | possible | unresolved | **fails in general** | Checking the ratio requires the unknown optimum projection unless an independently checkable optimality certificate is also supplied. |
| Return the exact completeness witness from Theorem 9 when the labeling is public | pass | **fail** | pass | The proof writes the selected columns and scaling down directly. |

## Gate status

| Requirement | Status | Evidence |
|---|---|---|
| G — generatable | Would pass | Sample `x` first, or carry the satisfying Label-Cover labeling through Theorem 9. |
| H — hard under Track A | **Fails** | No theorem for the generated distribution; Theorem 2 is worst-case and Theorem 10 requires low-value Label Cover on the soundness side. |
| H — hard under Track B | **Fails for the proposed construction** | No separate compact route exists to create the required mechanical-versus-insight gap. |
| V — exact verification | Would pass for exact decomposition | Count support and recompute `Phi x = y` over exact rationals. |
| Steps 1–4 | Not run | The task requires stopping at Step 0 once G, H, or V fails. |

The decisive gate is H. The paper's title and worst-case theorem cannot certify the inverse-planted distribution requested by the prior triage, so shipping it would make precisely the hardness error the task warns against.
