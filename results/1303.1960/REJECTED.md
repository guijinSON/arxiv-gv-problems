# Rejected at Step 0: arXiv 1303.1960

Paper: Yaroslav Shitov, [*An upper bound for nonnegative
rank*](https://arxiv.org/abs/1303.1960) (2013).

## Decision

No paper-native family clears **G + H + V**. The proposed inverse-generated
nonnegative factorization family passes G and V: sample nonnegative rational
matrices `B,C`, form `A=BC`, and check a submitted pair by exact multiplication.
It fails **H on Track A** because this paper contains no hardness theorem or
hard parameter regime for the resulting planted distribution. It also fails
**H on Track B**. For the rank-three heptagon matrices to which the paper's
main construction applies, the displayed factorization is already the
mechanical certificate-producing algorithm; there is no shorter public route
for a solver to discover.

Implementation therefore stopped before Step 1, as Step 0 requires. No
generator, self-test report, or oracle transcripts were created.

## What the paper actually proves

Section 1 defines the nonnegative rank of a nonnegative matrix `A` as the
smallest `k` for which `A=BC` with both factors entrywise nonnegative. It also
records two easy cases that must not be mistaken for hard families:

- if either classical rank or nonnegative rank is below three, the two ranks
  agree;
- a width-`min(m,n)` factorization is trivial.

The native objects are real nonnegative matrices, slack matrices of polygons,
and their nonnegative factorizations. No graph, finite-field, or integer
surrogate is needed or licensed.

The certificate-producing part of Section 2 is constructive:

- Lemma 2.4 writes down a `7 x 6` nonnegative matrix `F` and a `6 x 7`
  nonnegative matrix `G` for the normalized matrix `V(a1,a2,a3,b1,b2,b3)`
  whenever the displayed middle-sum inequalities hold.
- Lemmas 2.5--2.11 give a rational change of variables, prove its period is
  seven, and show (also using the reversal symmetry of Lemma 2.3) that the
  factorable case must occur.
- Lemma 2.12 normalizes every rank-three `7 x 7` matrix with the cyclic
  heptagon zero pattern by explicit positive row and column scalings.
- Theorem 2.13 concludes that every convex-heptagon slack matrix has
  nonnegative rank at most six.

Section 3 then scales the result by composition, not by introducing a hard
search problem. Theorem 3.1 factors every nonnegative rank-three `7 x n`
matrix through at most six generators. Theorem 3.2 groups rows in sevens and
gives

`rank_+(A) <= ceil(6 min(m,n) / 7)`.

Theorem 3.4 transfers this upper bound to polygon extension complexity through
Yannakakis's slack-matrix theorem. These are upper-bound constructions; the
paper states no computational lower bound for finding the factors and no
average-case or planted-distribution hardness result.

## Mechanical cost versus compact route

### The strongest writable native candidate

The most favorable candidate is: give a normalized `V(psi)` satisfying Lemma
2.4 and ask for its width-six nonnegative factorization. All six parameters are
read directly from matrix entries:

`a1=V[6,3], a2=V[7,3], a3=V[1,3], b1=V[6,5], b2=V[7,5], b3=V[1,5]`

(using the paper's one-based indexing). Substitution into Lemma 2.4 then uses
exactly **12 nontrivial rational arithmetic operations**: eight additions or
subtractions and four divisions. The answer contains **84 rational scalars**.

I measured the direct constructor in CPython 3.11 with `fractions.Fraction`,
50 batches of 1,000 constructions, on the exact conic-derived example obtained
from parameters `t=(4,5,6)` after two of Lemma 2.5's cyclic changes of
variables. Median time was **0.000023227 seconds** per factorization; the
largest batch mean was **0.000037589 seconds**. Exact multiplication confirmed
`FG=V`, and every factor entry was nonnegative.

This gives the required Track B comparison:

| route | exact work | measured time | output |
|---|---:|---:|---:|
| mechanical Lemma 2.4 constructor | 12 rational operations | 23.227 microseconds median | 84 scalars |
| compact route after recognizing the normalized form | the same 12 operations | the same constructor | the same 84 scalars |

The ratio is one. The formula is not merely an efficient alternative to a
short structural solution; it *is* that solution. A construction-aware
in-context attack would therefore succeed on every such instance, so a Track
B G6 panel could not contain four failing attacks honestly.

### Arbitrary heptagon slack matrices do not open a gap

For an arbitrary cyclic heptagon matrix, Lemma 2.12 first applies explicit
diagonal row/column normalizations. One update of Lemma 2.5 costs 22 rational
arithmetic operations, and the transformation is seven-periodic by Lemma 2.8;
the reversal symmetry supplies the other orientation. Carrying a factorization
back through each update just rescales and permutes the 84 factor entries.

On the same conic-derived example, the factorable inequalities occur after two
updates. A prototype performing the parameter updates, rebuilding the 49
determinant entries, and constructing the direct factors measured **0.001461
seconds** per instance over 10,000 repetitions. Counting 44 recurrence
operations, nine additions for the three inequality tests, the 12-operation
formula, the monomial-transform coefficients, and sparse rescaling of the 35
nonzero factor entries gives about **143 exact operations** to carry the
factorization back. The compact route is not shorter: it performs those same
updates and rescalings. Instances requiring more updates grow both counts
together; they do not create a mechanical-versus-compact separation.

Theorem 3.2 does not rescue scaling. A square `d x d` factorization at the
theorem's width has `2*d*ceil(6d/7)` scalar entries. The largest square answer
under 256 atoms is `d=11`, with width 10 and **220 entries**; `d=12` already
requires **264**. The paper's method at `d=11` is one heptagon factorization
plus four singleton rows. Both the mechanical and purported compact routes do
the same output-linear work. Beyond that point both merely grow a certificate
that the benchmark forbids writing. This is not `cap_bound`: there is no latent
short route on the other side of the cap—the two routes remain identical.

## Why inverse generation does not rescue hardness

Inverse generation with arbitrary nonnegative `B,C` is a valid way to know a
certificate, but it detaches hardness from the paper:

- **Track A:** Theorem 3.2 is an upper bound on factor width, not a theorem that
  factor recovery is hard. It supplies no parameter regime or distributional
  claim for products of random nonnegative factors. Worst-case facts about
  nonnegative matrix factorization would not establish hardness of this
  answer-first distribution.
- **Track B:** With unstructured random factors, the planted factors and random
  seed are private. A solver-visible invariant, symmetry, or change of
  variables recovering them in at most 300 operations does not exist in the
  paper. The only honest compact route is to run the same factor-recovery
  computation as the mechanical route. Imposing a low-parameter pattern on
  the factors would make that pattern the direct recovery algorithm, returning
  to the 12-operation failure above.

Thus the prior triage's candidate proves G and V but offers no acceptable
hardness basis under either track.

## Other candidate tasks

| paper result | possible answer | diagnosis |
|---|---|---|
| Theorem 2.13, heptagon slack matrix | width-six factors | G and V pass; H fails on both tracks because Lemmas 2.4--2.12 construct the factors directly |
| Theorem 3.2, general rank-three matrix | factors of width `ceil(6 min(m,n)/7)` | same direct block construction; explicit answer reaches 264 atoms already at `12 x 12` |
| Theorem 3.4, polygon extension | an extended formulation or slack factorization | equivalent certificate through Yannakakis; no new search hardness and a still larger witness |
| output only the upper bound or extension complexity bound | an integer | not a witness for the claimed factorization/existence; attaching the factorization restores the easy constructor |
| hide one heptagon block among decoys | indices plus factors | added haystack search is not a reduction or problem studied in the paper; it would be benchmark-convenience structure, not native coverage |

## Gate diagnosis

| requirement | result |
|---|---|
| G -- generatable | **Passes** by inverse generation, or theorem-backed construction using Lemmas 2.4--2.12. |
| V -- exact witness verification | **Passes** by checking dimensions/nonnegativity and multiplying rational factors exactly. |
| H -- Track A | **Fails.** The paper gives no hardness theorem or hard parameter regime for the generated distribution; its relevant results are constructive upper bounds. |
| H -- Track B | **Fails.** The mechanical and compact routes are the same 12-operation displayed factor formula (or the same roughly 143-operation update/rescale route on the tested nontrivial example). |
| Overall | **Rejected at Step 0.** |

This rejection is not based only on the existence of an efficient algorithm.
It compares that algorithm with the shortest solver-visible route and finds
them identical, while also checking that enlarging the native object merely
lengthens the same certificate and computation.
