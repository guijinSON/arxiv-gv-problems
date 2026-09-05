# Tropical cycle-closure determinant generator (arXiv:1303.6478)

> Build status: the generator and every local gate pass, and the script-owned
> bare oracle loop returned **`hardened` at `n=96`**.  The structural-hint and
> placebo diagnostics remain unmeasured because the bare run consumed the
> configured OpenRouter key limit.  Their script-owned error transcripts are
> retained; no API error is counted as a model failure.

## Profile

| field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | integer lattice |
| computational core | graph |
| certificate form | exact symbolic prime-exponent vector |
| intuition | invariant: a co-tree minor is an edge-weight product despite basis scrambling |
| domain essentiality | licensed reduction |
| reduction | paper-licensed by Definition 2.16 and Proposition 2.24 |

## The problem and why the local result is trustworthy

This family comes from Buchholz and Markwig, [*Tropical covers of curves and
their moduli spaces*](https://arxiv.org/abs/1303.6478).  A solver receives a
weighted trivalent tropical cover of the tripod-shaped tropical line, a
spanning tree, and a dense integral matrix representing the associated
cycle-closure minor after integral basis changes.  It must return the prime
exponents of the absolute determinant.

The generator makes a chain of balanced diamonds.  Every finite source length
is the exact rational target distance divided by its edge weight.  The center
has genus 29 and profile `u=(60), v=(1,59), w=(60)`; every other vertex is
trivalent, genus zero, and has RH-number one.  Thus the object is a genuine
cover under Definition 2.2, not a graph analogue.  `verify` independently
checks connectivity, genus, end profiles, slopes, balancing, RH labels, the
spanning-tree complement, the dense determinant by Bareiss elimination, and
the proposed prime factorization.  It never reads `inst["answer"]`.

Generation is by composition of identities.  In the fundamental-cycle basis,
the selected minor is diagonal with the co-tree edge weights.  Unit triangular
integer matrices change its two lattice bases and preserve the absolute
determinant.  The answer is therefore tallied before the dense matrix is made;
the generator never solves its emitted matrix.  Definitions 2.16 and 2.19
define the cycle equations and their lattice index.  The graph-theoretic
argument in the proof of Proposition 2.24 gives the spanning-tree minor
identity; although the proposition's cone-weight comparison is stated for
rational covers, that part of its proof uses only the connected graph and its
cycle basis.  Lemma 3.2 places the same lattice factors in the branch-map
multiplicity.  The profile therefore records a **paper-licensed reduction**:
the cover is present and fully checked, but the solver's actual search is the
weighted-graph/co-tree calculation authorized by those results.  It is not
claimed as fully native algebraic-geometry coverage.

## Track B hardness

The paper does not prove a complexity-theoretic hardness result, so Track A
would be unjustified.  The disclosed general route is fraction-free Bareiss
elimination, `O(n^3)` exact integer arithmetic, followed by division over the
fixed prime basis.  At shipping `n=96`, the eight-seed reference panel solved
8/8 and used **1,161,484 counted exact operations** per instance, averaging
**1.103 seconds** in the final local panel.  This is easy with a program and not executable by hand from
a dense 96×96 matrix.

The compact route uses the minor argument in the proof of Proposition 2.24:
integral basis changes do not alter the absolute determinant, while the
fundamental-cycle/co-tree matrix has one edge weight per pivot.  Tallying the
96 named co-tree primes takes at most 128 small exact operations.  Section
3.1's one-dimensional star resolutions were
avoided as an easy regime: there a transposition merely cuts or joins cycles.
Likewise, once a full combinatorial type and branch images are supplied, its
metric lengths are direct distance/weight evaluations; that is why the prior
“recover lengths” triage was not used.

## Worked demo (complete rendered instance)

This is `make_instance(n=4, mix_bound=1, seed=2)`.  A person can solve it on
paper: ignore the scrambled determinant, take the listed co-tree weights
`53,17,29,17`, and tally their prime exponents.

```text
Tropical cycle-closure determinant

The target tropical line is a tripod with center c and rays u, v, w.  A source
vertex mapped to c has the three ray directions; a source vertex at a positive
coordinate on u has a left and a right direction.  Every finite source edge is
mapped linearly to its listed ray with positive integer slope called its weight.
Its target distance equals weight times source length.  At each source vertex,
the sums of adjacent weights in every target direction must agree; their common
value is the local degree.  The Riemann-Hurwitz number is

  r(V) = valence(V) + 2*genus(V) - 2
         - local_degree(V)*(target_valence-2).

It must be nonnegative and equal the number of labels at V.  Ends have infinite
length.  These rules define the tropical cover below; all integers and rational
lengths are exact.  Vertex and edge identifiers are zero-based labels only.

Degree: 60
Source genus: 33
Ramification profile: u=[60], v=[1, 59], w=[60]

VERTICES
V0 target=c pos=0/1 genus=29 labels=-
V1 target=u pos=1/1 genus=0 labels=1
V2 target=u pos=2/1 genus=0 labels=2
V3 target=u pos=3/1 genus=0 labels=3
V4 target=u pos=4/1 genus=0 labels=4
V5 target=u pos=5/1 genus=0 labels=5
V6 target=u pos=6/1 genus=0 labels=6
V7 target=u pos=7/1 genus=0 labels=7
V8 target=u pos=8/1 genus=0 labels=8

EDGES
E0 V0 END ray=v weight=1 length=infinity
E1 V0 END ray=v weight=59 length=infinity
E2 V0 END ray=w weight=60 length=infinity
E3 V0 V1 ray=u weight=60 length=1/60
E4 V1 V2 ray=u weight=53 length=1/53
E5 V1 V2 ray=u weight=7 length=1/7
E6 V2 V3 ray=u weight=60 length=1/60
E7 V3 V4 ray=u weight=43 length=1/43
E8 V3 V4 ray=u weight=17 length=1/17
E9 V4 V5 ray=u weight=60 length=1/60
E10 V5 V6 ray=u weight=29 length=1/29
E11 V5 V6 ray=u weight=31 length=1/31
E12 V6 V7 ray=u weight=60 length=1/60
E13 V7 V8 ray=u weight=43 length=1/43
E14 V7 V8 ray=u weight=17 length=1/17
E15 V8 END ray=u weight=60 length=infinity

Delete the following finite edges to obtain the stated spanning tree T:
co-tree edges = E4, E8, E10, E14
Equivalently, the finite edges of T are:
tree edges = E3, E5, E6, E7, E9, E11, E12, E13

For each integral cycle, its closure equation is the signed sum of
weight(edge)*length(edge).  Restrict the cycle-closure homomorphism to the
co-tree edge lattice.  An integral lattice basis means a basis over the
integers; a change between two such bases has determinant +1 or -1.  The
following 4 by 4 integer matrix M represents that restricted
homomorphism after independent changes of integral lattice bases in its domain
and codomain:

MATRIX M (one row per line)
53 53 0 53
53 70 17 53
-53 -36 46 -24
53 36 -17 70

Find the exact prime factorization of abs(det(M)).  Use this fixed prime basis:

[7, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]

Your answer must be a JSON list [e0,...,e11] of exactly 12 integers.  Each ei is
inclusive in 0..4, their sum must be exactly 4, and
abs(det(M)) must equal product(prime_basis[i]**ei).  Order is the displayed
prime-basis order; repeats and any other primes are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON integer list.
Example of syntax only (not the answer): <answer>[4,0,0,0,0,0,0,0,0,0,0,0]</answer>
Output nothing else inside the tags.
```

Answer:

```text
<answer>[0,0,2,0,0,1,0,0,0,0,0,1]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Dropping its last
exponent returns `(False, "expected 12 exponents, got 11")`.

## Difficulty presets

| preset | cycles / matrix size | candidate space | Bareiss updates | rendered chars at seed 1 | ships? |
|---|---:|---:|---:|---:|---|
| demo | 4 | 1,365 | 56 | 3,256 | no; hand example |
| easy | 16 | 13,037,895 | 4,960 | 6,640 | no |
| medium | 48 | 279,871,768,995 | 142,880 | 21,002 | no |
| hard | 96 | 309,847,743,777,845 | 1,161,280 | 58,466 | **yes; bare loop hardened** |

No preset was rejected by a local gate.  `escalate` keeps adding 64 cycles and,
up to its declared cap, raises the coefficient-mixing range, all at a fixed
12-element answer length; it grows the matrix haystack without lengthening the
witness.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset×seed planted witnesses; JSON round-trip |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose plus a fenced JSON answer round-trips |
| G4 | pass | 0/200,000 structure-aware guesses; exact density 3.2274e-15 |
| G5 | pass | one exact answer among 309,847,743,777,845; strongest failing restart: 32,768 candidates / 1.436 s over 8 seeds |
| G6 | pass | 7 attacks, each 0/8; Bareiss reference and compact route each 8/8 |
| G7 | pass | doubled `n=192` builds and verifies; 36,864 matrix entries |
| G8 | pass | 20/20 composed invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | shipping sample 28 chars/~7 tokens, exact worst case 34 chars/~9 tokens, 12 atoms; 128 intended operations |

The exact numbers are in `selftest_report.json`.

## Oracle loop and G9 arms

The bare harness used both configured vendors.  `easy` was solved 3/3,
`medium` 2/3, and `hard` 0/3.  Every hard reply parsed to a 12-entry vector and
failed the exact determinant comparison, so the held rung is not a parser
artifact.

| bare preset | scored solved/attempts | result |
|---|---:|---|
| easy (`n=16`) | 3/3 | defeated; escalated |
| medium (`n=48`) | 2/3 | defeated; escalated |
| hard (`n=96`) | 0/3 | **held / hardened** |

| preset | seed | model | solved? | exact grading result |
|---|---:|---|---|---|
| easy | 522916388 | Gemini 3.8 Flash | yes | `ok` |
| easy | 1535740967 | GPT-5.6 Terra | yes | `ok` |
| easy | 1730217808 | Gemini 3.8 Flash | yes | `ok` |
| medium | 163563223 | Gemini 3.8 Flash | yes | `ok` |
| medium | 980532386 | GPT-5.6 Terra | no | factorization did not equal `abs(det(M))` |
| medium | 286240099 | Gemini 3.8 Flash | yes | `ok` |
| hard | 1031526510 | GPT-5.6 Terra | no | factorization did not equal `abs(det(M))` |
| hard | 1476236660 | Gemini 3.8 Flash | no | factorization did not equal `abs(det(M))` |
| hard | 2105823155 | GPT-5.6 Terra | no | factorization did not equal `abs(det(M))` |

| G9 arm at shipping | scored solved/attempts | API errors | result |
|---|---:|---:|---|
| bare | 0/3 | 0 | hardened |
| structural hint | 0/0 | 4 | aborted: key limit exceeded |
| placebo hint | 0/0 | 4 | aborted: key limit exceeded |

Thus `hinted − placebo` is not measurable and no conclusion about the claimed
invariant intuition is warranted yet.  Rerun the two missing arms with a
replenished or replacement OpenRouter key; do not treat the retained error
transcripts as model failures.  The answer is 28 characters / 12 atoms on the
shipping sample (34 characters worst case), and the intended route uses 128
exact operations.

## Use

From the repository root:

```python
import importlib.util
import json

spec = importlib.util.spec_from_file_location(
    "g", "results/1303.6478/gen_1303_6478.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=2, **g.DIFFICULTY["demo"])
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Because Python package components cannot normally start with digits, loading by
`importlib.util.spec_from_file_location` is the portable import route used by
the repository scripts.  Emit only after the oracle blocker is cleared:

```bash
bash scripts/emit.sh 1303.6478 20 hard
```

## Caveats

- Recognizing the co-tree argument in the proof of Proposition 2.24 makes the
  task intentionally easy: it becomes a 96-item frequency tally.  This is
  Track B, not a structural-hardness claim.
- The 0/200,000 guess result is uniform over weak compositions satisfying every
  stated shape and sum constraint.  It says nothing about a solver that uses
  the co-tree invariant or statistical priors over the generator's prime pairs.
- The panel tried equal counts, smaller-branch selection, diagonal valuations,
  row and column contents, first-nonzero-column factors, and 4,096 random
  restarts per seed.  It did not test a CAS Smith normal form, modular
  determinant/CRT, or LLL; Bareiss is the successful exact reference instead.
- The proof of Proposition 2.24 explicitly changes the cycle basis.  This
  generator also expresses the restricted co-tree lattice in a changed integral
  domain basis; determinant invariance under that second basis change is standard
  lattice linear algebra, not a separately numbered result in the paper.
- The benchmark isolates the lattice-minor ingredient of the paper, not the
  full enumeration of branch-map fibers or tropical Hurwitz numbers.
- The bare two-vendor hardness claim is verified by the current harness.  The
  structural-hint and placebo comparison remains unverified until the
  OpenRouter key limit is restored.
