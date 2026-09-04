# Rejected: arXiv 2405.10238

Paper: Mitali Bafna, Jun-Ting Hsieh, and Pravesh K. Kothari,
[*Rounding Large Independent Sets on Expanders*](https://arxiv.org/abs/2405.10238)
(v2, 2024).

## Decision

No family is shipped. The tested native Track B family passed inverse generation
and exact witness checking, but failed **H (hardness)**, the mandatory bare oracle
loop, and—on the subsequent construction-aware audit—**G6**. The script-owned
verdict is `too_easy`: the pool solved every named rung and the sole permitted
fixed-length escalation. The prompt therefore forbids further hand tuning.

The experimental module and script-owned bare transcript are retained as rejection
evidence. There is deliberately no shipping README, self-test report, or G9 arm:
STEP 4 failed first and requires stopping.

## What the paper actually says

Section 3.2 fixes the witness predicate: a set of vertices is independent exactly
when no input edge has both endpoints in the set. Equation (1) encodes the same
object by Boolean indicator variables.

The prior-triage idea—plant a large independent set in a random expander-like
graph—does not inherit the paper's hardness result. The positive results are
algorithms:

- Theorem 2, restated as Theorem 4.1, gives a polynomial-time algorithm for a
  regular graph containing an independent set of size
  `(1/2-epsilon)n` when `epsilon <= 0.001` and
  `lambda_2 <= 1-40 epsilon`.
- Algorithm 1 obtains a constant-degree sum-of-squares pseudo-distribution,
  conditions it on constantly many variables, and thresholds its marginals.
- Theorem 1 similarly handles almost 3-colorable one-sided expanders.
- Fact 3.7 identifies the easier regime above `n/2`, where the standard
  vertex-cover approximation already returns a linear independent set.

Appendix A does prove conditional worst-case hardness in a different regime.
Proposition A.2 concerns almost 4-colorable one-sided expanders under the Unique
Games Conjecture, and Proposition A.6 concerns exactly 6-colorable expanders under
the perfect-completeness `2-to-1` variant. Their reduction overlays a dense regular
bipartite expander on an already-hard source graph. These are worst-case promise
results, not average-case guarantees for a randomly planted distribution. Starting
from a hard source loses the known certificate; sampling a satisfying source first
loses the paper's hardness guarantee. Thus they do not justify Track A for the
triage's proposed planter.

The paper's other short witness candidates also fail H immediately. Lemma 2.1 asks
only for a correlated pair among three independent sets, and Lemma 2.5 only for a
correlated pair among three colorings. Each answer space has three pairs and is far
too small to satisfy guess resistance.

## Track B family that was tested

Section 7 defines the hypercube graph. The candidate used a relabelled `r`-cube
`Q_r`, which is regular, has an independent side of size `n/2`, and has normalized
second eigenvalue `1-2/r`; every tested rung lies comfortably inside Theorem 2's
regime at `epsilon=0.001`.

Each graph vertex received a distinct binary label. The answer was a bounded affine
polynomial over `GF(2)`, represented by one constant bit and a fixed-size support:

```text
P(x) = constant XOR XOR(bit_j(x) for j in support).
```

Its zero set had to contain exactly `n/2` vertices and no edge. The generator sampled
the support first, assigned graph sides according to its parity, and then assigned
the remaining labels. It never solved the generated graph. Verification recomputed
the zero set and scanned all edges, without reading `inst["answer"]`. The graph,
finite-field labels, and polynomial indicator were all visible to the solver; no
graph/SAT surrogate replaced the paper's object.

The bounded answer language had size
`2 * binomial(label_bits, weight)`. The final escalation had
`n=256`, `label_bits=72`, and `weight=8`, hence 23,938,032,690 candidates but only
two valid affine polynomials (the two bipartition orientations). The answer was nine
atomic values and 47--59 serialized characters, far below the output cap.

## Mechanical cost and compact route

This was correctly labelled Track B, not Track A. A reference solver first
bipartitions the graph by BFS and then solves the resulting affine parity equations
by exact Gauss-Jordan elimination over `GF(2)`. Its complexity is
`O(|V|+|E|+|V| d^2)` field operations. On eight final-escalation instances it solved
8/8 with:

| measurement | result |
|---|---:|
| mean exact field operations | 609,206 |
| maximum exact field operations | 616,296 |
| mean wall time | 0.00240 s |
| maximum wall time | 0.00258 s |

The intended compact route took at most **263 XOR operations**: XOR all 256 labels
to expose a distinguished center, then XOR its eight neighbor labels with the center
to read the support. That is much shorter than 616,296 scalar field operations and
fits the 300-operation cap, so the existence of an efficient algorithm alone was
not a reason to reject. The family was built and tested as Track B.

The decisive problem is that the shortcut was too visible and even shorter in
practice. The construction included the center together with all 72 labels at
Hamming distance one from it. A construction-aware outlier attack therefore:

1. chooses the label with the most Hamming-distance-one companions;
2. examines that vertex's graph neighbors; and
3. returns the eight coordinates on which those neighbor labels differ.

This deterministic attack returned a verifier-accepted polynomial on **20/20**
fresh instances at easy, medium, hard, and final-escalation settings (80/80 total).
It exploits the plant/decoy distribution directly: the affine frame is a glaring
per-element signature. The initial panel's weaker coordinate-bias, edge-flip,
random-restart, and “assume label zero is the center” probes all missed it. The
retained module now includes this attack and honestly reports G6 failure.

The oracle replies independently exposed the same defect. At medium, Claude wrote
that it found “a cluster around a base label with single-bit differences”; at hard,
it selected the distinguished vertex and read its one-bit neighbor differences.
Those were verified witnesses, not parser artifacts or uniform guesses.

## Mandatory bare oracle result

`scripts/harden.py` used the required four-vendor pool at medium reasoning effort.
API errors did not count as failures and were redrawn.

| round | rung | parameters `(n,d,w)` | verified solves / genuine attempts | outcome |
|---:|---|---|---:|---|
| 0 | easy | `(64,36,6)` | 2/3 | defeated |
| 1 | medium | `(128,48,7)` | 2/3 | defeated |
| 2 | hard | `(256,64,8)` | 3/3 | defeated |
| 3 | escalated | `(256,72,8)` | 2/3 | **defeated** |

At the final rung Gemini and Claude returned valid witnesses; Terra returned a
shape-correct but invalid polynomial. Grok timed out and was correctly excluded,
then the redraw supplied Claude's second genuine solve. The metadata records:

```json
{
  "verdict": "too_easy",
  "escalations_used": 3,
  "axes_moved": ["label_bits", "n", "weight"],
  "answer_atoms": 9,
  "answer_chars": 59,
  "reason": "the oracle pool solved every level through 3 escalations"
}
```

## Gate outcome

| requirement | result | evidence |
|---|---|---|
| G — known certificate by construction | Pass | sample the sparse parity polynomial first and label the two cube sides around it |
| V — cheap exact witness check | Pass | evaluate parity, count exactly `n/2`, scan graph edges |
| H — Track A | Unsupported | Appendix A is worst-case conditional hardness, not hardness of an inverse-planted distribution |
| H — Track B | **Fail** | every rung was solved; final rung 2/3, and the affine-frame attack solves 80/80 across rungs |
| G6 — adversary panel | **Fail** | construction-aware affine-frame outlier succeeds 20/20 at the final rung |
| STEP 4 | **Fail** | authoritative verdict `too_easy` after all allowed escalations |
| Overall | **Rejected** | G, H, and V do not hold simultaneously |

Removing the full affine frame could repair the statistical leak, but that would be
a new planted distribution with no hardness guarantee in this paper. Retuning after
the maximum oracle escalation is expressly forbidden, so it was not attempted.
