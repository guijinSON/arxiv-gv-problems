# arXiv 1708.06866 — triangle-count generator (parked)

| profile | value |
|---|---|
| Track | **B** — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (component counts plus total) |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |
| Designated preset | `hard` (provisional; the result is parked) |

This module turns [*Static Graph Challenge: Subgraph Isomorphism*](https://arxiv.org/abs/1708.06866)
into a deterministic, unlimited family of exact triangle-counting instances. The
solver receives a finite simple graph through exact vertex and edge predicates. Each
component is one of the paper's eight-neighbour image graphs after an integer
unimodular coordinate relabelling. The answer gives every component's triangle count
and their total. `verify` validates the coordinate data and recomputes the counts by
an exact identity; it never reads `inst["answer"]`.

**Status:** all local construction and verification gates pass, but this is not an
oracle-hardened release. The sanctioned bare loop solved every rung through `n=4096`
and returned `budget_bound`, with `n=8192` still available. The harness explicitly
says to park this outcome rather than reject it, so there is no `REJECTED.md` and no
claim that the designated `hard` preset ships.

## Source fidelity and Track-B claim

Section III-A defines a triangle as an unordered set of three mutually adjacent
vertices and gives three polynomial-time counting algorithms. Section IV-A makes the
exact count the correctness criterion. Section IV-C's synthetic-data subsection
constructs an `M` by `M` image graph by joining every pixel to its eight neighbours.
Those are the native graph objects used here; the prior hypothesis of planting an
arbitrary pattern graph in a host is not the problem the paper actually specifies.

This cannot honestly be Track A. A standard forward-neighbour triangle enumerator
solves all eight designated `hard` instances in `O(V*Delta^2)` exact work, with
`Delta <= 8`. The final local run measured a mean of **10,166,691 operations** and
**6.009 seconds** (the same operation count took 3.0 seconds in an immediately prior
run). The compact route recognizes the two linear forms as grid coordinates, checks
that the four signed step pairs become the eight king moves, and observes that every
unit cell is `K4`. Each cell contributes four triangles and every triangle has one
such bounding cell, so a width-`M` component has `4(M-1)^2` triangles. The complete
designated-preset route is conservatively counted at **279 exact arithmetic
operations**.

There is a source inconsistency worth preserving: Table II reports `8(M-1)^2`
triangles. The paper's set definition and Algorithm 2's division by six imply the
ordinary undirected count `4(M-1)^2`; a `2 x 2` image is `K4` and has four, not eight,
triangles. The independent reference enumerator confirms the latter count.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders as:

```text
Count triangles in an exactly specified finite simple graph.

A triangle means an unordered set of three distinct vertices for which all three undirected edges are present.  Count each such set once.

The graph is the disjoint union of the components listed below.  A vertex is an integer triple (tag,x,y).  For a component line, the vertices are precisely the triples with that tag whose two displayed linear forms L1(x,y), L2(x,y) satisfy their displayed half-open bounds.
Two distinct vertices are adjacent exactly when they have the same tag and their difference (x'-x,y'-y) equals one of the four listed step vectors or its negative.  There are no edges between different tags.
Every displayed lower bound is inclusive and every upper bound is exclusive.

Components are 0-indexed in the displayed order:
  0: tag=413753999; L1=-x + 5472 with -3351 <= L1 < -3348; L2=-x - y + 8344 with 796 <= L2 < 799; steps=[[1,0],[1,-1],[0,1],[-1,2]]
  1: tag=906791059; L1=-y - 61 with 866 <= L1 < 870; L2=x - 4*y + 5618 with 4558 <= L2 < 4562; steps=[[5,1],[-4,-1],[-3,-1],[-1,0]]

Return an object with exactly two fields:
  component_counts: one nonnegative integer per component, in displayed order, each equal to that component's number of triangles;
  total: the sum of component_counts, hence the graph's triangle count.
Order matters, repetitions are allowed, and no component may be omitted.

Give your final answer inside <answer></answer> tags as one JSON object.
Example format only: <answer>{"component_counts":[4,16],"total":20}</answer>
Output nothing else inside the tags.
```

The answer is `{"component_counts":[16,36],"total":52}`. A person can solve this
demo on paper from widths 3 and 4.

```python
>>> verify(demo, demo["answer"])
(True, "ok")
>>> verify(demo, {"component_counts": [16, 35], "total": 51})
(False, "component 1 triangle count is incorrect")
```

## Difficulty presets

The side of each square is sampled from `n..n+jitter`. Tags, offsets, component order,
and coordinate changes vary with the seed. Escalation doubles the component sides and
keeps the eight-count witness fixed.

| preset | `n` | components | jitter | shears | seed-0 vertices | answer chars | outcome |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 3 | 2 | 1 | 1 | 25 | 39 | hand-solvable; not hardened |
| easy | 32 | 8 | 7 | 2 | 10,698 | 76 | oracle-defeated |
| medium | 96 | 8 | 31 | 3 | 98,242 | 85 | oracle-defeated |
| hard | 256 | 8 | 63 | 4 | 713,667 | 94 | oracle-defeated; provisional designation |

The loop also defeated escalated `n=512,1024,2048,4096`; it stopped on its escalation
budget, not because the answer approached either output cap.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 planted verifies | pass | 12/12, every preset x three seeds |
| G2 corruption | pass | 5/5 rejected with five distinct reasons |
| G3 round trip | pass | tagged fenced prose parsed; answer is JSON-native |
| G4 guess resistance | pass | 0/200,000 structure-aware samples; language size `77622327931723813833916800902079828094103610000` |
| G5 density/baseline | pass | hard 0/200,000; demo exact solution count 1; reference mean 10,166,691 ops / 6.009 s |
| G6 adversaries | pass | six attacks at 0/8; disclosed reference algorithm 8/8 |
| G7 scaling | pass | 663,268 to 2,643,647 vertices with eight counts unchanged |
| G8 canonical key | pass | 100/100 invariant, 100/100 carried witnesses valid, 20/20 unrelated distinct |
| G9 size/effort | pass | 94 chars, 25 tokens, 9 atoms, 279 operations |

The six failing attacks are largest-component-only, edges divided by three, the
degree-bound midpoint, one triangle per unit cell, the paper's doubled Table II count,
and 256 structure-aware random restarts per seed. The successful standard algorithm
is reported separately because Track B requires it to succeed.

## Bare oracle loop

`ok` means an exact answer verified; the other failures supplied a well-formed but
incorrect component count. At least one solve defeated every level.

| preset | seed | model | solved | why |
|---|---:|---|---|---|
| easy | 836933404 | Gemini 3.8 Flash | no | component 0 incorrect |
| easy | 529942832 | GPT-5.6 Terra | no | component 0 incorrect |
| easy | 294691475 | Gemini 3.8 Flash | yes | ok |
| medium | 1207271768 | GPT-5.6 Terra | yes | ok |
| medium | 1343372069 | Gemini 3.8 Flash | yes | ok |
| medium | 103628083 | GPT-5.6 Terra | no | component 0 incorrect |
| hard | 36023413 | GPT-5.6 Terra | yes | ok |
| hard | 1344569527 | Gemini 3.8 Flash | yes | ok |
| hard | 2057640784 | GPT-5.6 Terra | yes | ok |
| escalated `n=512` | 515159310 | GPT-5.6 Terra | yes | ok |
| escalated `n=512` | 360865985 | Gemini 3.8 Flash | yes | ok |
| escalated `n=512` | 99507764 | GPT-5.6 Terra | yes | ok |
| escalated `n=1024` | 1426657653 | Gemini 3.8 Flash | yes | ok |
| escalated `n=1024` | 939445961 | GPT-5.6 Terra | no | component 0 incorrect |
| escalated `n=1024` | 724560925 | Gemini 3.8 Flash | yes | ok |
| escalated `n=2048` | 1737276402 | Gemini 3.8 Flash | yes | ok |
| escalated `n=2048` | 733796773 | GPT-5.6 Terra | yes | ok |
| escalated `n=2048` | 644335889 | Gemini 3.8 Flash | yes | ok |
| escalated `n=4096` | 815467870 | GPT-5.6 Terra | yes | ok |
| escalated `n=4096` | 1052161394 | Gemini 3.8 Flash | yes | ok |
| escalated `n=4096` | 1726009887 | Gemini 3.8 Flash | yes | ok |

The recorded pool had two models, so the three attempts per level necessarily repeat
one vendor. The script-owned verdict is `budget_bound`, not `hardened`.

## G9 arms

These diagnostics were run in isolated copies at the provisional `hard` preset with
the harness's escalation budget set to zero, so each transcript contains exactly the
three requested calls at that rung.

| arm | solved/attempts | verdict at hard |
|---|---:|---|
| bare | 3/3 | too easy |
| structural hint | 3/3 | too easy |
| placebo hint | 3/3 | too easy |

`hinted - placebo = 0.0`. The hint bought no measured improvement: the bare statement
already exposes enough structure for these models to recover the coordinate change.
This weakens the intended `change of variables` diagnostic claim even though G9(a/b)
are non-gating. The G9(c) measurements remain 94 characters, 25 conservative tokens,
9 atomic elements, and 279 intended-route operations.

## Use

```python
import json
import gen_1708_06866 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY["hard"])
question = g.render(inst)
candidate = g.parse_answer(
    "work outside tags <answer>" + json.dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, the normal emission command would be:

```bash
bash scripts/emit.sh 1708.06866 20 hard
```

Do not emit this result into a release while `.meta.json` says `budget_bound`; rerun
the sanctioned hardening process under a larger escalation budget or redesign the
family first.

## Caveats

- Recognizing the hidden king grid makes the family easy, as the oracle evidence now
  demonstrates. Larger `n` raises the generic enumerator's work but barely changes
  the compact calculation, so size-only escalation may never establish Track-B model
  difficulty.
- The 0/200,000 density result samples each component count independently from the
  exact maximum-degree upper bound and forces the total to be their sum. It measures
  blind guessing after obvious shape constraints, not an intelligent solver that
  recognizes the grid.
- The panel did not run a production GraphBLAS matrix multiplier, a general graph
  isomorphism package, or the paper's k-truss kernel. It did run an independent exact
  forward-neighbour triangle enumerator on the actual generated graph.
- `canonical_key` is exact for this generated family: it removes component order,
  tags, translations, signed step presentation, unimodular coordinates, and square
  axis swaps by retaining the square-size multiset. It is not a general graph
  isomorphism canonicalizer.
- The paper's Table II discrepancy is treated as an erratum by inference from the
  definition and Algorithm 2; the paper itself does not label it one.
