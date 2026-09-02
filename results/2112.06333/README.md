# Single-conflict coloring generator (arXiv:2112.06333)

## What this generates

This module turns the proper-coloring special case of Bradshaw and Masařík's
[Single-conflict colorings of degenerate graphs](https://arxiv.org/abs/2112.06333)
into witness problems.  The solver receives a loopless multigraph encoded by an
ordinary list of vertex pairs.  Each listed pair represents three parallel
edges with forbidden ordered pairs `(0,0)`, `(1,1)`, and `(2,2)`.  It must return
one of the three colors for every vertex while avoiding every conflict.  The
checker only validates the vector shape and scans the edges, so verification is
exact and linear in the instance size.

The generator samples a balanced coloring first, scrambles its vertex labels,
then places edge-disjoint random perfect matchings between every two hidden
color classes.  Shipping graphs are triangle-free and 8-regular before the
three-edge expansion.  The matching layers are not exposed.

## Why the family is hard—and where it is easy

Section 1 gives the exact ordered-conflict definition.  Section 1.1 states that
replacing every graph edge by `k` parallel monochromatic conflicts makes
single-conflict `k`-coloring exactly ordinary graph `k`-coloring.  Here `k=3`,
so the family contains the classical NP-complete graph 3-coloring search
problem; see Garey, Johnson, and Stockmeyer,
[Some simplified NP-complete graph problems](https://doi.org/10.1016/0304-3975(76)90059-1).
The paper itself is an extremal existence paper and does **not** prove
average-case hardness for this planted distribution.

The shipping expanded multigraph is 24-regular and 24-degenerate.  It offers
only 3 colors, well outside the paper's easy sufficient regimes: Theorem 1.1
would guarantee a coloring here only at 12 colors, and the uniquely restrictive
bound in Theorem 2.3 is about 27 colors.  The proof of Theorem 2.3 also notes the
elementary `2d+1` greedy regime.  Theorem 3.1 extends the existence bound to
general restrictiveness but gives no three-color algorithm here.  Conversely,
large color sets, low degeneracy, and the sufficient-bound regimes should be
treated as easy and are intentionally avoided.

## Worked tiny example

This is `make_instance(n=4, matchings=2, triangle_free=False, seed=73)` rendered
in full:

```text
Single-conflict coloring witness problem

There are 12 vertices, numbered 0 through 11, and 3 colors,
numbered 0 through 2. A coloring assigns exactly one color to
every vertex. Colors may be reused, and the coloring need not use every color.

A conflict edge has two endpoints and one forbidden ordered color pair.
For each unordered constraint pair `u v` listed below (always u < v),
there are exactly 3 parallel conflict edges. For color c in
{0, ..., 2}, the c-th parallel edge forbids (c,c) from u to v;
the reverse orientation forbids the reversed pair, which is also (c,c).
Thus a coloring is valid exactly when every listed pair has differently
colored endpoints. The order of the listed pairs has no meaning.

CONSTRAINT_PAIRS 24
5 11
1 4
7 9
5 6
1 10
1 9
2 7
0 7
7 11
0 6
2 3
3 8
1 3
0 4
3 4
9 11
6 8
5 10
10 11
2 8
0 2
6 9
4 10
5 8
END_CONSTRAINT_PAIRS

Output exactly 12 base-10 integers. Integer number v is the color of
vertex v, so order matters and vertices are 0-indexed. Separate integers
with commas. Do not include vertex numbers, brackets, or repeated entries.

Give your final answer inside <answer></answer> tags, as a comma-separated
list of colors in vertex order.
Example of the format only: <answer>0, 2, 1, 0</answer>
Output nothing else inside the tags.
```

A witness is `<answer>1, 1, 2, 0, 2, 2, 0, 0, 1, 2, 0, 1</answer>`.
`verify(inst, witness)` returns `(True, "ok")`.  Swapping its first and third
entries produces `[2, 1, 1, 0, 2, 2, 0, 0, 1, 2, 0, 1]`, for which verification
returns `(False, "forbidden_conflict_on_pair:0,4")`.

## Difficulty presets

`n` is the hidden class size; the rendered vertex count is `3n`.

| Preset | `n` | Vertices | Matchings/pair | Constraints | Triangle-free | Status |
|---|---:|---:|---:|---:|:---:|---|
| `tiny` | 4 | 12 | 2 | 24 | no | Local tests pass; oracle solved 3/3 |
| `medium` | 72 | 216 | 4 | 864 | yes | **Shipping; oracle solved 0/3** |
| `hard` | 108 | 324 | 4 | 1,296 | yes | Reserve; final loop did not need it |
| retired pilot | 36 | 108 | 4 | 432 | yes | Rejected by G6: min-conflicts solved 5/8 |

## Gate results at shipping difficulty

| Gate | Result | Measurement |
|---|:---:|---|
| G1 planted verifies | pass | 12/12 across every current preset and four seeds |
| G2 corruption | pass | 5/5 rejected with 5 distinct reasons |
| G3 round trip | pass | 216 colors recovered through prose and a Markdown fence |
| G4 random guess | pass | 0/200,000; global color-name symmetry removed |
| G5 sparse | pass | tiny: 6/531,441 = 1.129e-5 valid |
| G6 adversaries | pass | outlier 0/8; greedy 0/8; min-conflicts 0/8; triangle seed 0/8 |
| G7 scaling | pass | 216→432 vertices and 864→1,728 constraints; plant verifies |
| G8 canonical key | pass | 80/80 invariant and real transforms; 20/20 unrelated keys distinct |

The machine-readable measurements are in `selftest_report.json`.

## Final oracle loop

The script-owned transcript used four vendors at reasoning effort `medium`.  A
level is solved if any oracle succeeds and held only if all three fail.

| Preset | Model | Seed | Solved? | Verification result |
|---|---|---:|:---:|---|
| tiny | Anthropic Claude Sonnet 5 | 228879568 | yes | `ok` |
| tiny | Google Gemini 3.1 Pro Preview | 1586446611 | yes | `ok` |
| tiny | xAI Grok 4.6 | 170613570 | yes | `ok` |
| medium | Anthropic Claude Sonnet 5 | 955026929 | no | 222 colors, expected 216 |
| medium | OpenAI GPT-5.6 Terra | 1730106465 | no | 240 colors, expected 216 |
| medium | Google Gemini 3.1 Pro Preview | 978297173 | no | conflict on pair 155,203 |

Verdict: `hardened`, shipping parameters `n=72, matchings=4,
triangle_free=True`.  See `llm_loop_transcript.jsonl` and `.meta.json` for the
complete replies, timings, master seed, and schema.

## How to use it

```python
from gen_2112_06333 import (
    DIFFICULTY, SHIPPING_DIFFICULTY, make_instance,
    render, parse_answer, verify,
)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
prompt = render(inst)                 # send this string to a solver
answer = parse_answer(solver_reply)   # raw model response
ok, reason = verify(inst, answer)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2112.06333 20 medium
```

Run the local gates with `python3 results/2112.06333/gen_2112_06333.py`.

## Caveats

- NP-completeness is a worst-case fact about the exact subfamily, not a proof
  that every random planted instance is hard.  The oracle panel and attacks are
  empirical evidence only.
- G4 samples independent per-vertex colors after canonicalizing the freely
  interchangeable color names.  It does not condition on balanced class sizes
  (balance is not stated to the solver), and it does not approximate the success
  rate of a search heuristic.  The reported `3^216` space is explicitly naive.
- Tested attacks were degree/input-position ranking, left-to-right greedy,
  triangle-seed availability, and min-conflicts with 16 restarts, `20N` moves
  per restart, and 8% noise.  Exact DSATUR/backtracking, SAT/ILP solvers,
  belief propagation, spectral/SDP recovery, and larger local-search budgets
  were not tested.
- Every shipping vertex has the same degree and input edges are shuffled, but
  regularity, balance, and the planted matching model may still have exploitable
  higher-order signatures.  Triangle-free conditioning is randomized over the
  three class-pair orders; it is not a proof of distributional symmetry.
- `canonical_key` uses rooted common-neighbor/distance profiles followed by
  Weisfeiler–Lehman refinement.  It is genuinely invariant under vertex and
  input-edge relabelling, but it is not a complete graph-isomorphism canonical
  form and can theoretically collide on non-isomorphic graphs.
