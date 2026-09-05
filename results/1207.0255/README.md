# arXiv 1207.0255 — fixed-path interval-extension generator

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | integer tuple: a row-wise component-placement table |
| Objects shown | fixed host path, partially represented interval graph, pre-drawn singleton subpaths, unlocated path components |
| Intended intuition | invariant: three size bands carry affine copies of one residue-tag set |
| Domain essentiality | **licensed reduction** |
| Reduction | paper-licensed: Section 3.3, Theorem 3 (3-PARTITION to `RepExt(INT,Fixed)`) |

## What the family is

The source is Klavík, Kratochvíl, Otachi and Saitoh, [*Extending Partial
Representations of Subclasses of Chordal Graphs*](https://arxiv.org/abs/1207.0255).
The solver receives the paper's fixed-path partial interval-representation
objects: singleton subpaths fixed at gap boundaries and unlocated path
components whose lengths must fill the gaps. It returns one `[gap, rank]` row
for each take component. The checker expands this compact placement into the
paper's canonical closed-subpath representation and checks ranks, capacities,
boundaries, and path lengths using exact integers. It never reads the planted
answer, invokes a solver, or uses floating point.

This is a paper-licensed reduction, not an analogue: the search is carried by
the 3-PARTITION reduction in Theorem 3, but the host path, partial subpaths, and
interval-graph components remain visible to the solver and verifier.

## Why this is Track B

Section 1.2 fixes the four allowed host-tree modifications; this family uses
`Fixed`. Section 2 shows that connected components occupy disjoint areas.
Lemma 6 gives `minspan(P_A)=A`, and Theorem 3 places split singletons at
`p_(M+1)j`, leaving gaps of exactly `M` vertices. Thus a representation exists
exactly when three take components fill each gap.

The general problem is NP-complete, but this module makes no Track A claim
about its planted distribution. An efficient special-purpose algorithm exists:
the affine-residue decoder is expected `O(n)` with hash tables (or deterministic
`O(n log n)` after sorting). It solved 8/8 shipping instances in 1,232 counted
operations and 0.049525 seconds total. The domain-standard mechanical baseline
builds all low/middle exact-pair candidates and runs Algorithm X; candidate
generation is `O(n²)` and exact-cover search is exponential in the worst case.
At shipping it examines 900 cross-band pairs per instance and took 42,605
primitive checks, 248 search nodes, and 0.062572 seconds over eight instances.

The compressed route is to notice that `q²=M/12` and that the three visible
length bands encode the same tags modulo `q` (the high band uses `-2t`). After
that insight, reconstruction needs at most 182 exact arithmetic operations.
Without it, a no-tool solver must organize the much larger complementary-pair
table. This gap—not complexity-theoretic hardness—is the Track B claim.

The generator avoids the paper's easy regimes: `Recog*(INT,Fixed)` is linear by
Proposition 1; `RepExt(INT,Sub)` is linear by Theorem 2; Section 3.4 notes that
locating every component restores a fixed order and a linear test; and
Proposition 5 makes bounded host-path size FPT. Here the path size, splitter
count, and number of unlocated components all grow.

## Worked demo

For `make_instance(seed=7, **DIFFICULTY["demo"])`, the rendered data are
`n=2`, `M=122412`, a fixed path from `p_0` through `p_244826`, split singletons
at coordinates `0`, `122413`, and `244826`, and these take-component lengths:

```text
0: 50498
1: 30907
2: 41007
3: 30704
4: 50601
5: 41107
```

The complete answer is:

```json
[[1,2],[1,0],[1,1],[0,0],[0,2],[0,1]]
```

`verify` returns `(True, "ok")`. Moving components 0 and 3 to the opposite
gaps gives `[[0,0],[1,0],[1,1],[1,2],[0,2],[0,1]]`; `verify` returns
`(False, "capacity mismatch: gap 0 receives total span 142206, not M=122412")`.
A person can solve this smallest setting on paper by testing the two three-item
sums. `render()` additionally supplies all definitions, indexing conventions,
the canonical subpath-expansion formula, and tagged JSON output instructions.

## Difficulty presets

| Preset | Gaps `n` | Take components | `q` | Screen restarts | Result |
|---|---:|---:|---:|---:|---|
| demo | 2 | 6 | 101 | 0 | hand-solvable illustration |
| easy | 18 | 54 | 1009 | 64 | rejected: one oracle solved it |
| medium | 30 | 90 | 1009 | 128 | **ships; held 3/3** |
| hard | 42 | 126 | 1009 | 256 | available, not needed for shipping |

`SHIPPING_DIFFICULTY` is `medium`. Difficulty grows by matching more
simultaneous components. Beyond the named ladder, `escalate()` first raises
coefficient height and the attack-screen budget while keeping the certificate
length fixed.

## Gate results

| Gate | Result | Measurement at shipping unless noted |
|---|---|---|
| G1 | pass | 12/12 preset/seed plants verify and JSON-round-trip |
| G2 | pass | seven corruptions rejected with seven distinct reasons |
| G3 | pass | tagged fenced JSON with surrounding prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; declared space about `4.13e120` |
| G5 | pass | shipping density 0/200,000; demo exactly 72/288 placements; strongest failed attack 102,175 operations and 0.322210 s over eight instances |
| G6 | pass | four attacks each 0/8; Algorithm X reference 8/8; affine decoder 8/8 |
| G7 | pass | candidate space rises at every rung; doubled `n=60` builds and verifies |
| G8 | pass | 80/80 key-invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 601 characters, 151 estimated tokens, 180 atoms, 182 intended exact operations |

The four failing G6 attacks are size-band rank zipping, largest-first exact
pairing, 256 random residue-blind exact-pair restarts, and the in-context
“sort and take adjacent triples” heuristic. The successful references are
reported outside `attacks`, as Track B requires.

## Oracle loop

The repository's currently configured pool contained OpenAI and Google models.
`easy` was defeated because any one solve advances the ladder; `medium` held
because all three attempts failed.

| Preset | Seed | Model | Solved? | Recorded reason |
|---|---:|---|---|---|
| easy | 1762347928 | GPT-5.6 Terra | no | claimed no placement; no tagged answer |
| easy | 1914233121 | Gemini 3.8 Flash | **yes** | parsed witness verified |
| easy | 1190957301 | GPT-5.6 Terra | no | incorrect excess-capacity claim |
| medium | 1177544505 | Gemini 3.8 Flash | no | parsed table had a capacity mismatch |
| medium | 134546116 | GPT-5.6 Terra | no | parsed table had a capacity mismatch |
| medium | 834449307 | Gemini 3.8 Flash | no | exhausted 32k output budget without an answer |

The script-owned verdict is `hardened`, shipping `medium`, after one
escalation. The last failure is preserved as a length-limited response rather
than silently described as a mathematical error.

## G9 arms

| Arm | Solved / completed | Error redraws | Status |
|---|---:|---:|---|
| bare | 0 / 3 | 0 | complete; shipping evidence above |
| structural hint | 1 / 2 | 4 | incomplete after quota exhaustion |
| placebo hint | 0 / 0 | 4 | no completed call; quota exhausted |

Hinted-minus-placebo is therefore undefined, not zero. The one completed hinted
solve is consistent with the claimed intuition: naming the residue invariant
can make the problem easy. Because no placebo call completed, that conclusion
is suggestive rather than a controlled estimate. The incomplete diagnostic is
non-gating; the answer and intended route remain within all G9(c) caps.

## How to use it

From the repository root:

```python
import importlib.util

path = "results/1207.0255/gen_1207_0255.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=7, **g.DIFFICULTY["demo"])
candidate = g.parse_answer(
    "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

Emit samples with:

```bash
bash scripts/emit.sh 1207.0255 20
```

## Caveats

This distribution is intentionally easy for code that discovers or is told the
modular promise. It is a no-tool compression benchmark, not evidence of
average-case NP-hardness. The 0/200,000 estimate applies only to the uniform
prior that already puts one member of each forced size band in every labeled
gap and randomizes ranks; it is not a bound against modular, SAT, ILP, CP-SAT,
or learned proposals.

No external SAT/ILP/CP solver, longer random-restart search, or alternative
exact-cover implementation was tried. The generic reference is exponential in
the worst case even though it is fast here. The answer describes a deterministic
full interval representation symbolically rather than printing millions of
individual vertex subpaths; the verifier checks that expansion from exact
formulas. Canonicalization covers take-component relabeling and host reflection,
not general graph isomorphism.

Finally, the G9 comparison is incomplete because the OpenRouter key reached its
total limit after two hinted calls. Those HTTP 403 records remain in the
script-owned transcripts and are not counted as oracle failures. A future run
with renewed quota should repeat both diagnostic arms in isolated directories.
The module is standard-library-only because all native coordinates are integral;
`gvlib` is unnecessary here.
