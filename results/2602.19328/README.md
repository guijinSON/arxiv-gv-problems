# Verified generator for arXiv:2602.19328

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | exact symbolic weighted-edge set |
| Intended intuition | symmetry: a parallel class of affine triples |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 4.1 proof of Theorem 4(ii) |

## What this is and why it is trustworthy

[DasGupta and Kruzan, *On Identifying Critical Network Edges via Analyzing Changes in Shapes (Curvatures)*](https://arxiv.org/abs/2602.19328) define the criticality problem in Section 2.2. This family uses their weighted restricted edge-insertion construction from Section 4.1. The solver receives an exact, compact encoding of a positively weighted graph, a distinguished edge `{U,V}`, and legal unit-weight edges from `T` to set vertices. It must choose exactly `q` insertions that change the distinguished edge's Ollivier-Ricci curvature from negative to strictly positive.

The generator samples a prime-field affine line `y = ax+b` first. Its `q` triples

`(x, ax+b, (a+1)x+b)`

cover each of the three coordinate classes exactly once because `a` is neither `0` nor `-1`. Random triples are added as decoys and all triples are shuffled. Thus the answer is known before the graph exists; the generator never solves its own instance. Averaged over the random line, planted and decoy triples have the same one-triple marginal distribution. Only the joint affine correlation identifies the plant.

Section 4.1's construction gives an exact checker identity. With replication `R=q+4`, `N=3qR` element-copy vertices, and `c` distinct base coordinate labels covered by the selected triples,

`Ric(U,V) = (R*c + q + 4 - N) / (6*(N+n))`.

Consequently the curvature is positive exactly when `c=3q`: the selected triples are an exact cover. Verification is just shape checking, a set union, integer arithmetic, and a strict sign comparison. It uses no float and never reads the planted answer.

This is licensed-reduction coverage, not a claim that the search distribution is a generic network instance. The graph and curvature operation remain explicit, but the paper's maximum-coverage reduction carries the search.

## Why Track B

Theorem 4(ii) proves NP-completeness for weighted restricted insertion even when all weights are in `{1,2,3}` and `b=1`; every generated graph is in that parameter regime. That worst-case theorem does **not** make this planted distribution Track A. This distribution has a disclosed efficient algorithm: hash the displayed `(x,y)` candidates, enumerate affine slopes and intercepts, and test each complete line. Its worst-case cost is `O(n+q^3)` time and `O(n)` space.

At the shipping preset, that reference scan solved 8/8 instances using 33,835 hash probes total (4,229 average, 7,250 maximum) in 0.00847 seconds total. Those thousands of exact lookups are easy for a program but not realistic unaided in the evaluation context. Once a solver visually recognizes the correct parallel class, checking its 73 points takes at most `2q=146` modular operations. That mechanical-versus-compact gap is the Track B claim.

The easy regime deliberately avoided is the paper's unweighted case: Theorems 5, 6, and 11 give feasibility and approximation algorithms for unweighted restricted insertion; Theorem 6 becomes a randomized exact algorithm under `b=1` and property `(spadesuit)`. Merely invoking the paper's NP-completeness result would therefore have been misleading without the Track B disclosure above.

## Worked demo (complete rendered instance)

For `make_instance(n=13, q=5, seed=7)`, `render` produces:

```text
Critical-edge intervention in a weighted graph

For a vertex A, its closed neighborhood consists of A and every adjacent vertex.
Put the uniform probability distribution on each closed neighborhood. For two
adjacent vertices A,B, the earth mover distance EMD(A,B) is the minimum, over all
nonnegative shipments from A's closed neighborhood to B's closed neighborhood,
of the sum of (shipped mass)*(weighted shortest-path distance), with every source
sending its full mass and every destination receiving its full mass. The
Ollivier-Ricci curvature of edge {A,B} is

    Ric(A,B) = 1 - EMD(A,B)/dist(A,B).

The prime is q=5; all coordinate arithmetic below is modulo q.
Vertices are U,V,T; set vertices S0,...,S12; element-copy vertices EX[x,r], EY[y,r], EZ[z,r] for 0<=x,y,z<q and 0<=r<9; and sink vertices D0,...,D293.
The undirected weighted edges are exactly these:
  {U,V} has weight 2 and {U,T} has weight 3.
  V is joined with weight 3 to every set vertex and every element-copy vertex.
  V is joined with weight 1 to every sink vertex.
  Every two distinct set vertices are joined with weight 1.
  If Si has triple (x,y,z), Si is joined with weight 1 to EX[x,r], EY[y,r], and EZ[z,r] for every 0<=r<9.
There are no other edges. Thus there are 135 element-copy vertices and 294 sinks.
The set-vertex triples are:
  S0: (4,0,4)
  S1: (0,2,2)
  S2: (3,0,3)
  S3: (1,2,3)
  S4: (0,4,4)
  S5: (3,3,1)
  S6: (0,1,1)
  S7: (2,2,4)
  S8: (3,1,4)
  S9: (4,3,2)
  S10: (0,0,0)
  S11: (1,4,0)
  S12: (4,1,0)

The distinguished edge is {U,V}. Its initial curvature is exactly
(2-444)/444, which is negative.

Choose exactly 5 DISTINCT set vertices. For every chosen Si, insert the new
undirected edge {T,Si} with weight 1; no other insertion is permitted. The
closed neighborhoods of U and V therefore do not change. Your inserted edges
must make Ric(U,V) strictly positive (zero is not accepted).

Exact checking identity: if c is the number of distinct base labels among
X_x, Y_y, and Z_z occurring in the chosen triples, then the post-insertion
curvature is

    ((5+4)*c + 5+4 - 135) / (6*(135+13)).

This identity is an exact rational equality, not a floating-point approximation.
Indices are 0-based; edge order does not matter; repeats are forbidden.

Give your final answer inside <answer></answer> tags as one JSON object with key
"insertions" and exactly 5 entries ["T","Si",1].
Example shape: <answer>{"insertions": [["T","S0",1],["T","S1",1],["T","S2",1],["T","S3",1],["T","S4",1]]}</answer>
Output nothing else inside the tags.
```

The planted answer is:

```json
{"insertions":[["T","S2",1],["T","S6",1],["T","S7",1],["T","S9",1],["T","S11",1]]}
```

It gives `verify(...) == (True, "ok")`; dropping its last edge gives `(False, "expected exactly 5 insertions, received 4")`. A person can solve this demo on paper by finding five triples with every `x`, `y`, and `z` residue represented exactly once.

## Difficulty presets

| Preset | `n` candidates | prime `q` / answer edges | implicit graph vertices | Status |
|---|---:|---:|---:|---|
| demo | 13 | 5 | 445 | hand-scale illustration |
| easy | 900 | 59 | 36,154 | rejected by oracle loop: 2/3 solved |
| medium | 1,400 | 73 | 54,790 | **ships; 0/3 solved** |
| hard | 1,800 | 83 | 70,390 | reserve rung; not needed |

`escalate` first increases the number of decoys at fixed `q`, so the answer does not grow. Only after that haystack is exhausted does it increase the field size; it reports `cap_bound` before exceeding the 256-atom limit.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified across all presets |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged, fenced, prose-surrounded JSON round-tripped |
| G4 | pass | 0/200,000 uniform legal guesses; exact upper bound `2.904e-18` |
| G5 | pass | demo has exactly 1/1,287 valid answers; shipping reference cost reported |
| G6 | pass | all four no-tool attacks 0/8; affine reference scan 8/8 |
| G7 | pass | doubling `n` from 1,400 to 2,800 raises space from 410 to 484 bits |
| G8 | pass | 20/20 composed relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9(c) | pass | worst case 1,184 chars, about 296 tokens, 219 atoms; intended route 146 operations |

The strongest failing attack was 256 randomized greedy restarts: 2,867,200 candidate scans over eight seeds, 0 successes. Coordinate-frequency outliers, deterministic greedy coverage, and the plausible by-hand slope-one ansatz also scored 0/8.

## Oracle loop

| Preset | Model | Seed | Result | Checker evidence |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 641692132 | failed | covered 139/177 base labels |
| easy | Google Gemini 3.8 Flash | 199804356 | solved | valid witness |
| easy | Google Gemini 3.8 Flash | 245973958 | solved | valid witness |
| medium | Google Gemini 3.8 Flash | 238957208 | failed | covered 138/219 base labels |
| medium | OpenAI GPT-5.6 Terra | 1942758722 | failed | emitted 72 rather than 73 insertions |
| medium | Google Gemini 3.8 Flash | 407897648 | failed | covered 145/219 base labels |

The harness verdict is `hardened` at medium after one escalation.

## G9 diagnostic arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 2/3 | naming the affine-line invariant often unlocks the compact route |
| placebo | 0/3 | prompt-length/register change alone did not help |

Hinted minus placebo is `+0.667`. This supports the claimed `symmetry` intuition: difficulty is primarily recognizing the line, not carrying out 73 modular checks. The third placebo call returned an empty length-limited response and was scored unsolved by the harness, so the three-sample comparison is diagnostic rather than a precise effect estimate.

## Use

```python
from gen_2602_19328 import DIFFICULTY, SHIPPING_DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY[SHIPPING_DIFFICULTY])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 2602.19328 20
```

## Caveats

- This is intentionally Track B. Any solver with a hash table can run the affine scan in milliseconds; it must not be cited as distributional Track A hardness.
- `0/200,000` alone would not establish a probability below `1e-6`. The stronger statement comes from the exact bound: every valid answer uses each `X` coordinate once, hence there are at most `q!` valid selections among `C(n,q)` candidates, or at most `2.904e-18` at shipping size. This bound is conservative and does not estimate how many non-affine exact covers actually occur.
- No commercial ILP/SAT package was benchmarked. The disclosed specialized affine scan is already a faster and more relevant attack on this construction.
- `canonical_key` is a strong degree-and-incidence invariant, not a complete hypergraph-isomorphism canonicalizer. The self-test covers set reorderings, affine coordinate relabellings, `X/Y` swaps, their compositions, witness transport, and unrelated-seed distinctness; adversarial invariant collisions may still exist.
- The graph is handed by exact vertex classes and edge rules rather than materialized as tens of thousands of adjacency rows. Nothing is approximate, but consumers wanting a literal edge list must expand those rules.
- The checker trusts the Section 4.1 transport identity instead of re-solving the earth-mover LP on every candidate. The identity is exact for this graph construction; changing the graph rules would require re-deriving it.
