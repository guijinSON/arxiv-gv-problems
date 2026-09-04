# Rejected at Step 0: the certificate is the spectral computation

Paper: Iliyas Noman and Yuan Yao, [*Spectral Conditions for Spherical
Two-Distance Sets*](https://arxiv.org/html/2211.12582v2), arXiv:2211.12582v2
(2026 revision of the 2022 preprint).

## Decision

No generator is shipped. The natural native tasks are generatable and exactly
verifiable in isolation, but none satisfies **G + H + V** together with the
bounded-answer and anti-guessing requirements.

- **Track A fails H.** Theorem 1.1 is a necessary-and-sufficient spectral
  characterization. Proposition 1.2 reads the minimum representation dimension
  directly from the multiplicity of the second adjacency eigenvalue. The paper
  gives no worst-case or distributional hardness theorem for obtaining any of
  these data. They are produced by standard polynomial-time spectral linear
  algebra.
- **Track B also fails H.** On an unrestricted graph, the purported compact
  route is exactly the same computation of the spectra of `A_G` and `P A_G P`;
  no shorter solver-visible invariant is provided. On the only broad shortcut
  regime proved by the paper, Corollary 6.2, checking regularity is already the
  complete mechanical route. There is therefore no mechanical-versus-compact
  compression gap.
- The prior-triage proposal to output actual points has an independent **G9(c)**
  failure. For the paper's regime of `N=d+2` points in `R^d`, merely listing one
  coordinate array requires `N(N-2)` scalar atoms, before representing the
  generally algebraic coordinates. At `N=18` this is 288 atoms and already
  exceeds the 256-atom cap.

This is primarily an H rejection, not a witness-rule rejection. Eigenvectors,
exact characteristic-polynomial/root-isolation data, a PSD/rank certificate, or
an explicit coordinate realization can all be made into inspectable witnesses.
The problem is that the same spectral or factorization algorithm produces them.

## What the paper actually defines

Definition 2.1 calls a finite set in `R^d` a two-distance set when the distances
between distinct points take exactly two values. Definition 2.2 associates a
graph by making the *longer* distance an edge. Definition 2.4 calls the set
spherical when all its points lie on a common `(d-1)`-sphere, and calls a graph
spherically representable when it is the associated graph of such a set.

The paper studies the small regime of exactly `d+2` graph vertices/points:

- Theorem 2.1 (Einhorn--Schoenberg) says every graph on `d+2` vertices that is
  not complete multipartite has a unique two-distance ratio for a representation
  in `R^d`; complete multipartite graphs have none.
- Lemma 2.2 (Schoenberg) turns prescribed distances into the exact conditions
  `B' >= 0` and `rank(B') <= d`. A realization is then obtained by factoring
  this positive-semidefinite Gram-type matrix.
- Lemma 4.2 gives the distance matrix directly as
  `B_G = I - A_G/lambda_2 - J`.
- Corollary 4.3 consequently gives
  `k = sqrt(1 + 1/lambda_2)`.
- Theorem 1.1 says that `G` is spherical in `R^d` exactly when the largest
  eigenvalue of `P A_G P`, for `P=I-J/(d+2)`, equals `lambda_2` and its
  multiplicity there equals the adjusted multiplicity in `A_G`.
- Proposition 1.2 and its reformulation in Section 6 say the lowest spherical
  representation dimension is `N-k`, where `k` is the adjusted multiplicity of
  `lambda_2`.
- Corollary 6.2 makes the major easy regime explicit: every regular,
  non-complete-multipartite graph on `d+2` vertices is spherical in `R^d`.

These are native graph/Gram-matrix statements licensed by the paper itself; no
discrete surrogate was needed for this audit.

## Step-0 mechanical cost versus compact route

I used a representative would-be shipping size of **N=128 vertices**
(`d=126`). This size still permits a single 128-entry eigenvector witness under
the atomic-element cap, although it cannot permit a full coordinate realization
or dense Gram certificate.

For Theorem 1.1, the standard numerical reference calculation forms `P A_G P`
and computes two dense symmetric spectra. Its arithmetic scale is `Theta(N^3)`;
the conservative proxy `2*N^3` is **4,194,304 scalar cubic work units** at
`N=128`. With NumPy 1.26.4, OpenBLAS restricted to one thread, and both matrices
pre-formed, 30 repetitions averaged **0.001123556 seconds for both spectra**.
An exact checker replaces floating comparison by rational characteristic
polynomials, polynomial gcd/multiplicity tests, and exact real-root ordering
(or equivalent exact symmetric-matrix methods); that remains polynomial time
and does not create a solver shortcut.

The comparison is:

| Proposed family | Mechanical cost at the representative size | Compact route | Track-B result |
|---|---:|---:|---|
| Decide spherical representability by Theorem 1.1 | Two spectra; `Theta(N^3)`, 4,194,304 cubic work units, 0.001123556 s for the floating reference at `N=128` | **The same two spectra and multiplicity comparison**, hence the same asymptotic route and no sub-300-operation shortcut | Fail: ratio 1; nothing is being compressed |
| Return the minimum dimension from Proposition 1.2 | The same spectral computation, followed by one subtraction | **The same eigenvalue-multiplicity computation**, followed by one subtraction | Fail: the subtraction is not the costly part |
| Use Corollary 6.2 on regular graphs | Read/check all row sums; 16,256 off-diagonal adjacency inspections at `N=128` | **The identical row-sum check**; if regularity is promised, the answer is immediately “yes” | Fail: ratio 1, or a one-answer/guessable task |
| Construct point coordinates using Lemma 2.2 | Spectral/PSD factorization plus writing `N(N-2)=16,128` scalar coordinates | No different coordinate formula is proved; the compact route is the same factorization | Fail H, and fail G9(c) by 63 times the 256-atom cap |

For completeness, the largest coordinate instance that can fit the atomic cap
is `N=17`, `d=15`, with exactly 255 raw coordinate entries. At that size the
same one-thread benchmark averaged **0.000015105 seconds** for the two spectra,
with `2*N^3 = 9,826` cubic work units. It is both mechanically tiny and still
requires far more than the 300-operation intended-route cap once a generic
factorization is included. The compact route is no shorter.

The timing is not being offered as an exact verifier: it measures the standard
mechanical spectral route requested by the Track B triage. Exact equality and
multiplicity checking costs more, but follows the same polynomial-time route;
the paper supplies no separate short one.

## Why the answer-space requirements do not create hardness

The obvious small outputs cannot pass the task's guessing gate:

| Output | Structure-aware answer space | Consequence |
|---|---:|---|
| “spherical” / “not spherical” | 2 | Guess probability at least `1/2` |
| Minimum dimension | at most `N-1` possibilities | At `N=128`, guess probability at least `1/127`, not below `1e-6` |
| Distance ratio for a spherical graph | Uniquely determined by `lambda_2` via Corollary 4.3 | Enlarging a rational/algebraic encoding does not hide the spectral algorithm that computes it |

Attaching enough spectral data can enlarge the formal certificate language, but
it does not repair H: an eigensolver/characteristic-polynomial computation emits
that data. A full eigenspace, PSD matrix, Gram matrix, or point configuration
also grows linearly or quadratically with `N` and soon violates G9(c).

One could restrict generation to specially structured integral graphs and ask
for a sparse eigenvector hidden by a relabelling. That would test recognition of
the chosen graph construction (line-graph reconstruction, modular decomposition,
or graph isomorphism), not the paper's spectral characterization. If the
structure is stated, its known spectrum supplies the answer directly; if it is
hidden, the generator's private relabelling is not a solver-visible compact
route. Such a puzzle would need its own distributional and attack analysis and
is not justified by this paper.

## Candidate-family audit

| Candidate task | G | H | V / output | Outcome |
|---|---:|---:|---:|---|
| Given `G`, decide whether it has a spherical representation | Possible by constructing a regular graph | **Track A:** spectral iff test; **Track B:** no compression, and regular graphs are Corollary 6.2 | Exact spectral verification is possible, but the answer is binary | Reject |
| Given a spherical `G`, return its least representation dimension | Possible with a graph of known spectrum | **Fails:** Proposition 1.2 makes this an eigenvalue-multiplicity readout | An optimum certificate requires spectral/rank data; the scalar alone is guessable | Reject |
| Return the unique distance ratio | Possible with a known-spectrum graph | **Fails:** Corollary 4.3 is an explicit formula after computing `lambda_2` | Algebraic-number certification is possible | Reject |
| Return points on a sphere realizing `G` | Possible by constructing points first or factoring Schoenberg's matrix | **Fails:** standard PSD/spectral factorization produces the witness | Exact algebraic coordinates are bulky; raw coordinates exceed 256 atoms for `N>=18` | Reject |
| Given points, certify that exactly two distances occur | Trivial by construction | **Fails:** enumerate squared distances and compare | Exact and cheap, but it verifies a supplied object rather than searches a large witness space | Reject |

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G -- certificate known by construction | Possible in isolation | Start from points/Gram data, or choose a graph with known spectrum |
| H -- Track A structural hardness | **Fail** | Theorem 1.1, Proposition 1.2, Lemma 4.2, and Corollary 4.3 reduce the native answers to polynomial-time spectral data; no hard generated distribution is proved |
| H -- Track B no-tool compression | **Fail** | Generic instances have no route shorter than the reference spectrum computation; regular instances use the same row-sum test mechanically and compactly |
| V -- exact witness checking | Possible in isolation | Exact inner products, polynomial identities, PSD/rank, and algebraic root isolation are executable checks |
| G4 / answer space | **Fail for the natural scalar tasks** | Binary, dimension, and other small direct answers are readily guessable |
| G9(c) | **Fail for explicit geometric witnesses at scale** | `N(N-2)` coordinate atoms; over the 256-atom cap from `N=18` onward |
| Overall | **Rejected at Step 0** | No paper-backed family clears all gates on either track |

Steps 1--4 were intentionally not run. In particular, no LLM-hardening result
can turn a polynomial-time spectral readout with no distinct compact route into
a Track B problem, and no generator/self-test/oracle artifacts were fabricated.
