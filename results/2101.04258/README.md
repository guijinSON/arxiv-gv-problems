# Verified problem generator for arXiv:2101.04258

**Status:** complete. All local gates pass, and the script-owned bare hardening
loop returned `hardened` at the `easy` preset after 0/3 valid oracle witnesses.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | CSP over sparse polynomial coefficients |
| Certificate | polynomial |
| Intended intuition | invariant: finite-field fibre averages preserve one common polynomial translate |
| Domain essentiality | native |
| Reduction | none |

## Problem and construction

Bohman, Liu, and Mubayi's [“Independent sets in hypergraphs omitting an
intersection”](https://arxiv.org/abs/2101.04258) defines an
`(N,k,ell)`-omitting system as a `k`-uniform hypergraph with no two edges
meeting in exactly `ell` vertices. Section 3.2 builds an incidence structure
from low-degree polynomial graphs over a finite field. Section 3.3 replaces
each polynomial fibre by a local `k`-graph whose edges all contain a fixed
`ell+1` point core.

This module uses the `(k,ell)=(6,2)` regime highlighted after Theorem 1.4. The
solver receives a point set `U` in `F_q^2` and affine-line blocks with
three-point cores. Every six points of a block line containing its core form a
hyperedge. Distinct lines meet in at most one point, while two edges from one
block share at least the three core points, so intersection size two is
impossible exactly as in Section 3.3.

Generation is inverse. It first samples `P(x)=c+a*x^e+a*x^(e+1)` and an
exchangeable offset set `D`, then publishes each vertical fibre `P(x)+D`
without revealing that decomposition. Every `P+d` graph lies in `U`. Cores use
at least two offsets, so none is contained in one translated graph; all seven
translates at the shipping preset are independent witnesses. The answer is a
canonical three-term polynomial, and `verify` checks its complete graph by
exact modular evaluation and exact block incidence without reading
`inst["answer"]`.

The high-degree answer polynomial is a compact representation of an
independent vertex set, not one of Section 3.2's degree-one master lines. The
underlying point/line/core hypergraph is the paper's native construction, and
finite-field structure remains essential both to posing and checking the task.

## Why Track B

The paper proves extremal bounds, not average-case computational hardness.
Section 2 explicitly describes random-greedy independent-set search and quotes
the Bennett–Bohman theorem giving regimes where that algorithm efficiently
produces a large witness. A Track A claim would therefore be unsupported.

An exact reference algorithm exists here: average every vertical fibre over
`F_q`, then interpolate the resulting degree-bounded polynomial by Newton
divided differences and try its constant translates. Its complexity is
`O(q*fiber_size+n^2)`. At the shipping `easy` preset, the final self-test
measured **34,373 exact field operations and 0.002373 seconds per instance**
(274,984 operations and 0.018984 seconds across eight).

The compact route notices that only the constant term changes under fibre
averaging. Three fibre averages recover the scale and a power of the displayed
primitive root; a bounded baby-step/giant-step calculation recovers `e`. It
never exceeded **62 exact operations at shipping**. Without that invariant, the
mechanical route interpolates 98 coefficients. This compression gap—not a
complexity claim—is the Track B hardness basis.

## Worked demo

This is the complete `demo`, seed 123:

```text
TRINOMIAL GRAPH IN AN INTERSECTION-OMITTING HYPERGRAPH

All arithmetic below is in the prime field F_11, represented by the
integers 0,...,10; reduce every sum and product modulo 11.
For reference, g=2 is the least positive primitive root
of this field (its nonzero powers run through every nonzero field element).
The point set U is given by its vertical fibres.  A line "x=r: y1 ... ys" lists
exactly the points (r,y1),...,(r,ys) in U.  Orders within those lists do not
matter and repetitions are absent.

Point set U (55 points):
  x=0: 4 9 5 3 7
  x=1: 9 7 5 0 6
  x=2: 5 8 10 6 4
  x=3: 7 6 1 8 10
  x=4: 8 10 6 7 1
  x=5: 5 0 10 1 3
  x=6: 2 3 8 4 6
  x=7: 10 0 5 1 3
  x=8: 7 8 0 9 2
  x=9: 5 0 3 1 10
  x=10: 4 5 3 9 7

The following 1 affine blocks define a 6-uniform hypergraph
H on U.  For block Bi, let Ei be all displayed points satisfying its affine
equation y=a*x+b.  Its three listed core points belong to Ei.  The hyperedges
contributed by Bi are ALL 6-element subsets of Ei that contain all three core
points; H is the union of these hyperedges.  Thus an answer is independent when
it contains no such 6-set.  Distinct blocks are distinct affine lines.  It is
promised that the data below define an (N,6,2)-omitting hypergraph: no two
distinct hyperedges meet in exactly two points.

Blocks:
  B0000: y=1*x+7; core=(9,5) (3,10) (5,1); |fiber|=6

Find a polynomial Q over F_11 satisfying all of the following:
1. Q has degree at most 6, a nonzero constant term, and exactly two
   further nonzero monomial terms.
2. Its full graph {(x,Q(x)) : x in F_11} is contained in U.
3. That graph is an independent set of H.

Represent Q as a JSON array [[coefficient,[exponent]], ...].  Use integer field
representatives 1,...,10 for nonzero coefficients, list exactly
three terms in strictly increasing exponent order, and use exponent lists of
length one.  Exponents are inclusive from 0 through 6; repeats and
omitted zero coefficients are forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format (not necessarily a solution): <answer>[[1,[0]],[1,[1]],[1,[2]]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[4,[0]],[1,[2]],[1,[3]]]</answer>`.

```python
>>> verify(demo, [[4, [0]], [1, [2]], [1, [3]]])
(True, 'ok')
>>> verify(demo, [[4, [0]], [1, [2]]])
(False, 'polynomial must contain exactly three nonzero terms')
```

A person can solve the demo on paper by comparing finite-field fibre averages.
It has 12 valid witnesses among 3,420 structure-aware candidates.

## Difficulty presets

| Preset | Degree bound | Field | Fibre size | Points | Blocks | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 6 | 11 | 5 | 55 | 1 | hand-scale illustration |
| easy | 97 | 101 | 7 | 707 | 80 | **ships; bare oracle held 0/3** |
| medium | 397 | 401 | 9 | 3,609 | 350 | locally verified |
| hard | 997 | 1009 | 9 | 9,081 | 900 | locally verified; not needed |

`SHIPPING_DIFFICULTY` is `easy`. `escalate()` enlarges the field and block
haystack while the answer stays exactly three terms, and returns `cap_bound`
before the compact route would exceed G9(c)'s 300-operation cap. A discarded earlier draft
explicitly stated the translate promise and sampled `e` within 20 of the upper
bound; the oracle solved every named rung it reached. The revised version hides
that promise, samples a broad interior exponent, and includes the corresponding
40-boundary-exponent attack. No pre-revision oracle result is counted here.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 plants, 12/12 JSON round trips, 90 translated witnesses, and all affine audits |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose and fenced JSON round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; candidate space 22,586,256 |
| G5 | pass | shipping sampled density 0; demo exact 12/3,420; baseline 34,373 operations per instance |
| G6 | pass | four attacks each 0/8; interpolation reference algorithm 8/8 |
| G7 | pass | doubled `n=194`, `q=197`, 1,379-point instance builds and verifies |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 30 characters, about 8 tokens, 6 atoms, 62 exact operations |

The G6 attacks are field-mean-as-a-vertex, integer-median interpolation, 256
structure-aware random restarts, and the lowest/highest 20 exponent scan. The
successful reference interpolation algorithm is outside `attacks`, as Track B
requires.

## Oracle loop and G9 diagnostics

The revised bare loop used the two-vendor pool currently configured by
`scripts/harden.py` and returned `hardened` at `easy` without escalation:

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 1378577901 | Gemini 3.8 Flash | failed | emitted no answer before its response-length limit |
| easy | 1497475688 | GPT-5.6 Terra | failed | parsed polynomial had a graph point absent from `U` at `x=1` |
| easy | 414461929 | Gemini 3.8 Flash | failed | reasoning contained no parseable final answer |

| G9 arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0 / 3 | held at shipping |
| structural hint | 1 / 3 | one valid witness; diagnostic verdict `too_easy` |
| placebo hint | 1 / 3 | one valid witness |

The hinted-minus-placebo difference is `0.0`: in this three-sample diagnostic,
the structural sentence bought no measured improvement over merely appending a
similarly styled sentence. This may reflect a weak hint or sampling variance;
it does not support attributing the observed lift over bare to the stated
invariant. Answer size is 30 characters / 8 estimated tokens / 6 atoms, and the
intended route is at most 62 operations.

## Use

```python
from gen_2101_04258 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
candidate = parse_answer('<answer>[[1,[0]],[2,[3]],[4,[4]]]</answer>')
ok, reason = verify(inst, candidate)
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 2101.04258 20
```

## Caveats

This is a structured restriction of Section 3's construction, not the random
`U` distribution used to prove Theorem 1.4's upper bound; it is no evidence for
average-case hardness of that theorem. With a sandbox, the disclosed reference
algorithm solves it in fractions of a second. The 0/200,000 result samples
uniformly from trinomials already satisfying the obvious `x=0` and `x=1`
membership constraints; it neither proves a zero solution density nor models
informed algebraic guesses.

No production CAS, sparse-interpolation package, Gröbner-basis method, or
Reed–Solomon list-recovery implementation was tested. The shipping rendering is
9,545 characters for seed 0 and consumed about 6,758 prompt tokens in one oracle
call, so some failures may reflect scanning burden even though the intended
route uses only three fibres. One bare failure exhausted its response-length
budget without emitting an answer, which is weaker evidence than a checked
wrong witness. The canonical key uses color refinement rather than exact
incidence-structure isomorphism, so theoretical collisions remain possible.

The module is standard-library-only; it does not need `gvlib` because all
certificate arithmetic is over a prime field.
