# Rejected at Step 0: arXiv 2212.13149

Paper: Himadri Mukherjee, Askar Ali M, and Bogdan D. Djordjević,
[*Solutions to a system of Yang-Baxter matrix equations*](https://arxiv.org/abs/2212.13149)
(v2, 19 June 2024).

## Decision

No native family in this paper clears **G + H + V**.  The prior-triage proposal
can generate rational matrices and verify a submitted matrix exactly, but it
fails **H on Track A** and **H on Track B**.  In the paper's only scalable,
theorem-backed construction regime, a valid nonzero solution is obtained by one
outer product.  The certificate-producing algorithm and the compact structural
route are therefore the same computation; there is no no-tool compression gap.

This decision was made before Step 1, as required.  No generator, self-test
report, README, or oracle transcripts were created: those artifacts would imply
that a family had survived Step 0 when it had not.

## The exact native problem

Section 1 fixes matrices `A,B in M_n(K)`, for `K=R` or `C`, and asks for a matrix
`X` satisfying both

```text
X A X = B X B,       X B X = A X A.
```

The zero matrix is always a solution, so a search problem must at least require
`X != 0`.  Section 3, Lemma 3.1 embeds this system into a single Yang--Baxter
matrix equation using `2n x 2n` anti-diagonal block matrices.  Theorem 3.2
shows that simultaneous similarity carries solutions to solutions.  These are
valid structure-preserving transformations, but neither result supplies a hard
generated distribution.

The scalable explicit classification is Section 5.  There `A` and `B` are
idempotent orthogonal complements:

```text
A^2=A,  B^2=B,  AB=BA=0.
```

After simultaneous diagonalization, the main Section 5 theorem writes `X` in
blocks and reduces validity to exact identities such as
`Y_1^2=Y_2^2=0`, `Y_1 C=C Y_2=D Y_1=Y_2 D=0`, `CD=Y_1`, and `DC=Y_2`.
Thus Section 5 does support answer-first generation and exact checking.  It does
not support hardness.

## Step-0 discriminating test

For every idempotent-orthogonal pair and every matrix unit `E_ij`, define

```text
X = A E_ij B = (column i of A) (row j of B).
```

Then all four sides of the two requested equalities are zero:

```text
X A X = A E_ij (BA) E_ij B = 0,
B X B = (BA) E_ij B^2 = 0,
X B X = A E_ij B^2 A E_ij B = A E_ij (BA) E_ij B = 0,
A X A = A^2 E_ij (BA) = 0.
```

If `A` and `B` are nonzero, choose any nonzero column of `A` and any nonzero
row of `B`; their outer product is nonzero.  This works after every simultaneous
similarity transformation, so hiding the Section 5 block form behind a dense
change of basis does not hide a witness.  It also accepts a witness other than
the generator's plant, as a correct verifier must.

I measured this attack on 100 independently generated dense integer conjugates
of the canonical complementary projectors at each size.  Each conjugate was
formed by `5n` random elementary unimodular similarities.  The operation count
below charges the scan for the first nonzero column and row plus all entries of
the outer product; verification was a separate exact substitution.

| dense matrix size | attack successes | production operations, min / median / max | median / max wall time |
|---:|---:|---:|---:|
| 8 | 100/100 | 80 / 80 / 88 | 0.0070 / 7.0249 ms |
| 12 | 100/100 | 168 / 168 / 168 | 0.0117 / 0.0160 ms |
| 16 | 100/100 | 288 / 288 / 288 | 0.0166 / 0.6137 ms |

The `n=16` row is the relevant upper edge for a dense matrix answer: it already
contains exactly **256 atomic entries**, the G9(c) cap.  Its mechanical cost is
288 elementary scans/multiplications and its compact route is the identical
288-operation column--row construction, a ratio of **1**.  Returning the
rank-one factors instead would reduce both costs to copying `2n` coordinates;
it would not open a Track B gap.  Increasing `n` with an expanded matrix answer
only violates the output cap, while using the factorized answer makes the
solution still more immediate.

This attack is stronger than a Gröbner-basis computation and is the algorithm
that actually produces the certificate on the generated distribution.  The
paper's use of Gröbner bases elsewhere therefore cannot be cited as the
mechanical baseline for this family.

## Hardness diagnosis

### Track A fails

The paper proves no computational-hardness theorem, average-case result, or
hardness statement for a generated distribution.  More decisively, the direct
`A E_ij B` algorithm above solves every nontrivial Section 5 instance in
`O(n^2)` arithmetic after a linear scan.  It succeeds independently of the
plant and of the simultaneous basis change.  Consequently the required
domain-standard attack would have successes rather than the `0/8` demanded by
Track A.

Imposing a prescribed high rank, uniqueness normalization, random linear
measurements, or a special coefficient code could exclude these rank-one
solutions, but none is part of the paper's Yang--Baxter system or its Section 5
classification.  Such side constraints would make the added encoding, rather
than the paper's equations, carry the search difficulty.

### Track B fails

The most favorable paper-backed Track B candidate is precisely the Section 5
family hidden by Theorem 3.2's simultaneous similarity.  Its standard
certificate-producing computation is the outer-product construction just
measured, and recognizing `AB=BA=0` gives exactly that same construction.  The
mechanical and compact costs are equal, including at the largest writable dense
size.  There is nothing shorter to discover than the algorithm already used to
produce an arbitrary valid witness.

Requiring a maximal-rank off-diagonal solution does not rescue an honest paper
family.  Once the common image/kernel decomposition is known, both the
mechanical method and the purported compact method select bases and an
isomorphism between the two subspaces by the same Gaussian-elimination work.
Without an extra generator-specific encoding there is again no separate short
route.  Moreover, conjugating one canonical projector pair produces no new
abstract pair: simultaneous idempotent orthogonal complements are classified
by their joint eigenspace dimensions.  A canonical key that quotients change
of basis would collapse such seed variation rather than count it as diversity.

## Why the other sections do not rescue a family

| Paper result | Candidate task | Why it fails |
|---|---|---|
| Section 3, Lemma 3.1 and Theorem 3.2 | transform a known solution by block embedding or similarity | These preserve a certificate but add no hardness.  Section 5 plants remain vulnerable to `A E_ij B`; repeated conjugates also create only relabelled instances under the paper's own symmetry. |
| Section 3, intertwining theorem | output an intertwining solution from a matrix `E` | The theorem requires `E` itself to solve another displayed nonlinear matrix equation.  It is a characterization, not a scalable certificate generator.  The closed-form square-root formula is an explicit algorithm in the regular commuting case, not Track-A hardness. |
| Section 4, doubly-stochastic results | find a doubly-stochastic solution | The main scalable theorem is a nonexistence result when at least one coefficient is a permutation matrix.  The paper provides no Farkas, Nullstellensatz, Positivstellensatz, or other instance-local executable refutation certificate.  Brouwer's theorem gives existence for auxiliary fixed-point equations but does not construct the required common fixed point. |
| Section 5 block classification | find any nonzero solution | Solved universally by the measured rank-one outer-product attack. |
| Section 6 Gröbner calculations | solve the complete `2 x 2` cases | The matrix dimension is fixed.  The propositions display explicit one-parameter formulas or the zero solution.  Direct sums merely expose independent constant-size blocks and scale answer transcription rather than reasoning. |
| General `A,B` | solve an unrestricted system | The paper explicitly treats general Yang--Baxter solution search as open and gives necessary spectral conditions, not a theorem-backed answer-first generator.  Generating `A,B` by first solving for them around a random `X` would violate G. |

The Section 4 negative theorem was also checked against the witness rule.  An
inverse matrix and a permutation flag make its hypotheses cheap to test, but
they are not an algebraic refutation of nonexistence.  Even if one treated the
theorem's hypotheses as a bespoke negative certificate, producing and checking
them is routine exact inversion/permutation testing, so Track A would still
fail and the paper supplies no distinct compact Track B route.

## Gate outcome

| Requirement | Result | Evidence |
|---|:---:|---|
| G -- certificate known by construction | Passes in isolation | Section 5 block solutions, followed by Theorem 3.2 similarity, give exact rational plants. |
| V -- cheap exact witness verification | Passes | Multiply rational matrices and compare both identities exactly; no numerical approximation is needed. |
| H -- Track A | **Fails** | No hard regime is proved, and `X=A E_ij B` finds a nonzero witness in `O(n^2)` on every scalable theorem-backed instance. |
| H -- Track B | **Fails** | At writable `n=16`, mechanical and compact routes are both the same 288-operation outer product; measured ratio 1 and 100/100 success. |
| G7/G8 for the fixed `2 x 2` classification | **Fails** | Fixed dimension does not scale; block repetition is decomposable and lengthens the answer. |
| Overall | **Rejected at Step 0** | G and V never coexist with H for a paper-backed family. |

The rejection is not based on the abstract, on the mere existence of an
algorithm, or on confusing a valid witness with a hard-to-find one.  It follows
from the full paper's scalable parameter regime and the measured algorithm that
actually produces an arbitrary valid certificate there.
