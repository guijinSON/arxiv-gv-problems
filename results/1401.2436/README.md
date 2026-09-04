# Verified generator for arXiv:1401.2436

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite field |
| Computational core | CSP/SAT (linear equations over GF(2)) |
| Certificate form | integer tuple: a fixed-weight set of key positions |
| Intuition | change of variables |
| Domain essentiality | licensed reduction |

## Problem and trust model

This generator turns the exact 3XOR-to-graph construction in O'Donnell, Wright,
Wu, and Zhou, [*Hardness of Robust Graph Isomorphism, Lasserre Gaps, and
Asymmetry of Random Graphs*](https://arxiv.org/abs/1401.2436), into a witness
problem.  The solver receives two CFI-style gadget graphs specified succinctly
by 3XOR rows and GF(2) decoder masks.  It must return a short key whose decoded
assignment induces a vertex bijection.  `verify` expands that bijection and
compares the complete integer edge sets exactly.

This is a paper-licensed reduction, not a convenience discretization.  Section
3 defines the ten-vertex constraint gadget and whole-instance graphs; the
Completeness Lemma in Section 4 gives exactly the assignment-to-bijection map
used by the checker.  With every equation satisfied, its epsilon is zero, so
the map is an exact isomorphism.  Section 2 fixes the edge-preservation
normalization and the meaning of alpha-isomorphism.

## Why Track B

The Introduction itself says that satisfiable XOR instances yield to Gaussian
elimination.  The reference algorithm here is exact GF(2) elimination on the
advertised checksum rows: `O(m*k^2)` bit operations.  At the shipping preset it
solved 8/8 instances, with median cost 134,649 counted bit operations and about
0.0010 seconds.  This success is reported separately, as Track B requires.

The compact route cancels the common affine mask, recognizes the 96 rotations
of one circulant basis vector, and applies the transpose of a three-tap map.
Counting fixed-width rotate/XOR operations gives 292, within the no-tool cap,
but it still requires exact work on 96-bit hexadecimal words.  Without that
change of variables, the visible route is dense row reduction.  This module
does **not** claim Theorem 1.2's Track-A average-case hardness: that theorem is
conditional on Feige's R3XOR Hypothesis, and the paper's soundness lemma uses
`m=c*n` with `c >= 10^10`, neither of which describes these finite instances.

Easy cases deliberately avoided or disclosed are also in the Introduction:
basic Weisfeiler--Lehman succeeds on almost all dense `G(n,1/2)` graphs, robust
isomorphism is efficiently solvable for trees, and dense approximate graph
isomorphism has an additive PTAS.  The generated objects are sparse CFI-style
gadget graphs instead.

## Worked demo

This is `render(make_instance(seed=0, **DIFFICULTY["demo"]))` in full:

```text
COMPRESSED ISOMORPHISM OF TWO 3XOR GADGET GRAPHS

All bit arithmetic below is over GF(2): XOR is addition, AND is bitwise AND,
and parity(x) is the number of 1-bits of x modulo 2. Hexadecimal masks have
exactly 6 bits. Bit positions are numbered 1 through 6 from least
significant to most significant.

The instance defines two undirected simple graphs G and H from n=12 Boolean
variables and m=8 equations. Each equation row has the format
"number: i j k | b | r" and means x_i XOR x_j XOR x_k = b. The final mask r
is an exact redundant checksum U_i XOR U_j XOR U_k, included so it may be
recomputed or used directly.

Here are the public variable masks U_i:
  1:1f  2:33  3:10  4:13
  5:18  6:28  7:21  8:2c
  9:2d  10:34  11:37  12:15

Here are the equations:
  1: 3 5 9 | 0 | 25
  2: 2 3 10 | 1 | 17
  3: 5 9 10 | 1 | 01
  4: 2 3 5 | 1 | 3b
  5: 2 6 12 | 1 | 0e
  6: 2 8 9 | 1 | 32
  7: 6 7 12 | 1 | 1c
  8: 4 10 11 | 0 | 10

The graph construction is part of the instance. In G, variable i has two
vertices (i,0) and (i,1), joined by an edge. Equation e on i,j,k has four
vertices (e,a_i,a_j,a_k), one for each bit triple with
a_i XOR a_j XOR a_k=b. Those four vertices form a clique, and each is joined
to the three consistent variable vertices (i,a_i),(j,a_j),(k,a_k).
The graph H is built identically on the same equation triples except that every
right side is 0. Thus each graph has 56 vertices and
156 edges. These definitions specify every vertex and
edge; there are no colors, loops, parallel edges, or omitted edges.

Your answer is a compressed isomorphism key T. It must be a strictly increasing
list of exactly 3 distinct positions from 1..6. Let K have 1-bits
exactly at T, and define tau_i=parity(U_i AND K). The decoded vertex map is
  (i,a) -> (i,a XOR tau_i),
  (e,a_i,a_j,a_k) ->
      (e,a_i XOR tau_i,a_j XOR tau_j,a_k XOR tau_k).
Find T for which this decoded map is a bijection carrying every edge of G to an
edge of H. The checker expands the map and compares the two exact edge sets.
Order in T is therefore fixed, repeats are forbidden, and all bounds are
inclusive.

Give your final answer inside <answer></answer> tags, as comma-separated decimal
integers in strictly increasing order. A format example (not an answer to this
instance) is <answer>1, 7, 12</answer>.
Output nothing else inside the tags.
```

The answer is `<answer>1, 4, 6</answer>`.  `verify(inst, [1, 4, 6])` returns
`(True, "ok")`; dropping the last position returns
`(False, "key must contain exactly 3 positions")`.  A person can solve this
demo by hand because its certificate language contains only `C(6,3)=20`
candidates.

## Difficulty presets

| preset | n | key bits | decoys | equations | graph vertices | answer elements | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 12 | 6 | 1 | 8 | 56 | 3 | hand example |
| easy | 120 | 96 | 2 | 99 | 636 | 48 | **ships; oracle held** |
| medium | 132 | 96 | 10 | 107 | 692 | 48 | available, not needed |
| hard | 148 | 96 | 20 | 117 | 764 | 48 | available, not needed |

Escalation adds eight decoy checksum rows and sixteen ambient variables while
keeping the 48-position answer fixed: it grows the haystack, not the needle.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted answers verify and JSON-round-trip |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | realistic prose/fence/tag response round-trips |
| G4 | 0/200,000 fixed-weight guesses; language size `6,435,067,013,866,298,908,421,603,100` |
| G5 | shipping density 0/200,000; demo has exactly one answer; reference median 134,649 bit operations and 0.0010 s; strongest failing greedy median 921,888 nodes and about 0.075 s |
| G6 | five attacks, all 0/8; Gaussian reference 8/8 as expected |
| G7 | doubled `n=240` instance and fixed-length escalation both verify |
| G8 | 60 invariance and 60 certificate-preservation checks; 20/20 unrelated keys distinct |
| G9 | worst case 145 answer characters, 48 elements, about 37 tokens; compact route 292 exact word operations |

The five failing G6 attacks are per-bit RHS correlation, fixed-weight pair-swap
greedy search, 256 random restarts, raw sparse propagation, and the obvious RHS
prefix ansatz.  Dense shared-distribution masks remove marginal outliers;
constraint shuffling removes positional leakage; decoys and the affine offset
defeat the sparse and prefix routes.

## Oracle loop

| preset | model | seed | solved | reason |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 1650267649 | no | parsed candidate violated equation 1 |
| easy | Google Gemini 3.1 Pro Preview | 878171890 | no | parsed candidate violated equation 2 |
| easy | Anthropic Claude Sonnet 5 | 885503870 | no | exhausted the 32k response budget without a witness |

The bare harness verdict is `hardened`, with zero escalations.

## G9 arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`.  The full structural recipe bought no observed
success, so this run does not show that the oracle failures came from failure to
*discover* the change of variables; exact 96-bit execution and transcription
remain plausible bottlenecks.  Grok timed out once in each extra arm; those rows
are recorded as errors and were redrawn, not counted among the three attempts.

## Use

```python
import gen_1401_2436 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
answer = g.parse_answer("<answer>" + ",".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit examples with:

```bash
bash scripts/emit.sh 1401.2436 20
```

## Caveats

- This is a Track-B compression benchmark, not evidence for distributional
  robust-GI hardness and not an implementation of the paper's noisy R3XOR
  soundness regime.  A solver with ordinary code solves it essentially
  instantly by Gaussian elimination.
- `P(guess)` is conditional on the exact prior stated to the solver: uniform
  fixed-weight sorted keys.  It rules out blind guessing under that prior, not
  algebraic or construction-aware attacks.
- The full graph permutation is deliberately represented by a 48-index decoder
  key to stay writable.  Verification nevertheless expands and checks every
  graph edge, rather than trusting the 3XOR equations alone.
- No external canonical-labeling package or industrial SAT solver was run.  The
  domain-standard exact elimination was implemented and measured; no-tool
  heuristics were tested, but further affine-orbit recognition attacks may
  exist.
- `canonical_key` is a relational 1-WL invariant, not a complete canonical
  labeling algorithm.  It survived variable, equation, within-row, bit-coordinate,
  and composed relabelings and distinguished 20/20 unrelated seeds, but a rare
  collision could over-collapse two distinct instances.
