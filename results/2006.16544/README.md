# Properly coloured tight Hamilton cycles (arXiv:2006.16544)

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: a normalized cyclic vertex ordering |
| Intuition | change of variables |
| Domain essentiality | native |
| Reduction kind | none |

This generator asks for a properly coloured tight Hamilton cycle in an exactly
specified 4-uniform hypergraph.  The hypergraph is given compactly by a vertex
bipartition and a cubic base graph; the checker expands the displayed predicate,
checks every cyclic 4-set, and compares exact integer colours.  It is based on
[Properly colored Hamilton cycles in Dirac-type hypergraphs](https://arxiv.org/abs/2006.16544),
especially the definitions and Theorem 1 in Section 1 and the absorbing argument
in Section 3.

## Trust and hardness claim

The certificate is known by inverse generation, not by solving: a random base
Hamilton cycle is sampled first, a disjoint random perfect matching supplies
same-distribution decoy edges, and the base cycle is carried to the alternating
tight cycle of the 4-graph.  `verify` never reads `inst["answer"]` and accepts any
normalized valid cycle.

This is deliberately Track B.  Exact GF(2) Gaussian elimination recovers the
public decoder word, parity-classifies the base edges, and traces the cycle in
`O(r*b^2 + |E|*b)` bit operations.  At the shipping preset it solved 8/8 seeds
with a median 349,522 counted bit operations and 0.001537 seconds.  The intended
shortcut cancels a common affine offset, recognizes the rotated inverse of
`1+x+x^3`, and then classifies/traces in 259 packed-word XOR/parity operations.
The machine route is fast but not realistically executable without tools from
the 121 dense 88-bit equations printed in the prompt.

The paper's Theorem 1 identifies the easy side that had to be avoided: above
minimum codegree `(1/2+gamma)N`, with sufficiently locally bounded colours, a
properly coloured tight cycle is guaranteed by absorption.  Shipping instances
instead have minimum codegree at least `N/2-8`.  This is the hard side of the
same threshold and matches the `k=4` regime of Garbe--Mycroft
[Theorem 1.5 and Section 8](https://arxiv.org/abs/1609.03101), which proves
NP-hardness at `N/2-O(1)`.  That worst-case theorem motivates the construction;
it is not misreported as distributional hardness, because the public decoder
makes this generated distribution efficiently solvable.

## Worked demo (seed 0)

This is the complete `render(make_instance(seed=0, **DIFFICULTY["demo"]))`:

```text
PROPERLY COLOURED TIGHT HAMILTON CYCLE IN A 4-GRAPH

A 4-uniform hypergraph has vertices and unordered 4-element hyperedges.  A
tight Hamilton cycle is a cyclic ordering of every vertex in which every four
cyclically consecutive vertices form a hyperedge.  It is properly coloured if
every two of those hyperedges that intersect have different colours.

This instance has 16 vertices, numbered 0 through
15, partitioned into the following equal sets:
  A = [0, 1, 2, 4, 5, 7, 11, 14]
  B = [3, 6, 8, 9, 10, 12, 13, 15]

The hypergraph is specified exactly by a cubic simple graph G on A.  Its rows
below are "u v | m", where {u,v} is an undirected edge and m is a public
8-bit hexadecimal annotation.  Leading zeroes are significant only for
width; bit 0 is the least significant bit.
  1 0 | 09
  7 0 | 4a
  0 14 | 8a
  1 2 | e5
  1 4 | b3
  5 2 | a8
  7 2 | 2f
  11 4 | b4
  14 4 | 64
  5 11 | ec
  5 14 | ad
  7 11 | fb

For any 4-set e, put a=|e intersect A|.  It is a hyperedge exactly when:
  * a is 0, 1, or 4; or
  * a=2 and the two A-vertices form an edge of G; or
  * a=3 and none of the three A-pairs is an edge of G.
There are no other hyperedges.  The colour of a hyperedge is its injective
lexicographic rank among all 4-subsets of the numbered vertex set.  Thus two
hyperedges have the same colour exactly when they are the same 4-set; this is
an exact integer colouring, not a floating-point convention.

The following public decoder rows have format "mask | rhs" and mean
parity(mask AND K)=rhs over GF(2), for one promised unique 8-bit word K.
XOR is addition and parity is the number of 1-bits modulo 2.
  2e | 1
  09 | 1
  b2 | 0
  c0 | 0
  78 | 1
  9c | 1
  57 | 0
  a5 | 1
  eb | 1

The instance promises that the G-edges whose annotations m satisfy
parity(m AND K)=0 form a Hamilton cycle of G.  This promise is auxiliary
information for finding a witness; the checker accepts every valid witness,
whether or not it is that promised cycle.

Required projected A-edges that your cycle must contain: {2,5}, {7,11}.

Output exactly 16 distinct vertex identifiers in cyclic
order.  The first must be min(A)=0; entries must alternate A,B;
and to remove reversal ambiguity the A-entry at position 2 must be smaller than
the A-entry at the penultimate position (positions are 0-based here).  Every
vertex must occur once, order matters subject to this normalization, repeats
are forbidden, and all displayed bounds are inclusive.  Projecting the output
to its A entries must include every required edge above.

Give your final answer inside <answer></answer> tags, as comma-separated decimal
integers.  Example format: <answer>0, 9, 2, 7</answer>
Output nothing else inside the tags.
```

The answer is
`[0, 15, 7, 13, 11, 8, 4, 3, 1, 12, 2, 10, 5, 9, 14, 6]`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the final `6`
returns `(False, "answer must contain exactly 16 vertices")`.  A person can
solve this demo on paper: it has only eight A-vertices, two supplied cycle
edges, and an eight-bit decoder.

## Presets

| preset | base n | hypergraph vertices / answer atoms | decoder bits | decoy rows | required edges | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 16 | 8 | 0 | 2 | hand-scale |
| easy | 112 | 224 | 88 | 32 | 0 | **shipping; hardened** |
| medium | 116 | 232 | 92 | 64 | 0 | retained above shipping |
| hard | 120 | 240 | 96 | 96 | 0 | retained above shipping |

No preset was rejected: the first evaluated rung already held.  `escalate`
first adds decoder decoys without lengthening the answer, then permits `n=124`;
beyond that it returns `cap_bound` because the 256-atom output ceiling binds.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted checks passed across every preset; answers JSON-round-trip |
| G2 | empty, dropped, duplicated, out-of-range, and swapped answers all rejected with five distinct reasons |
| G3 | realistic prose/fence/tag response parsed; 224 atoms recovered |
| G4 | 0/200,000 valid structure-aware random candidates; estimated density 0 |
| G5 | shipping density 0/200,000; demo exact valid-answer count 161,280; reference median 349,522 operations / 0.001537 s |
| G6 | four attacks each 0/8; reference decoder 8/8 as expected |
| G7 | doubled 448-vertex instance built and its planted witness verified |
| G8 | 20/20 vertex/decoder-coordinate relabelling invariance, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9 | 1,010 answer characters, 253 estimated tokens, 224 atoms, 259 intended operations; hinted verdict hardened |

The four failing G6 attacks were Hamming-weight outlier selection,
smallest-label greedy tracing, 256 random walks, and the in-context ansatz that
mistakes shuffled RHS order for decoder-bit order.  The successful Gaussian
reference algorithm is correctly reported separately for Track B.

## Bare oracle loop

| model | seed | result | exact reason |
|---|---:|---|---|
| OpenAI GPT-5.6 Terra | 1015939753 | failed | parsed candidate; cyclic 4-set 171 absent |
| xAI Grok 4.6 | 590558277 | error, redrawn | 900 s total deadline |
| xAI Grok 4.6 | 1386068458 | error, redrawn | 900 s total deadline |
| Google Gemini 3.1 Pro Preview | 1559260903 | failed | parsed candidate; cyclic 4-set 0 absent |
| Anthropic Claude Sonnet 5 | 762925753 | failed | empty length-limited response |

The script verdict was `hardened` at `easy` with zero escalations.  Error rows
did not count as model failures.

## G9 arms

| arm | solved / valid attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`.  The named circulant structure bought no measured
success in this three-model sample, so the diagnostic does not show that the
claimed change-of-variables intuition helps these models.  Each arm included
one empty length-limited Sonnet response; the other attempts produced parsed but
invalid cycles (except the two separately recorded bare Grok timeouts).

## Use

```python
import random
import gen_2006_16544 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
text = g.render(inst)
candidate = g.parse_answer("<answer>" + ",".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.random_candidate(inst, random.Random(1)) is not None
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 2006.16544 20
```

The generator and checker use only the Python standard library; `gvlib` and
third-party solver packages are not required.

## Caveats

The colouring is injective, so properness itself is automatic for distinct
hyperedges; the difficulty is finding the tight Hamilton ordering.  This is a
native hypergraph witness and exact hypergraph verification, but it does not
stress colour conflicts, and the decoder annotations are planted auxiliary
structure rather than a feature of the source theorem.  Removing the decoder
or exposing its key would respectively make the family much harder or trivial.

The 0/200,000 density estimate is only for uniformly sampled normalized
alternating orders, with required edges contracted into blocks.  It is not a
bound under decoder-aware or graph-aware priors, and it does not estimate the
number of base Hamilton cycles.  Industrial SAT/ILP encodings, specialized
random-regular-graph Hamilton algorithms, and unbounded exact backtracking were
not tested.  The canonical key uses a strong all-roots distance/edge-layer
invariant rather than complete graph isomorphism, so a pathological collision
is possible even though all 20 unrelated shipping instances differed.  Finally,
three oracle failures were empty length-limited replies; the transcripts make
that limitation explicit rather than treating them as wrong mathematical work.
