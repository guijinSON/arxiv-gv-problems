# Vertex deletion for a fixed `aea` first-order property

| profile axis | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | `combinatorics` |
| object regime | `finite_discrete` |
| computational core | `exact_cover` (the generated 2-set case is perfect matching) |
| certificate form | `exact_symbolic` graph-vertex labels |
| intended intuition | `invariant`: neighbor-row sums expose a common affine translation |
| domain essentiality | `licensed_reduction` — the paper's graph is visible, but search and optimized verification use its Set Cover characterization |
| reduction | `paper_licensed`, Section 3, Lemma 3.14 (`lemma:vd-basic-aea`) |

This module instantiates Bannach, Chudigiewitsch, and Tantau, [*On the
Descriptive Complexity of Vertex Deletion Problems*](https://arxiv.org/abs/2406.18299).
It gives a compact, exact specification of a finite simple graph and asks for
at most `k` vertices whose deletion makes every remaining vertex incident with
an edge contained in no triangle. The answer names vertices of the paper's
four-cycle gadgets. Checking the answer requires only exact label parsing,
incidence lookup, and coverage/disjointness tests. For the demo, the self-test
also expands the graph and evaluates the first-order property directly.

This is representational rather than fully native coverage. Lemma 3.14 reduces
Set Cover to the graph problem; the rendered graph and its fixed formula remain
explicit, but the actual search is carried by the reduction's set-incidence
structure.

## Why Track B

Section 2 defines vertex deletion as finding `D`, `|D| <= k`, for which the
induced structure after deleting `D` satisfies a fixed sentence. Theorem 3.1
and Lemma 3.2 give the basic-graph trichotomy: the `eae` and `e* a*` regimes
are in parameterized constant depth, while a problem in the `aea` regime can
be W[2]-hard. Lemma 3.14 supplies the exact sentence used here,

```text
forall x exists y forall z
  ((E(x,y) and (E(y,z) -> not E(x,z))) or x=z),
```

and its Set Cover gadget. The `aea` W[2]-hardness is **not** claimed for this
distribution. Every generated source set has two elements and joins opposite
shores; a cover of size `p` is exactly a bipartite perfect matching.
Hopcroft–Karp therefore solves it in `O(m sqrt(2p))`. At the configured hard
preset and seed 314159 it succeeded after 2,430 neighbor inspections in
0.000481 seconds; it solved all 8 panel instances, as Track B requires. The
corresponding expanded paper graph has 415,840 edges.

The inverse construction samples a nonzero `alpha` modulo prime `p` and a set
of intercepts `B`. Row `x` contains all
`p + (alpha*x+b mod p)` for `b in B`; each intercept layer is a perfect
matching. The planted layer is sampled before the graph exists and carried
through Lemma 3.14. Plants and decoys are drawn from the same affine-layer
distribution, and every layer is itself a valid answer.

The compact route uses the invariant
`sum(R_1)-sum(R_0) = degree*alpha (mod p)`, where right-shore labels are read
modulo `p`. Recover `alpha`, choose any entry of row 0, and follow its affine
translate. The conservative hard-preset accounting is at most 245 exact
arithmetic operations. This is roughly one tenth of the measured matching
work, and it stays below the 300-operation no-tool cap.

## Worked demo (`seed=0`)

The smallest instance is hand-solvable:

```text
p=5, universe 0,...,9, k=5
0: 5 6 8
1: 5 7 9
2: 6 8 9
3: 5 7 8
4: 6 7 9
```

For every displayed `{u,v}`, make gadget vertices `a:u:v`, `b:u:v`,
`c:u:v`, and `d:u:v` on the cycle `a--b--c--d--a`. For every universe
element `w`, make copies `e:w:0` through `e:w:5`; join each copy to both
`a:u:v` and `b:u:v` whenever `w` is in `{u,v}`. One answer is

```text
<answer>["b:0:6", "b:1:5", "b:2:9", "b:3:8", "b:4:7"]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the final
label returns `(False, "wrong deletion-set size: expected 5, got 4")`. A
person can solve this demo on paper by choosing one edge incident with each
left and right vertex.

## Difficulty presets

| preset | shore size `p` | affine layers per row | answer atoms | status |
|---|---:|---:|---:|---|
| `demo` | 5 | 3 | 5 | hand example; never shipped |
| `easy` | 113 | 4 | 113 | first oracle rung |
| `medium` | 113 | 6 | 113 | fixed-length crowding increase |
| `hard` | 113 | 8 | 113 | **configured preset; local gates pass** |

The evaluated ladder grows the haystack while keeping the witness at 113
labels. `SHIPPING_DIFFICULTY="hard"` is provisional: the required oracle
service was unreachable, so this directory is not submission-ready and no
hardness verdict is asserted.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified; 12/12 JSON round trips; optimized verification agreed with direct formula evaluation on all 243 demo edge-choice tuples |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | all 113 labels recovered from prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; 1,000 optimized checks cross-checked with `verify` |
| G5 | shipping density 0/200,000; Hopcroft–Karp 2,430 inspections / 0.000481 s; strongest failing heuristic 256 restarts / 0.020932 s |
| G6 | four no-tool attacks each 0/8; reference matching 8/8, mean 2,515 inspections |
| G7 | all four candidate spaces strictly increase; doubled request `n=226` builds at `p=227` and verifies |
| G8 | 20/20 composed relabelings invariant, 20/20 carried answers valid, 20/20 unrelated keys distinct |
| G9(c) | 1,247 characters, about 312 tokens, 113 atoms, at most 245 intended-route operations |

The exact demo count is 416 endpoint-labelled answers out of 7,776 for each
of three measured seeds. It is an illustration, not a hard level.

## Oracle loop

`scripts/harden.py` was run on the repaired ladder. OpenRouter rejected every
redraw with HTTP 403 `Key limit exceeded`; errors do not count as model
failures. The transcript is machine-written and unedited, but it contains no
deciding attempt and `.meta.json` consequently has no hardening verdict.

| preset | seed | model | solved | reason |
|---|---:|---|---|---|
| `easy` | 820961216 | `openai/gpt-5.6-terra` | error | HTTP 403 key limit |
| `easy` | 1850785717 | `openai/gpt-5.6-terra` | error | HTTP 403 key limit |
| `easy` | 1795694513 | `google/gemini-3.8-flash` | error | HTTP 403 key limit |
| `easy` | 752742465 | `openai/gpt-5.6-terra` | error | HTTP 403 key limit |

## G9 arms

All three arms were run in separate scratch directories at the configured hard
preset; the extra bare record is retained as `g9_bare_transcript.jsonl` because
the main ladder failed at `easy` before reaching `hard`. All arms hit the same
external failure, so there is no meaningful `hinted - placebo` estimate.

| arm | solved / deciding attempts | provider errors | conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | unreachable |
| structural | 0/0 | 4 | unreachable |
| placebo | 0/0 | 4 | unreachable |

The structural hint only names the row-translation invariant; it does not give
the recovery procedure. Answer size is 1,247 characters (about 312 tokens),
with 113 atomic labels. The intended route uses at most 245 operations.

## Use

```python
import gen_2406_18299 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer('<answer>["a:0:113"]</answer>')
ok, reason = gen.verify(inst, candidate)
```

After a successful oracle rerun, emit from the repository root with:

```bash
bash scripts/emit.sh 2406.18299 20 hard
```

No third-party package or `gvlib` helper is needed; the module uses only the
Python standard library.

## Caveats

- The family is not ready to submit until the bare, structural, and placebo
  harness runs produce deciding attempts. Local correctness is verified;
  multi-model no-tool hardness is not.
- This is deliberately Track B. Matching solves every generated instance very
  quickly. The paper's unrestricted W[2]-hardness cannot be transferred to
  this planted 2-set distribution.
- The mechanical/compact gap is only about one order of magnitude (2,430 edge
  inspections versus at most 245 arithmetic operations), not a complexity
  separation. Whether that is enough to defeat the oracle pool remains exactly
  what the blocked hardening run must measure.
- `0/200,000` is the observed rate when choosing one random displayed set per
  left element and a random selector side. It does not model augmenting paths,
  affine recognition, or a trained solver's prior.
- The supplied integer labels preserve the affine shortcut. Arbitrary graph
  relabeling preserves the problem and canonical key but can erase that human
  route; this benchmark tests structure in the presented encoding.
- The panel does not run a separate ILP, blossom implementation, or commercial
  solver. Hopcroft–Karp is the more specific reference algorithm here and is
  reported as successful.
- `canonical_key` uses common-neighbor and four-cycle signatures rather than a
  complete graph canon. It passed the required transformations and diversity
  checks, but nonisomorphic graphs can theoretically collide.
