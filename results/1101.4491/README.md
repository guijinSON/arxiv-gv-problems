# arXiv 1101.4491 — cover-subset matching generator

Status: **verified Track B generator**. The official bare hardening run held at
`medium` (`n=171`, degree `20`): all three oracle attempts failed to return a
valid matching.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (right endpoints of a matching) |
| Intended intuition | invariant: a common modular displacement identifies a perfect matching |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Paul, Perez, and Thomassé,
[*Conflict Packing: an unifying technique to obtain polynomial kernels for editing problems on dense instances*](https://arxiv.org/abs/1101.4491).
Section 2, Lemma 2.1 states that if `S` is a minimum vertex cover of a bipartite
graph `B=(X union Y,E)`, then every subset `I` of `S_X` can be matched into
`Y minus S_Y`. The paper uses this matching certificate in the FAST, FASBT, and
dense-RTI kernel proofs.

An instance gives the bipartite graph as shuffled adjacency rows, sets `S=X`
and `I=X`, and asks for one distinct adjacent right endpoint per row. The
generator samples a modular perfect matching first, then adds decoy edges with
the same one-edge marginals. The planted matching proves both existence and
that the `n`-vertex cover `X` is minimum. `verify()` checks only answer shape,
range, distinctness, and exact edge membership; it never reads `inst["answer"]`.

This is a native proof object from Lemma 2.1, not a surrogate for a tournament,
tree, or betweenness instance. It covers the shared matching subproblem inside
the paper's kernels; it does not claim direct coverage of the four headline
editing problems.

## Why Track B

There is an efficient algorithm, and hiding it would make the hardness claim
false. Hopcroft--Karp finds a matching in `O(E sqrt(V))`. At the shipping preset
it solved 8/8 instances, with a median **7,882.5 edge scans** and **0.00041 s**
in the final selftest. A cheaper, non-guaranteed depth-2 augmenting-path repair
also solved 8/8, with a median **1,215 scans**, one restart, and **0.00145 s**.

The compact route notices that one value of `(right-left) mod n` occurs in every
row. Construction guarantees that the first three displayed rows isolate it.
Intersecting those displacement sets and applying the result to all rows costs
at most `3*degree+n = 231` exact modular operations. Without that invariant, a
no-tool solver must track a 171-row matching state. The official bare pool held
this level 0/3; the structural hint made it solve 3/3.

Track A would be indefensible. Section 1 explicitly records fixed-parameter
algorithms for all four editing problems. Theorems 2.7, 2.20, 3.12, and 4.12
give `4k`, `O(k^2)`, `5k`, and `5k` kernels for FAST, FASBT, dense RTI, and dense
BTI. Worst-case NP-completeness says nothing about this planted distribution.

## Worked demo (`seed=11`)

The complete data portion of the hand-solvable demo is:

```text
X=Y={0,1,2,3,4}; the copies are distinct.  S_X=X, S_Y=empty, I=X.
For each displayed row, choose one listed Y-neighbor; use every choice at most once.

1. x=4: 2 0
2. x=3: 1 4
3. x=2: 0 1
4. x=1: 4 0
5. x=0: 4 3

<answer>2, 1, 0, 4, 3</answer>
```

`verify(inst, [2,1,0,4,3])` returns `(True, "ok")`. Changing the first
entry to `1` returns `(False, "right endpoints must be distinct")`. There are
exactly two valid answers among the demo language's `5! = 120` permutations.
A person can solve this smallest preset on paper.

## Difficulty presets

| Preset | n | Degree | log2(n!) | Result |
|---|---:|---:|---:|---|
| demo | 5 | 2 | 6.91 | hand example; never shipped |
| easy | 159 | 18 | 938.34 | defeated by 1/3 bare oracles |
| medium | 171 | 20 | 1026.79 | **ships; held 0/3** |
| hard | 193 | 20 | 1192.03 | reserve escalation rung |

Earlier rungs through `n=127, degree=20` were all defeated by the bare pool.
An attempted `n=149, degree=20` shipping rung was also discarded locally
because distinctness-aware randomized greedy succeeded on 1/8 seeds. The final
ladder starts above both failures. `escalate()` raises degree first, then `n`,
and returns `"cap_bound"` when no writable fixed-length escalation remains.

## Gate results

| Gate | Shipping-preset evidence |
|---|---|
| G1 | 12/12 planted witnesses verified; all answers JSON-round-tripped |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | tagged, fenced model-style response recovered all 171 entries |
| G4 | 0/200,000 uniform permutation candidates valid; language size is `171!` |
| G5 | shipping density 0/200,000; demo exactly 2/120; Hopcroft--Karp median 7,882.5 scans |
| G6 | four attacks each 0/8; Hopcroft--Karp and shallow repair each 8/8 as Track B references |
| G7 | every named `n` increases; doubled `n=342` built and verified |
| G8 | 80/80 keys invariant, 80/80 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 745 characters, about 187 tokens, 171 atoms, 231 intended operations |

The four failing G6 attacks are minimum-column-degree selection, deterministic
first-unused greedy, 256 restarts of distinctness-aware randomized greedy, and
the obvious fixed modular offsets `0,+1,-1`.

## Official bare oracle loop

The script-selected pool for this run contained OpenAI and Google models at
medium reasoning effort. A level is defeated if any attempt solves it.

| Preset | Seed | Model | Result | Why |
|---|---:|---|---|---|
| easy | 1261290195 | Gemini | solved | verified witness |
| easy | 642290299 | GPT | failed | repeated right endpoint |
| easy | 1362268860 | GPT | failed | non-edge at position 132 |
| medium | 1259807435 | GPT | failed | non-edge at position 123 |
| medium | 480872089 | Gemini | failed | no parseable tagged answer |
| medium | 1055107081 | Gemini | failed | wrong answer length |

The resulting script-owned verdict is `hardened`, shipping `medium`.

## G9 diagnostic arms

| Arm at `n=171, degree=20` | Solved/attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | held and ships |
| structural hint | 3/3 | naming the invariant exposes the compact route |
| placebo hint | 2/3 | generic prompt effects are substantial |

`hinted - placebo = 1/3`. The sample is small, but the positive difference is
consistent with the declared invariant helping; the 2/3 placebo rate warns that
the arm comparison is noisy. Hint success is diagnostic, not a gate. The answer
has 745 serialized characters, about 187 tokens, and 171 atomic elements; the
intended route has at most 231 exact operations.

## Use

The generator is standard-library-only; the discrete matching certificate does
not need the optional `gvlib` exact-algebra helpers.

```python
import gen_1101_4491 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
wire = "<answer>" + ",".join(map(str, inst["answer"])) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1101.4491
```

## Caveats

- This is a Track B benchmark only: ordinary software solves it in under a
  millisecond. The claim is about no-tool state tracking versus recognizing a
  compact invariant, not computational complexity.
- The 0/200,000 guess result uses a uniform-permutation prior that enforces
  length, range, and distinctness. It does not model augmenting paths or a solver
  that mines modular correlations; both are explicitly tested elsewhere.
- The shallow repair probe reduces the mechanical/compact gap to about
  `1215/231`, much smaller than the guaranteed Hopcroft--Karp scan count. The
  oracle hold is essential evidence; cardinality alone would not support H.
- The panel does not test every row ordering, ILP encoding, or correlation
  statistic. Maximum matching dominates those for feasibility but not for
  modeling how a language model may notice the plant.
- `canonical_key()` uses bipartite color refinement plus common-neighbor
  multisets. It passed all required relabellings but is not a complete graph-
  isomorphism canonical form and can collide on adversarial graphs.
- The answer has 171 entries. It is under the 256-atom cap, but some oracle
  failures may still reflect transcription. The hint/placebo results should be
  read with that limitation in mind.
