# Generalized SET from multicolored clique (arXiv:1309.6504)

| profile | value |
|---|---|
| Track | **A — structural hardness** |
| Domain / regime | combinatorics / finite discrete |
| Core / certificate | graph / integer tuple |
| Objects | compact generalized-SET cards, attribute-value vectors, paper-licensed partite graph |
| Intuition | reduction recognition: complementary part/pair value swaps |
| Essentiality | `licensed_reduction`; this is the paper's central reduction, but it is **not native-domain coverage** because the compact source graph carries the search |

## What the problem is

Lampis and Mitsou's [The Computational Complexity of the Game of Set and its Theoretical Applications](https://arxiv.org/abs/1309.6504) generalizes a SET to `q` cards: in each attribute, all `q` values must be equal or all must differ. Section 2 maps a `k`-partite graph to generalized-SET cards. One selected vertex-card per color and one compatible edge-card per color pair form a SET of size `q = k + binomial(k,2)` exactly when the source vertices form a multicolored clique.

The instance supplies hexadecimal adjacency rows and the paper's lossless card recipe. The answer is a compact list of one local vertex label per color; it expands deterministically to all `q` selected cards. Verification performs exact bit lookups and the complementary-swap condition, never reads the planted answer, and accepts any valid clique/SET.

## Why the Track A claim is credible

The corollary after Theorem 1 in Section 2 proves generalized SET W[1]-hard when parameterized by the number of values/SET size; the construction has unbounded attributes. The shipping preset is in that regime: source `k=24`, `q=300`, 30,912 attributes, and 56 vertices per color. Its uniform color-tuple language has `56^24 = 904716785818481122446300007835278136836096` candidates. A complete forward-checking clique search, capped at 10,000,000 nodes, failed on all eight audit seeds and spent 80,000,062 nodes / 245.470 seconds in the final run.

This is empirical distributional evidence, not a theorem about planted random graphs. Section 2 also identifies the regimes avoided here: two attributes are polynomial-time; fixed `k` admits XP enumeration; and ordinary one-round three-value SETs can all be enumerated in polynomial time. The paper's multi-round packing/covering parameter `r` is FPT and is not used. An earlier `k=12, s=24` rung fooled all three no-tool oracles but exact DPLL solved it in 117–1,099 nodes, so G6 rejected that rung and it was removed.

## Worked demo (`seed=0`)

This is the complete rendered demo instance:

```text
Generalized one-round SET (compact card encoding)

A generalized SET with q values is a selection of exactly q distinct cards
such that, independently in every attribute, their q values are either all
equal or all different. Here q=6. Values and all indices below are 0-based.

The dealt cards are specified exactly by a 3-partite graph. Color classes are
0,...,2; every class has local vertices 0,...,3. For each color
pair i<j, the line below contains 4 fixed-width hexadecimal bitmasks, one for
each vertex a of color i in increasing order. Bit b (the least-significant bit
is bit 0) is 1 exactly when color-i vertex a is adjacent to color-j vertex b.
Leading zeroes are significant only as padding.

0,1: 0 0 4 b
0,2: a 1 1 1
1,2: 4 b 0 3

This graph losslessly specifies the actual generalized-SET cards using the
construction below. There are 24 attributes named
(i,j,a), where i and j are distinct colors and 0<=a<4. There are 6 value
labels: P_i for each color i, and Q_ij for each unordered pair i<j.

* Vertex-card V(i,a) has value P_i in every attribute except (i,j,a), for each
  j!=i, where its value is Q_min(i,j),max(i,j).
* For every displayed graph edge joining (i,a) and (j,b), i<j, edge-card
  E(i,a,j,b) has value Q_ij in every attribute except (i,j,a), where it has
  P_i, and (j,i,b), where it has P_j.

You must select one vertex-card V(i,a_i) for every color and the edge-card
E(i,a_i,j,a_j) for every color pair i<j. These are 6 distinct cards. They
form a generalized SET exactly when every prescribed edge-card exists; the
complementary exceptions above then make every attribute contain all 6
different value labels.

Output the local vertex labels [a_0,...,a_2] as one JSON array of exactly
3 integers. Position i is color i, each entry is in 0,...,3, order is
therefore fixed, and equal numeric labels in different colors are allowed.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format only: <answer>[0, 0, 0]</answer>
Output nothing else inside the tags.
```

