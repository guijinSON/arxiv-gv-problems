# Compressed bounded Kempe sequences (arXiv:2401.06027)

This generator turns Ohsugi and Tsuchiya’s [*Examining Kempe equivalence via commutative algebra*](https://arxiv.org/abs/2401.06027) into a witness problem. The solver receives two compactly described colorings of a star and must return a cyclic ordering of the ordinary colors. That ordering expands deterministically into singleton-leaf Kempe switchings followed by center-component switchings. `verify` checks the ordering, symbolically replays every group of switches, checks the exact move count, and compares the resulting center and leaf-class colors with the target. It accepts any valid ordering, never consults the planted answer, and does not ask the solver to prove optimality.

## Why this regime is hard

Section 1 of the target paper fixes the precise Kempe move: swap two colors on exactly one connected component of their induced bichromatic subgraph. Theorem 5.1 identifies reachability with membership in the 2-coloring ideal, and Section 7 (Procedures 1–3 and Algorithm 7.6) constructs switching sequences. The authors explicitly warn immediately before Algorithm 7.6 that enumerating every stable set and computing the Gröbner basis is infeasible for large graphs. Proposition 6.11 gives an easy regime to avoid: for `k >= Delta+1`, every induced subgraph has one Kempe class. Here the actual graph is a very large star, `k=n+1`, and `Delta=3n(2n+1)`, so that result does not trivialize the bounded problem.

The target paper supplies an algorithmic characterization, not a complexity lower bound. The hardness justification is the exact same bounded Kempe problem analyzed by Bonamy et al. in [*Shortest Reconfiguration of Colorings Under Kempe Changes*](https://doi.org/10.4230/LIPIcs.STACS.2020.35): Theorem 12 proves Kempe Distance NP-complete even on stars, and Lemmas 13–14 reduce Hamiltonian Cycle on cubic graphs to the move bound used here. For a cubic graph on `n` colors the module takes `K=2n+1>2n`; a certificate meets the bound exactly iff each consecutive color pair is a cubic edge. The number of colors grows with `n`, avoiding their FPT algorithm parameterized by the number of colors. Unbounded reachability on stars/bipartite graphs is easy, and their 4-approximation does not decide this exact bound.

Generation is inverse: it samples a random cyclic answer first, uses its edges, then adds a disjoint random perfect matching. The public graph is cubic. After random labeling, cycle and matching edges have the same endpoint, degree, and representation distributions; no edge is marked as planted.

## Worked `standard` example

This is the complete output of `render(make_instance(n=128, seed=0))`, the smallest preset:

<details><summary>Rendered instance</summary>

```text
Compressed bounded Kempe-switching certificate

A proper k-coloring assigns one integer color to every graph vertex,
with different colors at the ends of every edge.  A Kempe switching
chooses two distinct colors, takes the connected components of the
subgraph induced by vertices currently having either color, chooses
exactly one such component, and exchanges the two colors on every
vertex of that component.

This instance uses colors 0 through 128 inclusive.
Colors 0 through 127 are ordinary; 128 is a buffer.
The graph being recolored is a star: one center is adjacent to every
leaf, and there are no leaf-leaf edges.  The center has the buffer
color in both the source and target colorings.

The leaves are specified compactly by the undirected cubic graph below.
For each listed edge u-v and each r with 0 <= r < 257, there are
two distinct star leaves L(u,v,r) and L(v,u,r).  Leaf L(u,v,r) has
source color u and target color v.  Thus all leaf names, source colors,
target colors, and star edges are fully determined by this rule.
There are 98688 leaves and 98689 star vertices.
The compact graph vertices/colors are 0-indexed.  Edges are undirected.
Cubic edges (192 total):
0-2 0-63 0-119 1-11 1-38 1-82 2-25 2-76 3-21 3-44 3-49 4-22 4-73 4-126 5-33 5-53 5-117 6-19 6-69 6-105 7-82 7-89 7-122 8-24 8-41 8-120 9-54 9-87 9-93 10-44 10-94 10-102 11-86 11-119 12-41 12-79 12-96 13-34 13-84 13-115 14-29 14-54 14-124 15-57 15-86 15-101 16-95 16-111 16-127 17-36 17-64 17-106 18-30 18-39 18-77 19-35 19-83 20-59 20-80 20-125 21-84 21-120 22-92 22-110 23-54 23-115 23-124 24-28 24-74 25-51 25-126 26-37 26-70 26-81 27-64 27-74 27-84 28-30 28-126 29-72 29-75 30-127 31-41 31-70 31-92 32-68 32-102 32-110 33-65 33-78 34-73 34-121 35-107 35-118 36-90 36-109 37-47 37-50 38-61 38-106 39-82 39-105 40-55 40-78 40-80 42-57 42-60 42-87 43-44 43-48 43-108 45-61 45-74 45-116 46-52 46-67 46-87 47-58 47-115 48-64 48-98 49-77 49-83 50-91 50-95 51-62 51-117 52-75 52-85 53-61 53-113 55-122 55-125 56-66 56-104 56-114 57-104 58-91 58-104 59-71 59-123 60-71 60-113 62-65 62-79 63-92 63-119 65-98 66-111 66-122 67-76 67-103 68-90 68-94 69-96 69-103 70-114 71-116 72-100 72-108 73-127 75-85 76-123 77-90 78-81 79-102 80-103 81-88 83-111 85-89 86-112 88-99 88-118 89-112 91-93 93-105 94-124 95-107 96-109 97-98 97-108 97-113 99-118 99-120 100-106 100-117 101-107 101-110 109-121 112-114 116-125 121-123

Your witness is a compressed Kempe sequence: give exactly one cyclic
ordering h0,...,h127 of all ordinary colors.  Every integer 0 through
127 must occur exactly once; do not repeat h0 at the end.  Rotation
and reversal are both allowed.  The ordering expands deterministically:

1. Define pred(h[(i+1) mod n]) = h[i].  Visit leaves in increasing
   lexicographic order (u,v,r).  If a leaf L(u,v,r) currently has color
   u != pred(v), switch the singleton component containing that leaf
   using colors u and pred(v).
2. Starting with the center still at the buffer color, switch the
   component containing the center successively with the named colors
   h[n-1], h[n-2], ..., h[0], and finally the buffer color.

The expanded sequence must use at most 65921 Kempe switchings
and must finish at the target coloring.  Equivalently, every consecutive
pair in your cyclic ordering, including the last paired with the first,
must be one of the listed cubic edges.

Give your final answer inside <answer></answer> tags, as exactly the
128 comma-separated ordinary colors in cyclic order.
Example: <answer>3, 17, 42, 8</answer>
Output nothing else inside the tags.
```

</details>

A valid answer is:

```text
48, 43, 108, 72, 29, 14, 54, 23, 124, 94, 10, 44, 3, 49, 83, 111, 16, 95, 107, 101, 110, 22, 4, 126, 25, 2, 76, 67, 46, 52, 75, 85, 89, 112, 86, 15, 57, 104, 58, 91, 50, 37, 47, 115, 13, 84, 21, 120, 99, 88, 118, 35, 19, 6, 69, 103, 80, 20, 59, 123, 121, 34, 73, 127, 30, 28, 24, 8, 41, 31, 92, 63, 0, 119, 11, 1, 82, 7, 122, 66, 56, 114, 70, 26, 81, 78, 40, 55, 125, 116, 71, 60, 42, 87, 9, 93, 105, 39, 18, 77, 90, 68, 32, 102, 79, 12, 96, 109, 36, 17, 64, 27, 74, 45, 61, 38, 106, 100, 117, 51, 62, 65, 33, 5, 53, 113, 97, 98
```

`verify(inst, answer)` returns `(True, "ok")`. Dropping the final `98` returns `(False, "wrong length: expected 128 colors, got 127")`.

## Difficulty presets

| Preset | `n` | Colors | `K` | Implicit star leaves | Move bound | Status |
|---|---:|---:|---:|---:|---:|---|
| `standard` | 128 | 129 | 257 | 98,688 | 65,921 | **ships; oracle held** |
| `hard` | 160 | 161 | 321 | 154,080 | 102,881 | available; not reached |
| `extreme` | 192 | 193 | 385 | 221,760 | 148,033 | available; not reached |

`escalate` adds 64 ordinary colors. Feasibility is preserved because every generated graph contains the answer sampled before its edges.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 9/9 plants verified (3 presets × 3 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | All 128 integers recovered from prose plus a Markdown fence |
| G4 | **0/200,000** valid structure-aware guesses; each guess was already a full permutation |
| G5 | At `n=12`, 120/168/216 valid labeled lists out of 479,001,600 (`2.51e-7`–`4.51e-7`) |
| G6 | Label-span outlier, short-cycle outlier, deterministic greedy, and 512 random restarts each solved **0/8** shipping seeds |
| G7 | Doubling to `n=256` built the implicit 393,985-vertex star and the plant verified |
| G8 | 60/60 reorder/relabel/composition invariance checks, 60/60 carried answers, 20/20 unrelated keys distinct |

Exact records are in `selftest_report.json`.

## Oracle hardening loop

The required script stopped at round 0 with `verdict: hardened` and shipping parameters `{"n":128}`. The two timeout rows are API errors and supply no hardness evidence.

| Preset | Seed | Model | Outcome | Recorded reason |
|---|---:|---|---|---|
| `standard` | 310944625 | Grok 4.6 | Error; excluded | 900-second hard deadline |
| `standard` | 495217791 | Grok 4.6 | Error; excluded | 900-second hard deadline |
| `standard` | 1259627752 | GPT-5.6 Terra | Failed | parsed 137 colors; expected 128 |
| `standard` | 680162278 | Claude Sonnet 5 | Failed | empty response after 32,000 completion tokens (`length`) |
| `standard` | 868879539 | Gemini 3.1 Pro Preview | Failed | parsed 143 colors; expected 128 |

Both visible attempted answers parsed, so the result is not a `parse_answer` false negative. Full replies and timings are in the script-owned `llm_loop_transcript.jsonl`; `.meta.json` records the pool and master seed.

## Use

```python
import gen_2401_06027 as kempe

params = kempe.DIFFICULTY[kempe.SHIPPING_DIFFICULTY]
inst = kempe.make_instance(seed=42, **params)
question = kempe.render(inst)
answer = kempe.parse_answer(model_output)
ok, reason = kempe.verify(inst, answer)
```

From the repository root:

```bash
python3 results/2401.06027/gen_2401_06027.py
bash scripts/emit.sh 2401.06027 20 standard
```

## Caveats

- The target paper does not establish hardness; the worst-case NP-completeness statement comes from the cited STACS paper. Worst-case hardness does not prove that this planted random cubic distribution is hard on every seed. Specialized Hamiltonian-cycle/SAT solvers and algorithms for random regular graphs were not tested.
- G4 samples uniformly from permutations, incorporating type, length, range, and all-different constraints. It does not condition on already having found a long adjacent self-avoiding path, and `0/200,000` is an empirical observation for one shipping instance, not a proof of probability zero.
- The panel did not try branch-and-cut, full exponential backtracking, MCMC cycle surgery, learned edge classification, or the target paper’s Gröbner-basis machinery. It only rules out the four recorded cheap attacks on eight seeds.
- The star is represented by symmetric leaf groups. The checker’s grouped replay is exact for those named leaves but does not allocate all 98,688 leaf objects. A bug in that compression would matter; G1, the final-color comparison, exact move count, and the carried-answer tests exercise it.
- `canonical_key` is a strong relabeling-invariant multiset of rooted BFS layer/edge profiles, not a complete graph-isomorphism canonical form. Nonisomorphic graphs can theoretically collide and be over-collapsed, although 20/20 unrelated test instances had distinct keys.
- If `n` were kept small, the star-case FPT algorithm would apply and random/greedy attacks become effective. If the move bound were removed, reachability on these bipartite star instances would be easy. Those are why only `n>=128` is shipped.
