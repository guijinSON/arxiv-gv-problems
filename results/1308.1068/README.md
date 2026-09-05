# arXiv 1308.1068 — deletion list-homomorphism to a skew-sum target

> **Status:** the generator passes every local G1–G9(c) gate, but the required
> four-vendor oracle run is **not complete**. OpenRouter returned HTTP 403 “Key
> limit exceeded” on every bare, structural-hint, and placebo call. The
> script-written error transcripts are retained; they are not hardness evidence.

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple (a sorted deletion-set array) |
| Intuition | decomposition — isolate the one obstructing list-pair block |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

The solver receives a loopless graph `G`, the target path `H` with edges
`0-1`, `0-3`, and `3-2`, a singleton allowed-image list for every vertex, and a
budget `k`. It must name exactly `k` vertices whose deletion makes the forced
map from `G-W` to `H` a list-respecting graph homomorphism. Requiring exactly
`k` loses no at-most-`k` witness because extra vertices may always be deleted.

This is the native DL-Hom(`H`) problem defined in Section 2 of Chitnis, Egri,
and Marx, [“List H-Coloring a Graph by Removing Few Vertices”](https://arxiv.org/abs/1308.1068).
Here `H` is the special sum of two one-edge graphs. Section 3.4 calls an edge
between the `B1` and `T2` list classes a *bad edge*. With the singleton lists
used here, the `1-2` edges are precisely those bad edges; all `0-1`, `0-3`, and
`2-3` blocks already map to target edges.

Generation composes the bad-edge block from odd paths. On a path with `2d+1`
vertices, the alternating internal side is the unique vertex cover of size
`d`. The generator samples paired paths and random labels, records those
alternating vertices, and only then adds safe edges. No emitted instance is
solved to obtain its answer. Verification checks shape and bounds, then checks
every remaining bad edge by exact integer membership; it never reads
`inst["answer"]` and accepts every valid sorted deletion set.

## Why Track B, not Track A

Theorem 1.1 proves fixed-parameter tractability in `k` and `|H|` for
skew-decomposable targets. Section 3.4 supplies the relevant bounded-depth
bad-edge branching, while the Introduction identifies the singleton-target
base case as Vertex Cover. These algorithmic results expressly rule out using
the paper’s worst-case NP-hardness remark as evidence that this inverse
distribution is Track A-hard.

An efficient algorithm exists here: classify the four rendered edge blocks by
their endpoint lists, run Hopcroft–Karp on the bipartite obstruction graph, and
obtain a minimum cover by Kőnig’s alternating reachability construction. Its
general complexity is `O(E sqrt(V))` time and `O(E+V)` space. On the block
representation actually shown to the solver, the shipping measurement scanned
192 obstruction edges, recorded 1,645 operations, and took 0.0006 s; it solves
8/8 as expected. Fully expanding the succinct reservoir first would instead
scan 4,201,248 edges and cost 12,607,981 recorded operations (1.738 s), but that
larger figure is a diagnostic, not the Track B reference cost.

The compact route uses the paper’s special-sum decomposition. The three safe
edge blocks can be discarded symbolically; the remaining symmetric adjacency
rows are disjoint odd paths, so one alternates inward from their endpoints.
That route visits at most 236 obstruction vertices/components. The benchmark
tests whether a no-tool solver finds this compression, not whether DL-Hom is
computationally hard.

## Worked demo

The complete `demo`, `seed=0` statement is hand-scale:

```text
DELETION LIST-HOMOMORPHISM TO A FOUR-VERTEX TARGET

All graphs below are finite, undirected, loopless, and have no parallel edges.
The target graph H has vertices 0,1,2,3 and exactly the edges
  {0,1}, {0,3}, {2,3}.

The input graph G has vertex IDs 0 through 141.  Every vertex has a
singleton list, so its image in H is forced.  The forced image c(v) is
  c(v)=0 for 0 <= v < 64;
  c(v)=3 for 64 <= v < 128;
  c(v)=1 for 128 <= v <= 134;
  c(v)=2 for 135 <= v <= 141.

The edge set of G is the union of the four blocks below.  Modular arithmetic in
the reservoir block uses residues 0,...,63.  These formulas are the exact
graph definition; do not add edges not specified here.

E12 (listed as symmetric adjacency rows; '-' means no neighbor):
  128: 137 141
  129: 135 136
  130: 137 138
  131: 135 140
  132: 136
  133: 140
  134: 138 139
  135: 129 131
  136: 129 132
  137: 128 130
  138: 130 134
  139: 134
  140: 131 133
  141: 128

E01 (explicit edges):
  (51,132) (28,131) (32,134) (5,128)
  (20,133) (19,130) (56,134) (30,129)
  (6,133) (61,133) (9,132) (31,129)
  (62,132) (18,131) (34,130) (35,128)

E23 (explicit edges):
  (140,76) (136,71) (137,97) (140,72)
  (139,125) (139,123) (135,124) (136,110)
  (135,73) (139,102) (141,114) (141,92)
  (138,111) (138,103) (141,75) (137,69)

E03 reservoir block:
  shifts S = [8, 24, 28, 41]
  reserved shift q = 41
  For every 0 <= i < 64 and every s in S, include
    {i, 64 + ((i+s) mod 64)},
  except omit the q-edge starting at i whenever i is the color-0 endpoint of
  an edge in E01.  No other edges exist.

A map phi from a graph to H is a homomorphism when every input edge {u,v}
maps to an edge {phi(u),phi(v)} of H.  It respects the lists when
phi(v)=c(v).  Delete exactly k=6 vertices so that the forced map
phi(v)=c(v) is a list-respecting homomorphism from the remaining induced graph
G-W to H.  Deleting exactly k loses no witness: any solution using fewer than k
vertices can be padded with arbitrary additional deletions.  Vertex IDs in W
must be distinct and written in strictly increasing order.

Give your final answer inside <answer></answer> tags as one JSON array of exactly
6 base-10 vertex IDs.
Example format: <answer>[1,2,3]</answer>
Output nothing else inside the tags.
```

The answer is `[128,130,134,135,136,140]`, and `verify` returns `(True,
"ok")`. Dropping the final vertex returns `(False, "answer must contain exactly
6 vertex IDs")`. A person can solve this demo by filtering the three target
edges from the one target nonedge and alternating on the two seven-vertex
paths.

## Difficulty and gate results

`n` is the number of safe reservoir vertices in each of two colors. The active
obstruction size varies slightly with the sampled path composition.

| preset | `n` per reservoir side | `k` | safe degree | active vertices | status |
|---|---:|---:|---:|---:|---|
| demo | 64 | 6 | 4 | 14 | hand example |
| easy | 20,000 | 36 | 8 | 78–84 | oracle not reached: quota error |
| medium | 100,000 | 72 | 10 | 154–168 | configured ladder |
| hard | 350,000 | 96 | 12 | 204–224 | configured shipping preset |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify and are JSON-native; repeated after the metadata edit |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged JSON round-trips through prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; space about `1.231e61` |
| G5 | shipping density 0/200,000; construction count 1; demo exact count 1/3003; strongest failing greedy used 18,680 operations in 0.0255 s; reference used 1,645 operations in 0.0006 s |
| G6 | four attacks each 0/8; polynomial reference algorithm 8/8 with a mean 1,649 operations |
| G7 | doubling `n` and raising safe degree multiplies the edge haystack by 2.333 while the 96-element answer remains fixed |
| G8 | 80/80 key invariances, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 673 chars / 169 estimated tokens / 96 atoms; at most 236 intended-route operations |

## Oracle loop and G9 diagnostic

The bare harness could not complete even one valid attempt. These rows are API
errors, not model failures and not evidence that `easy` held.

| preset | model | seed | result | why |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 767471416 | error | HTTP 403 key total limit |
| easy | GPT-5.6-terra | 1625387473 | error | HTTP 403 key total limit |
| easy | Gemini 3.8 Flash | 623002444 | error | HTTP 403 key total limit |
| easy | GPT-5.6-terra | 563667900 | error | HTTP 403 key total limit |

The two G9 arms were run in separate scratch directories and failed for the
same external reason.

| arm | solved / valid attempts | script calls | conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 errors | no verdict |
| structural hint | 0/0 | 4 errors | no verdict |
| placebo hint | 0/0 | 4 errors | no verdict |

`hinted − placebo` is undefined because both denominators are zero; the report
stores `0.0` only as its zero-attempt placeholder and labels the hinted verdict
`not_run`. Nothing can yet be concluded about whether the hint isolates the
claimed decomposition intuition.

## Use

From this directory:

```python
import json
import gen_1308_1068 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=7, **params)
statement = gen.render(inst)
answer = gen.parse_answer(
    "<answer>" + json.dumps(inst["answer"]) + "</answer>"
)
assert gen.verify(inst, answer) == (True, "ok")
```

After restoring OpenRouter quota, rerun the bare and two G9 harnesses. Once a
real hardened verdict exists, emit from the repository root with:

```bash
bash scripts/emit.sh 1308.1068 20
```

## Caveats

- This is a deliberately restricted singleton-list `P4` family. It exercises
  the paper’s native special-sum/bad-edge mechanism, but it is not evidence
  about arbitrary DL-Hom instances or the open cases in Section 5.
- The Track B reference cost already gives the algorithm the rendered block
  representation: it classifies whole blocks by endpoint list and never expands
  the safe reservoir. The remaining 1,645-versus-224-operation gap is modest;
  the full-expansion figure is reported separately and is not used to inflate
  the claim. The family makes no Track A claim.
- The 0/200,000 guess result samples exact-`k` subsets of bad-edge endpoints.
  It excludes safe-only reservoir vertices, but it does not model a solver that
  finds the list-pair decomposition or odd paths.
- Total degree is perfectly regular and obstruction degree does not separate
  all planted vertices from internal decoys. The tested outlier, greedy,
  random-restart, and single-target-side attacks fail. Generic SAT/ILP solvers
  and learned graph heuristics were not tested; Hopcroft–Karp is the successful
  reference algorithm.
- The canonical key handles active renumbering, edge-record order, independent
  reservoir rotations, and reflection through its normalized shift signature.
  It is a strong cheap invariant, not a complete canonical form for arbitrary
  colored cubic-graph isomorphism, so it may over-collapse rare nonisomorphic
  instances.
- The hard prompt is about 41,000 characters. That is inside the harness input
  budget, but it makes transcription mistakes more likely; G9(c) applies to the
  answer and post-insight operations, not prompt length.
- The only unfinished mandatory step is external: the supplied OpenRouter key
  has exhausted its total limit. Until the three valid bare attempts produce a
  `hardened` verdict, this directory is locally verified but not shippable.
