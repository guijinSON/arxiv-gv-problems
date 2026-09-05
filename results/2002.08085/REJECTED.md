# Rejected at Step 0: arXiv 2002.08085

Paper: Gary R. W. Greaves, Jeven Syatriadi, and Pavlo Yatsyna,
[*Equiangular lines in low dimensional Euclidean spaces*](https://arxiv.org/abs/2002.08085)
(2020).

## Decision

No self-contained, scalable family from this paper clears **G + H + V**.  The
native auxiliary witness (a rational Farkas vector for an interlacing-polynomial
coefficient system) is generatable and exactly verifiable, but it fails **H on
both Track A and Track B** once the checker-visible matrix is included.  The
paper's complete geometric nonexistence claims avoid that easy LP only by
requiring the expensive enumeration itself to be certified; then **G/V and the
answer-size/scaling requirements fail**.  Implementation therefore stopped
before Step 1, as the instructions require after a Step-0 failure.

This is not a rejection merely because an algorithm exists.  The mechanical
cost and the shortest legitimate compact route are quantified below.  No
generator, self-test report, README, or oracle transcripts were fabricated.

## What the paper actually proves

Section 1 gives the exact native correspondence.  Unit representatives of `n`
equiangular lines have a Gram matrix `G` with diagonal entries 1 and off-diagonal
entries `+/- alpha`; the associated Seidel matrix is `S=(G-I)/alpha`.  Reversing
a representative switches `S` by a diagonal `+/-1` matrix.  Positive
semidefiniteness and rank `d` force the least eigenvalue of `S` to be
`-1/alpha` with multiplicity `n-d`.

The paper does **not** construct the 28-line or 40-line configurations.  Their
existence is imported from earlier papers in the first paragraphs of Sections
6.1 and 6.2.  The contribution here is nonexistence: Theorems 5.1, 5.4, 6.1,
and 6.11 rule out 75, 95, 29, and 41 lines in dimensions 19, 20, 14, and 16.
Consequently, the prior-triage proposal to generate coordinates from "a known
Gram matrix or symmetry construction" is not a construction contained in this
paper.

The proof pipeline is explicit:

1. Theorem 2.1 fixes the least eigenvalue at `-5` in the four relevant regimes.
2. Lemma 3.1 and Corollary 3.2 constrain the characteristic polynomial.
3. Section 2.3's McKee--Smyth coefficient-enumeration algorithm lists all
   totally real polynomials satisfying the divisibility and congruence tests.
4. Section 4.1 enumerates all interlacing characteristic polynomials.
5. Section 4.2 rewrites Thompson's derivative identity (Theorem 2.3) as
   `x^T A = g^T, x >= 0`.  A vector `c` with `A c >= 0` and `g.c < 0` is the
   executable Farkas certificate.
6. The remaining exceptional cases use algebraic angle compatibility in
   Section 4.3 and Sections 6.1--6.2, not a coordinate construction.

The paper also states what is easy.  Proposition 3.3 reports candidate-list
times of **0.52 s, 0.61 s, 69.33 s, and 395.43 s** for the four fixed cases.
Most subsequent interlacing lists take hundredths of a second to a few seconds.
The largest reported one, in Lemma 6.8, contains 124 polynomials and took
**450.77 s** in the paper (455.624 s in the authors' saved notebook output).
All computations in the paper together took less than 22 minutes.  There is no
hardness theorem or scalable hard parameter regime.

## Step-0 certificate question

| proposed problem | what produces the witness | gate result |
|---|---|---|
| Given `A,g`, find a Farkas vector `c` | Rational linear programming in only 4--8 variables; exact substitution checks it | G and V can pass, but H fails on A and B |
| Given a candidate characteristic polynomial, certify that no Seidel matrix has it | Enumerate every admissible interlacer, then use Farkas/compatibility | The expensive enumeration is part of the certificate's soundness, not a solver computation that a compact witness bypasses |
| Certify the full bounds `N(14)=28`, etc. | Candidate-polynomial enumeration plus dozens of Farkas and algebraic compatibility cases | Fixed classification, not an unlimited family; a complete answer is far beyond the output cap |
| Produce 28 or 40 equiangular lines | A construction in the cited earlier literature, absent here | The suggested generator is not supplied or guaranteed by this paper |
| Randomly switch/relabel one known Gram or Seidel matrix | Direct matrix conjugation of a fixed external example | Canonically the same instance, with no G7 scaling or seed diversity |

## Mechanical cost versus compact route

The apparent 450.77-second Track B opportunity disappears when the problem and
checker are separated correctly.  That computation **constructs `A`** by proving
that its rows exhaust the admissible interlacing polynomials.  It does not search
for the seven-entry Farkas vector after `A` is handed to the solver.  If a prompt
contains `A`, its exhaustiveness is instance data and the remaining search is a
tiny LP.  If it does not contain `A`, a checker cannot infer nonexistence from the
short Farkas vector without repeating the enumeration that the alleged shortcut
was supposed to avoid.

I measured the hardest checker-visible LP using the authors' Lemma 6.8 notebook
output: **123 inequalities in 7 free variables**, with target coefficient vector
`(28,-700,6272,-23400,27148,22692,-31400)`.  SciPy/HiGHS found a separating
ray in **7 iterations** and a median **0.000900 s** over 200 runs (mean 0.001242
s).  Solving its active 7-by-7 basis over exact rationals gives, after positive
integer scaling,

```text
(6827279, 0, 0, 8078, 0, -143, -33),
```

which exactly has `A c >= 0` and `g.c < 0`.  The paper's different displayed
certificate `(0,0,0,-7130,-5303,-1486,-344)` verifies just as cheaply.  Exact
verification uses 123-by-7 plus one 7-term dot product: **868 coefficient
products** (and the corresponding additions).

There is no shorter self-contained compact route in the paper.  Once `A` is
visible, the by-hand route is the same small-dimensional separation/elimination
and the same row scan: `Theta(123*7 + 7^3)` elementary rational operations, of
the same order as the mechanical LP.  Merely copying the seven integers from
the appendix is a classification-table lookup, not an invariant or symmetry a
solver can discover.  Thus Track B has no meaningful mechanical/compact gap at
the native size.  The 450.77-second enumeration cannot be put on the mechanical
side while silently trusting its output on the checker side.

Artificially duplicating rows could make an LP perform a million scans, but it
would only enlarge the prompt.  A sound compact route would still have to inspect
the rows unless the generator marked which ones matter; marking them makes the
witness immediate.  Increasing the seven-variable system is not licensed by a
theorem in this paper, whose results concern four fixed low-dimensional cases.
Generating arbitrary planted LPs would be a benchmark-convenience analogue that
has discarded the Seidel/equiangular-line mathematics.

## Why neither hardness track can be claimed

**Track A fails.**  For the only directly executable witness problem, rational
LP is polynomial-time and is tiny on every matrix in the paper.  For the earlier
enumeration stages, Sections 2.3 and 4.1 give the certificate-producing
algorithm and measured sub-22-minute total cost.  More importantly, the paper
proves no distributional hardness for planted coefficient systems, partial Gram
matrices, Seidel completion, or any scalable generated distribution.

**Track B fails.**  With all data needed by an exact checker, the strongest
mechanical attack takes 7 LP iterations and under one millisecond, while the
compact route is the same elimination/row scan.  With the data omitted, there
is no bounded executable witness: the solver must supply an exhaustive list and
the checker must validate total reality, type-2 congruences, interlacing, and the
exceptional algebraic compatibility cases.  That is the paper's computation,
not a dozen-operation change of variables.

The coordinate alternative does not repair this.  Importing one of the earlier
28- or 40-line configurations and applying orthogonal changes, switchings, and
relabelings yields transformations of one known certificate, not canonically new
instances.  A full 28-by-28 Gram matrix already has 784 atomic entries, beyond
the 256-atom answer cap; a coordinate matrix is larger.  The paper provides no
fixed-length symbolic coordinate certificate or scalable construction around
which a Track B compression problem could be formed.

## Final gate accounting

- **G:** passes only for the small auxiliary Farkas systems or for transformations
  of an external fixed configuration; the full theorem/classification does not
  give an unlimited scalable inverse generator.
- **H / Track A:** fails because the executable certificate is a tiny LP and no
  distributional hardness theorem exists.
- **H / Track B:** fails because the measured mechanical and compact routes are
  the same small separation computation; the slow enumeration produces missing
  instance data rather than being bypassed by the witness.
- **V:** passes for `A c >= 0, g.c < 0`; it fails for the desired geometric
  nonexistence claim unless exhaustive enumeration/compatibility evidence is
  also supplied and checked.
- **G7/G8/G9(c):** the four theorem regimes are fixed, relabelled known
  configurations are canonical duplicates, and complete Gram/classification
  certificates exceed the answer cap.

No admissible family remains after these distinctions, so running the oracle
hardening loop would manufacture evidence for an auxiliary planted LP rather
than for this paper's native mathematical result.
