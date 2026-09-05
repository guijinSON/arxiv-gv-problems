# Point-in-Cone witness generator for arXiv:2307.00406

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | integer lattice |
| Computational core | exact linear algebra |
| Certificate | integer tuple: sparse nonnegative cone multiplicities |
| Intended intuition | decomposition: rank one plus odd-cycle incidence |
| Domain essentiality | native |
| Reduction | none; the solver receives the paper's bounded polytope and cone target |

This module instantiates Kowalik, Lassota, Majewski, Pilipczuk and Sokołowski,
[*Detecting Points in Integer Cones of Polytopes is Double-Exponentially
Hard*](https://arxiv.org/abs/2307.00406). The solver receives a bounded
integer-inequality polytope `P` and a target `q`, both in the native form of
Point in Cone. It must give multiplicities of lattice points of `P` whose exact
weighted sum is `q`. Verification evaluates the paper's inequalities and all
coordinates of the sum using integers only.

Generation is inverse. The multiplicities are sampled first, a carry-free
base-`B` height table is formed around them, and Section 3 Claim 2's
bit-complement construction completes them to a cone witness. Claim 1 proves
that the displayed inequalities have exactly the tabulated lattice points.
No manufactured instance is solved during generation. The module is
standard-library-only; it needs no optional `gvlib` component.

## Why Track B

Theorem 1 is a worst-case ETH lower bound for Point in Cone obtained from
Subset Sum with Multiplicities in the regime `d = O(log n)`,
`t <= 2^O(n)`, and encoding size `O(n log n log t)`. It does not imply
average-case hardness for this inverse-planted distribution, so this module
makes no Track A claim. Section 1 also gives the
Goemans–Rothvoss `enc(P)^(2^O(d))` algorithm and explicitly notes that Theorem
1 does not exclude an FPT algorithm.

An efficient distribution-specific algorithm exists and is reported openly:
decode the given heights into digits and apply dense fraction-free Gaussian
elimination. It is `O(n^3)` and used 96,965 exact operations and 0.0048 seconds
on the recorded shipping instance; across the eight G6 seeds it solved 8/8 in
775,720 operations and 0.0381 seconds total. That is easy for a computer and
far beyond unaided hand execution.

The compact route recognizes that the digit matrix is a rank-one matrix plus
a scaled, randomly relabelled odd-cycle incidence matrix. The calibration row
gives the common scalar. Each other row gives the sum of the two coefficients
at one edge; alternating edge sums around an odd cycle recovers one coefficient
and subtraction propagates the rest. With the final complement filler, this is
bounded by 248 exact arithmetic operations at `n=41`.

## Worked demo

This is `make_instance(n=5, coeff_max=3, factor_max=3, seed=7)` in full:

```text
POINT IN AN INTEGER CONE — EXACT WITNESS

Let d=4. For i=0,...,15, let chi_i be the length-4
binary expansion of i, least-significant bit first. Define the integer
height h_i as follows. The 5 nonzero heights are shown below in base B;
here n=5, B=1000, and a digit list [z0,...,z5] means
the exact integer sum z_r*B^r over r=0,...,5.
Every height omitted from the table is exactly zero.
Digits are little-endian and every displayed digit is in 0,...,B-1.

Active height digit lists:
h_1: 1 2 115 3 2 115
h_2: 1 2 115 3 115 2
h_3: 1 2 2 116 2 115
h_4: 1 115 2 3 115 2
h_5: 2 117 4 119 4 4

The target digit list is: 11 474 587 259 700 361
It defines T=sum target_digit_r*B^r exactly. The cone target is
q=(T,T,...,T) in Z^(d+1), with d+1 coordinates.

The bounded polytope P is the set of real (x_0,...,x_(d-1),y)
satisfying these integer inequalities:
  0 <= x_j <= 1 for every j=0,...,d-1, and 0 <= y <= T;
  for every i=0,...,2^d-1, define
    D_i(x) = T*sum(x_j where bit j of i is 0)
             + T*sum(1-x_j where bit j of i is 1),
  and require y + D_i(x) >= h_i and
              T - y + D_i(x) >= T - h_i.
Every sum over j uses j=0,...,d-1. These inequalities imply exactly
P intersect Z^(d+1) = {(chi_i,h_i): i=0,...,2^d-1}.

Find a sparse nonnegative-integer cone certificate for q. Output a JSON
list of [i,m] pairs, meaning m copies of the lattice point (chi_i,h_i).
Use this canonical form: for every active i=1,...,5 choose an integer
c_i in the inclusive range 1..3, include both [i,c_i]
and [15-i,c_i], and include the one filler term
[15,T-sum(c_i)]. Thus the answer has exactly 11 pairs.
The filler multiplicity must be positive. No other index may appear, pair
order does not matter, and indices may occur at most once. The weighted
sum of the listed points must equal q exactly in every coordinate.

Give your final answer inside <answer></answer> tags as a JSON list of
two-integer lists. Syntax-only example: <answer>[[1,2],[6,2],[7,99]]</answer>
Output nothing else inside the tags.
```

The answer is:

```json
[[1,2],[2,3],[3,1],[4,3],[5,1],[10,1],[11,3],[12,1],[13,3],[14,2],[15,361700259587474001]]
```

`verify(inst, answer)` returns `(True, "ok")`. Removing the final pair returns
`(False, "certificate must contain exactly 11 terms")`. A person can solve
this demo on paper: row 0 is the calibration row, the two exceptional entries
in each other row reveal a five-cycle, and its five adjacent sums determine the
five coefficients.

## Presets

| Preset | n | coefficient bound | factor bound | canonical search space | compact operations |
|---|---:|---:|---:|---:|---:|
| demo | 5 | 3 | 3 | `3^5` | 32 |
| easy | 25 | 9 | 5 | `9^25` | 152 |
| medium | 33 | 15 | 6 | `15^33` | 200 |
| **hard (provisional shipping)** | **41** | **31** | **7** | **`31^41`** | **248** |

An earlier direct one-spike-per-row version was solved by all three scored
easy-preset oracle calls. That version was discarded and replaced by the
odd-cycle construction above. The current version has not been scored because
the OpenRouter key became exhausted before its run; `hard` is therefore only a
provisional shipping preset, not a harness-certified one.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verify and are JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced JSON with surrounding prose round-trips |
| G4 | pass | 0/200,000 structure-aware guesses; exact space `31^41` |
| G5 | pass | exact canonical count 1; rank 41; no-carry slack 57,343; compact route verified in 248 operations; baseline 96,965 operations / 0.0048 s |
| G6 | pass | four attacks each 0/8; dense reference algorithm solves 8/8 |
| G7 | pass | doubled `n=82` instance builds and verifies; entropy 204 to 407 bits |
| G8 | pass | 40 coordinate-permutation checks, 40 carried witnesses, and 20/20 unrelated keys distinct |
| G9(c) | pass | over 10,000 seeds: at most 888 characters, 499 lexer-estimated tokens, 166 atoms, and 248 intended operations |

## Oracle loop and G9 arms

The harness-owned files contain four redraws per arm, all HTTP 403
`Key limit exceeded`. API errors are not attempts and are not model failures.

| Arm | Preset | Seeds | Scored | API errors | Solved/attempts | Verdict |
|---|---|---|---:|---:|---:|---|
| bare | easy | 232945628, 1140269399, 949494112, 1405663878 | 0 | 4 | 0/0 | unavailable |
| structural hint | hard | 78335450, 1622264126, 851853792, 1530800293 | 0 | 4 | 0/0 | unavailable |
| placebo hint | hard | 904826242, 525134069, 590321557, 1122131076 | 0 | 4 | 0/0 | unavailable |

`hinted - placebo` is undefined, so these arms support no conclusion about the
decomposition intuition. The three runs must be repeated after OpenRouter
capacity is restored. Their transcripts are retained solely as evidence of the
external blocker.

## Use

```python
from gen_2307_00406 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
question = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, after a successful oracle rerun:

```bash
bash scripts/emit.sh 2307.00406 20 hard
```

## Caveats

- This is deliberately Track B. A CAS, dense elimination, or implementation of
  the displayed odd-cycle decomposition makes every instance easy. The family
  tests recognition and no-tool execution, not the paper's worst-case lower
  bound.
- The `0/200,000` guess rate is conditional on the canonical complement-form
  prior. It already enforces all binary-coordinate equations, equal complement
  multiplicities, positivity, bounds, and the filler rule. It does not estimate
  density among arbitrary sparse cone sums.
- Uniqueness is for the bounded canonical certificate language. The unrestricted
  cone has irrelevant variants such as adding copies of the zero point `p_0`;
  the output contract intentionally excludes them.
- The failed panel did not run a general ILP solver or the full
  Goemans–Rothvoss algorithm. It did run the stronger distribution-specific
  dense exact solve separately, which succeeds as Track B requires.
- `canonical_key` is invariant under permutations of the first `d` binary
  coordinates and support order. It is not a canonical form under arbitrary
  unimodular changes of ambient lattice basis.
- Most importantly, Step 4 remains externally blocked. `.meta.json` has no
  `harden_verdict`; nothing here claims the current odd-cycle family defeated
  the oracle pool.