The answer is `[3, 3, 0]`; `verify(inst, [3, 3, 0])` returns `(True, "ok")`. Dropping its last entry returns `(False, "wrong number of color choices: expected 3, got 2")`. A person can solve this demo by decoding three four-bit rows and checking at most three edges.

## Difficulty presets

| preset | source `k` | part size | density / 10,000 | status |
|---|---:|---:|---:|---|
| demo | 3 | 4 | 3500 | hand-solvable illustration |
| easy | 24 | 56 | 7100 | **shipping; bare, hinted, and attack gates pass** |
| medium | 24 | 72 | 6900 | larger fixed-answer haystack |
| hard | 24 | 96 | 6720 | largest named fixed-answer haystack |

## Gate results

| gate | final measurement |
|---|---|
| G1 | 12/12 planted witnesses verified; 3 demo certificates fully expanded coordinate-by-coordinate |
| G2 | empty, dropped, swapped, duplicated, and out-of-range corruptions rejected with 5 distinct reasons |
| G3 | tagged prose plus fenced JSON round-tripped |
| G4 | 0 hits / 200,000 structure-aware guesses; candidate space `56^24` |
| G5 | shipping density estimate 0/200,000; demo exact count 5/64; strongest baseline 10,000,008 nodes and 24.894 s, unsolved |
| G6 | degree, greedy, 256 restarts, centered spectral, and ten-million-node DPLL each solved 0/8 |
| G7 | work sizes 33, 615,400, 988,693, 1,711,439; doubled `n=48` instance built and verified |
| G8 | 60/60 relabelling invariance checks, 3 transformed witnesses verified, 20/20 unrelated keys distinct |
| G9 | 67 chars, 17 estimated tokens, 24 atoms, 276 intended pair checks; hinted verdict `hardened` |

## Bare oracle loop

| model | seed | solved | result |
|---|---:|---:|---|
| Gemini 3.1 Pro Preview | 1991235567 | no | proposed tuple missed edge `(0,4)` |
| Grok 4.6 | 122048006 | no | proposed tuple missed edge `(0,14)` |
| Claude Sonnet 5 | 157434013 | no | empty length-limited response after using the 32k completion budget |

The harness verdict is `hardened` at `easy`, with 0/3 scored attempts solved.

## G9 arms

| arm | solved / scored attempts | note |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; one additional non-counting Grok timeout was redrawn |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is `0.0`. Thus this pool showed no measurable response to the claimed reduction-recognition hint; it neither exposed the answer nor improved success. The answer size is 67 characters / 24 atomic entries, and checking a proposed compact route needs 276 edge-bit tests.

## Use

```python
from gen_1309_6504 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit instances with:

```bash
scripts/emit.sh 1309.6504 20 easy
```

## Caveats

The W[1]-hardness theorem is worst-case; it does not prove this planted threshold distribution hard. The ten-million-node DPLL cap, four construction-aware attacks, and oracle runs are evidence, not a lower bound. An uncapped exact search eventually succeeds. No external SAT/ILP/SDP solver or multi-start spectral eigensolver was run; the spectral probe uses 12 centered power iterations, and DPLL uses one least-constraining-value order.

The 0/200,000 density observation is under the declared uniform one-vertex-per-color prior. It neither proves uniqueness nor excludes other cliques. Forced planted edges create a possible signal even though vertex labels are uniform; maximum-degree and spectral attacks did not recover it on the tested seeds. The canonical key is a strong degree/neighbor-degree invariant, not a complete graph-isomorphism canonical form, so rare nonisomorphic collisions are possible.

The 182k-token shipping prompts are large. Three Claude arm calls returned no content after consuming their reasoning/output budget, so part of the observed oracle failure may be context or budget pressure; the other six scored calls returned concrete wrong witnesses. Finally, the answer is a compact expansion of 300 SET cards from the paper's central reduction. This preserves exact card semantics but makes the computational core graph search and the essentiality `licensed_reduction`, not native SET-domain coverage.
