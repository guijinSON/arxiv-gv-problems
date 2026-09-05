# Connected vertex-radius domination on affine paths

Status: the generator and every local gate pass, but the required hardening run
is **not complete and no preset may ship**. A fresh run scored eight calls before
OpenRouter returned HTTP 403 “Key limit exceeded (total limit)”: Gemini solved
`easy` twice, `medium` twice, and `hard` once, while GPT failed once at each
level. Thus every named preset was defeated; the quota expired during the third
`hard` attempt, before the harness could enter automatic escalation or issue a
verdict. The current repository harness used its configured two-vendor pool,
which is also narrower than the four-vendor pool required by the task. Restore
quota, restore/use the required pool, and rerun STEP 4 before shipping.

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple (a 16-vertex set at shipping size) |
| Intended intuition | change of variables: recover the path interval forced by the extrema of `t+r(t)` and `t-r(t)` |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

The source is Leitert and Dragan, [“Parameterized Approximation Algorithms for
some Location Problems in Graphs”](https://arxiv.org/abs/1706.07475). The solver
receives a finite unweighted path with affinely scrambled vertex labels and an
exact integer radius function on its vertices. It must give a minimum-cardinality
connected set that radius-dominates every vertex. The answer is checked with
exact modular arithmetic and integer path coordinates; there are no floats and
`verify` never reads `inst["answer"]`.

Generation is inverse, not search. It first chooses two path coordinates
`z0 < z1`, a slack `c`, and the unique answer interval
`[z0+c, z1-c]`. It then composes affine maps around the polynomial whose two
zeros are `z0,z1`, and carries the answer through an independent affine vertex
relabeling. For every other coordinate the radius is at least `n+c`. Thus
`min(t+r(t)) = z0+c` and `max(t-r(t)) = z1-c`, which exactly force the planted
interval.

## Why this is Track B

Sections 1–2 define connected `r`-domination using the radius of the vertex
being served. In Section 3, immediately before Lemma 2, the paper states that a
minimum connected `r`-dominating subtree is computable in linear time; that
routine is a first step of Theorem 2’s connected approximation algorithm.
Because every generated graph is a path, claiming Track A would be false.

The reference algorithm composes the displayed affine radius maps and scans all
1,200,007 path positions. It is `O(n+L)` for `L` affine layers and, at the
shipping candidate, took **1.89 s** and **15,600,100 counted exact operations**
per instance, solving 8/8 as expected. The compact route reverses three affine
maps, recognizes the two radius extremizers, and emits their forced interval;
the measured worst case was **112 exact operations**. The benchmark is meant to
test discovery of that compression, not complexity-theoretic hardness.

The easy regime deliberately used here is therefore the paper’s tree regime.
The paper contrasts it with general domination, which it recalls is NP-hard and
W[2]-complete by solution size, and with split graphs, where even small
tree-likeness parameters do not remove approximation hardness. Those general
hardness results do not apply to this generated distribution.

## Worked demo

For `make_instance(n=37, witness_size=5, encoding_layers=1, seed=0)`, the full
rendered instance is:

```text
CONNECTED VERTEX-RADIUS DOMINATION ON AN AFFINELY LABELLED PATH

Vertices are 0,...,36.  The path coordinate t(x) is the unique residue with
    x = 2 + 27*t(x) (mod 37).
Coordinates differing by 1 are adjacent; coordinates 0 and 36 are not adjacent.

Starting from u=t(x), apply
    u <- (17*u + 32) mod 37,
then compute
    q = ((u-34)*(u-4)) mod 37,
    r(x) = 8 + 37*q^2.

Find a connected r-dominating set of exactly five distinct vertex labels.
Return it as <answer>[a,b,c,d,e]</answer>; order is irrelevant.
```

The answer is `[34, 24, 14, 4, 31]`.
`verify(inst, answer)` returns `(True, "ok")`; dropping the last label returns
`(False, "wrong_length")`. This demo is hand-solvable: invert one small affine
map modulo 37, recover the two zero coordinates 5 and 25, and select coordinates
19 through 23 before applying the vertex relabeling.

## Difficulty presets

| preset | vertices `n` | answer size | radius encodings | status |
|---|---:|---:|---:|---|
| demo | 37 | 5 | 1 | hand example; never ships |
| easy | 1,200,007 | 16 | 3 | defeated: Gemini solved 2/3 attempts |
| medium | 3,000,017 | 16 | 4 | defeated: Gemini solved 2/3 attempts |
| hard | 7,000,003 | 16 | 4 | defeated: Gemini solved 1/2 scored attempts; run then quota-blocked |

The module's required `SHIPPING_DIFFICULTY` field remains `easy` only so the
local gates have a reproducible candidate preset. It is not a shipping claim:
no preset earned a `hardened` verdict, and all three named non-demo presets were
solved at least once.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted answers verified; all JSON-native |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose + fenced JSON round-tripped; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware random candidates; exact density `1/1,199,992` |
| G5 | pass | demo brute-force count 1; shipping identity count 1; reference 1.89 s / 15,600,100 ops |
| G6 | pass | five attacks, 0/8 successes each; reference algorithm 8/8 as expected |
| G7 | pass | 2,400,019-vertex instance verifies with the same 16 answer atoms |
| G8 | pass | 140/140 invariant relabelings, 140/140 real transforms, 20/20 unrelated keys distinct |
| G9(c) | pass | 115 chars, 16 atoms, 112 intended-route operations |

An additional independent audit exhaustively checked 2,048 small instances and
109,056 candidate blocks against direct graph distances. Every planted set
dominated directly and every instance had exactly one connected answer block.

## Oracle loop and G9 diagnostics

The fresh bare run used the current script-owned two-vendor configuration. Its
twelve records comprise eight scored attempts and four error redraws:

| preset | model | seed | result | checker evidence |
|---|---|---:|---|---|
| easy | openai/gpt-5.6-terra | 1488135911 | failed | parsed set missed the left bound |
| easy | google/gemini-3.8-flash | 945084924 | solved | exact verifier returned `ok` |
| easy | google/gemini-3.8-flash | 2017248594 | solved | exact verifier returned `ok` |
| medium | openai/gpt-5.6-terra | 1177716689 | failed | parsed set missed the right bound |
| medium | google/gemini-3.8-flash | 1501737588 | solved | exact verifier returned `ok` |
| medium | google/gemini-3.8-flash | 1040183711 | solved | exact verifier returned `ok` |
| hard | google/gemini-3.8-flash | 1402371943 | solved | exact verifier returned `ok` |
| hard | openai/gpt-5.6-terra | 680533167 | failed | claimed incorrectly that no set exists |
| hard | mixed redraws | four further seeds | error | HTTP 403 key total limit; not scored as failures |

The earlier hinted and placebo transcripts contain only HTTP 403 redraws, so
both arms remain 0/0 rather than 0/3:

| arm | solved/attempts | status |
|---|---:|---|
| bare | not final | every named rung was solved; run aborted before verdict |
| hinted | 0/0 | quota-blocked; no diagnostic conclusion |
| placebo | 0/0 | quota-blocked; no diagnostic conclusion |

The hinted-minus-placebo difference is undefined until scored calls exist; the
module records `0.0` only because both denominators are guarded at zero, and
marks the verdict `not_run_openrouter_quota`. No conclusion about the claimed
intuition should be drawn yet. The structural hint names only the interval
extremizer invariant; it does not give the affine inversion procedure.

## Use

```python
from gen_1706_07475 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
candidate = parse_answer("<answer>[...]</answer>")
ok, reason = verify(inst, candidate)
```

After valid hardening evidence exists, emit from the repository root with:

```bash
bash scripts/emit.sh 1706.07475 20
```

To resume the blocked work, restore `OPENROUTER_API_KEY` quota, configure the
required four-vendor `ORACLE_POOL`, and run
`python3 ../../scripts/harden.py gen_1706_07475.py` here. Run structural and
placebo modes in separate scratch directories because the script overwrites its
transcript.

## Caveats

The family is easy with a CAS, a short modular-arithmetic program, or the
paper’s linear tree routine; that is the declared Track B premise. The exact
guess probability assumes a solver has already enforced the obvious shape
constraint and samples uniformly from connected `k`-vertex path blocks. It says
nothing about a nonuniform solver that recognizes the affine construction.

The attack panel tried degree/end-point selection, smallest numeric labels, raw
encoded roots, undoing only the final affine layer, and 256 random connected
blocks. It did not try a symbolic algebra system, SAT/ILP encoding, or a learned
construction-specific recognizer; the successful exact reference scan is
reported separately. The live run now shows a stronger caveat: Gemini recognized
and executed the full compact route at every named level, so this distribution
is vendor-sensitive and presently too easy to ship. Canonicalization is exact
for the generator’s affine label
changes, path reflection, encoded-root ordering, and equivalent affine-layer
factorizations, but it is not a general graph-isomorphism algorithm. Most
importantly, no automatic-escalation verdict and no four-vendor no-tool hardness
claim exist until the quota and pool-configuration blockers are resolved.
