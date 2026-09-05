# Convex-polygon cover generator for arXiv:1504.05476

Status: **verified and hardened**. The family passes G1–G8 and the gated G9(c)
caps. At the shipping preset, all three bare oracle attempts returned no valid
witness; both diagnostic hint arms also finished 0/3. One bare Gemini attempt
used its response budget without emitting an answer, while the other two bare
attempts emitted parseable but invalid covers.

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | rational exact (integer coordinates) |
| Computational core | CSP/SAT |
| Certificate | integer tuple of polygon identifiers |
| Intuition | change of variables: fixed-width base-3 digit reversal exposes affine maps |
| Domain essentiality | `licensed_reduction` |
| Reduction | paper-licensed, Section 5.1 / Theorem 1.9 |

This is representational coverage, not essential native-geometry coverage: the
solver is handed the paper's exact points and convex polygons and the checker
does exact containment, but after the convexity observation the search is a
cyclic CSP. The paper itself licenses that representation by placing points on
a parabola so arbitrary set incidences become convex-polygon incidences.

## Problem and provenance

The solver receives exact integer-coordinate clients on an invertible affine
image of a parabola and a family of closed convex polygons. It must name exactly
`k` polygons covering every client. This is the geometric construction in
Section 5.1 and the proof of Theorem 1.9 of Marx and Pilipczuk,
[“Optimal parameterized algorithms for planar facility location problems using
Voronoi diagrams”](https://arxiv.org/abs/1504.05476). A convex polygon through a
chosen subset of the parabola points contains exactly those points. Verification
uses integer orientations and never reads the planted answer.

Section 3.1 defines the paper's general problem with exactly `k` normal objects.
The generated family instead uses Theorem 1.9's decision problem: cover all
points with exactly `k` unrestricted convex polygons. Theorems 1.6 and 1.7 give
`n^O(sqrt(k))` algorithms for covering by disks and axis-parallel squares, and
Theorem 1.5 handles packing arbitrary polygons; those easier ball-like or packing
regimes do not include unrestricted convex-polygon covering. Theorem 1.9 rules
out `f(k) N^(k-epsilon)` algorithms for the latter under SETH in general.

This distribution does **not** inherit that worst-case claim. It is Track B.
For boundary `i`, polygon `C(i,x)` omits `B(i,x)` and the successor polygon
contains `B(i,g_i(y))`, so a cover satisfies `x_i=g_i(x_s(i))`. The generator
samples a cover first, constructs affine maps in hidden coordinates around it,
and conjugates every map by fixed-width ternary digit reversal. Each of the three
cycles has composed slope 2, hence exactly one fixed point.

The honest reference algorithm inverts all displayed tables and tries each start
around each cycle in `O(kn)` time. At shipping parameters
`n=729,k=18`, the measured seed used 19,596 indexed operations and 0.010 seconds
(26,244 operations in the worst case). Recognizing the common digit reversal
reduces the task to 108 exact arithmetic operations plus 54 reversals of six
ternary digits. That compression gap—not distributional NP-hardness—is the
claimed difficulty.

## Worked demo (`n=9, k=3, seed=11`)

The demo is hand-solvable: each displayed one-group cycle asks for the fixed
point of one nine-entry permutation.

```text
Convex-polygon point cover (all arithmetic is exact)

Let n=9, k=3, and L=31.  The modulus n is a power of 3.  Start with parabola points
P_j=(jL,j^2) for every integer 0 <= j <= L, and the apex A=(0,L^2).
Apply the same affine map
    T(x,y)=(-1x-2y+61, 4x+3y+57)
to every point.  Its determinant is 5, so it is invertible.  The
clients to cover are all transformed points T(P_j); T(A) is not a client.

For 0 <= i < k and 0 <= z < n, define client names
    G_i     = T(P_(1+i(n+1)))
    B_i,z   = T(P_(2+i(n+1)+z)).
The group-successor map s(i) is defined by these three directed cycles:
    0 -> 0
    1 -> 1
    2 -> 2
Let p(i) denote the predecessor of i in its displayed cycle.  All index bounds
above are inclusive where <= is written; all i and z indices are zero-based.

There are kn candidate closed convex polygons C(i,x), one for each
0 <= i < k and 0 <= x < n.  C(i,x) is the convex hull of these exact points:
    T(A), T(P_0), T(P_L), G_i,
    every B_i,z with z != x, and
    the one point B_p(i),g_p(i)(x).
Equivalently, put those vertices in increasing P-index order around the lower
chain, with T(A) closing the polygon.  Boundary points count as covered.
No other points are polygon vertices.  The tables defining the permutations
g_i are below.  Each table is listed at inputs 0,1,...,n-1 even though the
table blocks themselves may appear in any order.

g_1(0),...,g_1(8):
      3 5 4 1 0 2 7 6 8
g_2(0),...,g_2(8):
      6 8 7 4 3 5 2 1 0
g_0(0),...,g_0(8):
      6 8 7 4 3 5 2 1 0

Select exactly k distinct polygons whose union covers every client T(P_j).
The answer is unordered.  A valid cover necessarily selects one polygon from
each group i, but you must give all k concrete polygon identifiers.

Give your final answer inside <answer></answer> tags as comma-separated i:x
pairs, with exactly one pair for every i=0,...,2; x is in 0,...,8.
Example format (showing the required shape, not a claimed cover):
<answer>0:0, 1:0, 2:0</answer>
Output nothing else inside the tags.
```

Answer: `<answer>0:5, 1:8, 2:5</answer>`.

`verify(inst, [[0,5],[1,8],[2,5]])` returns `(True, "ok")`.
Changing `0:5` to `0:6` returns
`(False, "boundary 0 client B_0,6 is uncovered")`.

## Difficulty and gates

`easy` ships. Escalation triples the number of decoy labels while the answer
stays 18 pairs.

| preset | `n` | `k` | rendered size at seed 1 | status |
|---|---:|---:|---:|---|
| demo | 9 | 3 | 2,005 chars | hand-solvable |
| easy | 729 | 18 | 55,868 chars | **ships; bare oracle 0/3** |
| medium | 2,187 | 18 | 187,846 chars | not needed by hardening loop |
| hard | 6,561 | 18 | 598,355 chars | not needed by hardening loop |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified; 12/12 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | prose/fence/tag response round-tripped |
| G4 | 0/200,000 informed guesses; language size `729^3=387,420,489` |
| G5 | one exact demo solution; one analytic shipping solution; reference 19,596 operations / measured wall time in `selftest_report.json` |
| G6 | five attacks at 0/8; reference propagation solved 8/8 |
| G7 | `n=2187` built and verified with unchanged witness length |
| G8 | 60/60 invariant and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 153 chars, 39 estimated tokens, 36 atoms, 108 arithmetic operations + 54 digit reversals |

A separate exact audit materialized full convex hulls and agreed with the
optimized containment predicate on 154,980/154,980 polygon/client tests.

## Oracle loop and G9 arms

The earlier raw-affine design was solved by both vendors at `n=1009`, `2003`,
`4001`, and by one oracle at escalated `n=8009`; table length alone did not hide
its constant differences. That run motivated the ternary conjugation and the
new raw-affine attack. The current, redesigned run is:

| arm | scored solves/attempts | script-owned result |
|---|---:|---|
| bare | 0/3 | hardened at `easy`; two invalid covers and one empty length-limited response |
| structural hint | 0/3 | hardened diagnostic |
| placebo hint | 0/3 | hardened diagnostic |

Hinted-minus-placebo is `0.0`. The structural sentence bought no measured
advantage over the placebo in this three-attempt sample. That does not disprove
the change-of-variables interpretation—the hinted replies began using ternary
reversal—but it shows that naming the invariant alone did not make the remaining
exact work reliably executable in context.

## Use

```python
import random
import gen_1504_05476 as g

inst = g.make_instance(seed=11, **g.DIFFICULTY["demo"])
question = g.render(inst)
answer = g.parse_answer("<answer>0:5, 1:8, 2:5</answer>")
assert g.verify(inst, answer) == (True, "ok")
candidate = g.random_candidate(inst, random.Random(7))
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 1504.05476 20 easy
```

The module is standard-library-only; it does not need `gvlib`.

## Caveats

The `0/200,000` estimate samples one uniform start per cycle and propagates all
non-closing equations. It therefore measures the informed `n^3` prior, not the
naive `n^18` space and not the probability of recognizing ternary digit
reversal. These instances are easy with code by design; the reference solver is
why this is Track B. The tested attacks were equal polygon size, zero-start
greedy propagation, eight random propagated starts, constant/index guesses, and
fitting affine maps directly to raw table entries. A generic ILP solver was not
run; exact functional-CSP propagation is more direct for this distribution.

The ternary relabelling was recognized partway through by some diagnostic
replies, so more attempts or a larger response budget could change the 0/3
estimate. In particular, one bare Gemini call emitted no answer after exhausting
its response budget; the bare claim therefore rests most strongly on the two
parseable invalid covers. The canonical key normalizes declaration order and
global affine coordinate maps but not arbitrary incidence-graph isomorphism.
Polygons are specified by exact vertex formulas rather than millions of repeated
coordinates; `render` defines them fully and `verify` performs exact geometric
containment. The compact-route count treats a fixed-width ternary digit reversal
as a symbolic relabelling and records the 54 reversals separately from the 108
exact modular-arithmetic operations; counting digit extraction as arithmetic
would exceed G9(c), so this convention is a material suitability caveat.
