# Acyclic edge-colouring of disguised circular ladders

Paper: Manu Basavaraju and L. Sunil Chandran, [“Acyclic Edge Coloring of
2-degenerate Graphs”](https://arxiv.org/abs/0803.2433) (arXiv:0803.2433v2).

> **Completion status:** complete. Every local gate passes and the script-owned
> no-tool oracle loop hardened the `easy` preset at its first rung (0/3 solved).
> The structural-hint and placebo diagnostics also each recorded 0/3 solved.

## Profile

| field | value |
|---|---|
| Track | **B** — an efficient general algorithm exists |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate | integer tuple: one colour per edge |
| native objects | connected non-regular subcubic graph; acyclic four-edge-colouring |
| intuition | symmetry: suppress degree-two chains to expose two ladder rails with the same periodic pattern |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

The solver receives an ordinary finite graph as a shuffled edge list and must
colour every edge with `0,1,2,3`. Equal colours may not meet at a vertex, and
the union of any two colours must contain no cycle. The checker first compares
incident colours, then uses exact union-find cycle detection on each of the six
colour pairs. It accepts any valid colouring and never reads the planted one.

Section 1 of the paper gives exactly this definition, explicitly identifies
connected non-regular subcubic graphs as 2-degenerate, and states Theorem 1:
`a'(G) <= Delta+1`. Thus four colours suffice here because `Delta=3`. The
certificate is known by transformation: start with a proved periodic colouring
of a prism with one subdivided rung, subdivide pairwise nonincident edges, and
carry the colours through each new path. Contracting a subdivided path would
turn any alleged new bichromatic cycle into an old one.

## Why Track B, not Track A

The paragraph immediately after Theorem 1 says the proof is constructive and
yields an `O(Delta*N^2)` algorithm. Claiming Track A would therefore be false.
At the shipping preset, `Delta=3`, `N=154`, and the paper's nominal
scale is `3*N^2 = 71,148` work units. The executable exact MRV reference proxy
solved 8/8 instances, averaging 101,700 candidate-colour checks, 324,887
bichromatic-path vertex visits, 226 search nodes, and 0.191661 seconds in the
fresh gate run (0.205427 seconds in the earlier uncontended benchmark).

The compact route is different: identify and suppress the visible degree-two
chains, use the unique length-three rung as an anchor, walk the two rails, and
apply the periodic four-colour pattern while lifting through subdivisions. The
reported post-insight count is 226 colour assignments. The paper also makes
the easy regimes explicit at the opening of Section 3: pendant edges extend
immediately, and a graph consisting only of a cycle is directly three-colourable.
This generator avoids forests and lone cycles, but it remains a specially
structured ladder distribution rather than a claim about average 2-degenerate
graphs.

## Worked demo (`n=4`, seed 7)

The complete rendered edge data are:

```text
vertices: 0..9; colours: 0..3
0: 3 6
1: 2 4
2: 1 8
3: 4 9
4: 2 5
5: 6 8
6: 8 9
7: 0 7
8: 5 7
9: 4 7
10: 2 3
11: 0 1
12: 5 6
13: 3 9
```

The task is to return 14 colours in edge-number order, with properness and no
bichromatic cycle as defined above. One answer is:

```text
<answer>[2,3,0,2,2,3,1,2,3,1,1,1,0,3]</answer>
```

`verify(inst, answer)` returns `(True, "ok")`. Changing edge 11 to colour 2
returns `(False, "not proper at vertex 0: edges 7 and 11 both have colour 2")`.
A person can solve and check this demo on paper; the three larger rungs are not
intended for manual edge-by-edge search.

## Difficulty presets

| preset | rail length | extra subdivisions | vertices | edges / answer atoms | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 0 | 10 | 14 | hand example; hardener skips it |
| easy | 72 | 8 | 154 | 226 | **ships; oracle-hardened 0/3** |
| medium | 76 | 10 | 164 | 240 | available escalation |
| hard | 80 | 12 | 174 | 254 | last rung below the 256-atom cap |

Further growth returns `cap_bound`: a complete edge-colouring necessarily adds
answer atoms, and the graph already uses the available fixed-length axes
(random subdivision positions and crowding) without changing the witness type.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified; 12/12 JSON-native |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | tagged, fenced, prose-surrounded answer round-tripped |
| G4 | **0/200,000** valid under the structure-aware proper-colouring prior; 244-bit candidate space; 718.207322 s on a heavily shared host |
| G5 | shipping sampled density 0/200,000; demo exact count 20,064 of 45,312; strongest cheap attack 8 restarts, 0.005628 s average; reference 0.191661 s |
| G6 | five attacks, each 0/8; exact reference 8/8 |
| G7 | doubled instance has 442 edges, verifies, and raises the language from 244 to 478 bits |
| G8 | 60/60 keys invariant under real relabellings; 60/60 carried witnesses verify; 20/20 unrelated keys distinct |
| G9 | bare 0/3, hinted 0/3, placebo 0/3; 453 characters, about 114 tokens, 226 atoms, 226 intended colour assignments |

The G6 failures were endpoint-degree outlier scoring, input-order proper
first-fit, input-order acyclic first-fit, a period-four edge-list ansatz, and
eight randomized acyclic first-fit restarts. No attack had a success in eight
seeds.

## Oracle loop

The bare hardener held at `easy` without escalation. Every reply parsed; none
verified, so these are mathematical failures rather than transport or parser
failures.

| preset | model | seed | solved | verifier result |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 598293828 | no | improper at vertex 0 |
| easy | GPT-5.6 Terra | 1931301843 | no | 241 colours supplied; 226 required |
| easy | Gemini 3.8 Flash | 1183361214 | no | improper at vertex 2 |

## G9 arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. The named symmetry did not measurably help this small
sample: recognition alone was not enough to execute and transcribe the full
colouring. The answer has 453 characters (about 114 tokens), 226 atomic
elements, and the intended post-insight route uses 226 colour assignments.

## Use

```python
import gen_0803_2433 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
question = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

Emit dataset instances with:

```bash
bash scripts/emit.sh 0803.2433 20 easy
```

## Caveats

- The paper proves the certificate-producing problem is in P. This family has
  only a no-tool compression claim; the oracle evidence is 0/3 over the
  hardener's configured two-vendor pool, not a complexity-theoretic claim.
- The executable reference is an exact generic MRV/backtracking proxy with an
  exponential worst case, not a transcription of the paper's 21-page
  recolouring proof. The paper's `O(Delta*N^2)` bound is separately reported;
  the proxy measurement is empirical for this distribution.
- The G4 prior is stronger than raw random colour noise: it samples uniformly
  from proper colourings of the once-subdivided ladder and from both locally
  proper lifts at every added subdivision. It is still a family-specific subset
  of every proper colouring of the final graph, so 0/200,000 is a sampled
  conditional density, not an exact probability over all proper final
  colourings and not a complexity proof.
- The instances are disguised circular ladders. A graph-isomorphism-aware
  specialist can recover that structure in polynomial time; that recovery is
  the intended insight, not an untried threat. The panel did not test SAT/ILP
  encodings, sophisticated constraint programming, or learned graph models.
- `canonical_key` is complete for the generator's anchored prism coordinates
  up to reflection and rail exchange. It is not claimed to canonize arbitrary
  subcubic graphs outside this family.
