# Verified symbolic clique-factor generator

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | exact symbolic congruence rule |
| Native objects | balanced four-partite graph; perturbed host; transversal `K4`-factor |
| Intuition | invariant: a short signed balance of the four partwise tag sums isolates the factor modulus |
| Domain essentiality | native, with the paper-licensed partite restriction from Lemma 2.6 and Section 7.2 |

## What this generates

The source is Antoniuk, Kamcev, and Reiher, [*Clique factors in randomly perturbed graphs: the transition points*](https://arxiv.org/abs/2410.11003). A generated instance gives four equal graph parts, six exact cross-adjacency matrices, and one integer tag on every vertex. The solver must return a modulus and four checksum weights. Reducing the tags modulo that modulus pairs one vertex from each part; the checker confirms that every resulting quadruple has all six edges and that these `K4` copies cover every vertex exactly once.

Generation is inverse. The modulus, residue classes, checksum relation, and factor exist before any host or perturbing edge is emitted. Six cyclic host graphs contain the equal-residue edges; independent cross edges are then added. The host minimum degree is at least `N/4`, and the perturbation probability follows the paper's `r=4, s=3` transition scale `N^(-3/5)`. Verification never reads `inst["answer"]`.

The full paper model adds random edges everywhere. This module exposes the balanced four-partite spanning subgraph and asks for a transversal factor. Lemma 2.6 and Section 7.2 explicitly use these partite factor objects; a factor found here is also a factor in the full supergraph. No graph, SAT, finite-field, or integer-coordinate surrogate replaces the graph.

## Why Track B

Section 2 fixes the factor definition. Theorem 1.2 gives the transition at `r=4, s=3, alpha=1/4`, namely `p_s(N)=N^(-3/5)`. The introduction identifies the easy `alpha>=3/4` regime, where Hajnal–Szemerédi needs no random edges, and Theorem 1.1 gives the different `N^(-2/s)` scales away from transition points. Section 3's below-threshold construction normally has no factor, so it cannot supply positive witnesses.

This is not a Track A claim. A complete bounded search over checksum weights is an exact algorithm for this promised distribution. At the shipping preset it solved 8/8 instances in at most **469,373 counted operations and 0.111 s**, with complexity `O(B^3 + Bn)` for four parts. The compact route notices that the relation is a signed ordering of four small coefficients; it used **36 exact operations** on the measured shipping instance. Graph-only transversal-clique enumeration plus exact cover is the much larger fallback.

## Worked demo

The `demo` preset is hand-scale: 20 vertices and six 5-by-5 matrices. A person can solve it by summing four short tag lists, testing the small signed balance, and checking five residue-defined cliques.

```text
SYMBOLIC TRANSVERSAL K4-FACTOR

The graph has four named parts P0,P1,P2,P3, each with vertices 0..4.
There are no usable edges within a part. For each pair Pa,Pb with a<b,
matrix M_ab has rows in Pa and columns in Pb; 1 means adjacent.

Tags:
P0: 945703 1057536 746518 884936 1023564
P1: 1141514 783235 947813 746731 1084962
P2: 842527 879659 1017867 1021241 930723
P3: 1118302 927981 1036432 665706 872911

M_01: 11110 10010 01011 00011 01100
M_02: 01110 10010 01001 10101 01100
M_03: 10010 00101 00110 11000 01011
M_12: 10100 00101 01011 00111 11001
M_13: 10111 01110 11010 10001 10100
M_23: 10101 00110 01001 10011 11000

Find q with 2^7 <= q < 2^8 and four distinct nonzero weights in
[-8,8], of sum zero and gcd one. Their weighted part-tag sum must have
absolute value q. Modulo q, every part must have the same five distinct
residues, and each equal-residue quadruple must be a K4.
```

Answer:

```json
{"modulus":211,"weights":[1,-3,3,-1]}
```

`verify(inst, answer)` returns `(True, "ok")`. Dropping the last weight returns `(False, "too few weights: expected exactly four")`.

## Difficulty presets

| preset | part size `n` | vertices `N` | modulus bits | coefficient bound | perturbation | result |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 20 | 8 | 8 | 0.166 | hand-scale |
| easy | 23 | 92 | 31 | 32 | 0.066 | **ships; oracle held** |
| medium | 41 | 164 | 47 | 48 | 0.047 | not needed |
| hard | 61 | 244 | 61 | 64 | 0.037 | not needed |

The answer remains five integer atoms on every rung. Difficulty grows through the graph haystack, modulus/tag sizes, bounded-relation space, and lower perturbation density—not by lengthening the witness.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified; every answer JSON-round-tripped |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | realistic fenced/prose response round-tripped; garbage rejected |
| G4 | 0/200,000 structure-aware random certificates valid; declared space `146,655,953,289,216` |
| G5 | shipping sampled density 0; demo has exactly 4 valid certificates in 218,112; reference 8/8, max 469,373 operations / 0.111 s |
| G6 | five attacks, each 0/8; successful Track B reference 8/8 |
| G7 | doubled part size 46 (184 vertices) built and verified in 0.004 s |
| G8 | 20/20 relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 44 characters, 11 estimated tokens, 5 atoms, 36 intended-route operations |

## Oracle loop

All calls used the script-owned pool at medium reasoning effort. The easy rung held, so the ladder stopped there.

| preset | model | seed | solved | outcome |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 1279761054 | no | parsed; checksum identity failed |
| easy | Gemini 3.8 Flash | 1341552626 | no | exhausted response budget without an answer |
| easy | OpenAI GPT-5.6 Terra | 116776493 | no | parsed; checksum identity failed |

## G9 arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted - placebo = 0.0`. The hint bought no observed success, so these runs do not show that merely naming the checksum invariant is sufficient; arithmetic and coefficient ordering remained obstacles. The diagnostic is not used as a gate.

## Use

```python
import json
import gen_2410_11003 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
text = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(wire)
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2410.11003 20
```

## Caveats

- This is a promised, tagged Track B distribution, not evidence of average-case hardness for unlabelled `K4`-factor. Reading the generator reveals the four-coefficient prior immediately; the evaluated solver sees only `render(inst)`.
- The public tags are auxiliary benchmark data absent from the paper's bare random-graph model. The graph remains load-bearing—`verify` checks every clique edge—but the compact route is an arithmetic invariant rather than the paper's probabilistic proof.
- The deterministic host already contains the inverse-generated factor; the transition theorem fixes the graph regime but does not produce the finite certificate.
- `0/200,000` is an observed density under the exact bounded language prior, not a statistical proof that every alternative prior has probability below `10^-6`.
- The panel tests degree outliers, local edge gcds, greedy bounded relations, 256 random restarts, and a plausible symmetric ansatz. It does not implement LLL/PSLQ or a full graph-only Algorithm X run. A complete bounded relation search is stronger for the posed certificate and is openly reported as successful.
- Canonicalization is complete only for relabellings that preserve attached tags and the four-part structure; it does not identify unrelated tagged presentations that happen to encode isomorphic unlabelled graphs.
