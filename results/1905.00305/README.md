# Verified generator for arXiv:1905.00305

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | integer tuple (a compressed colouring extension) |
| Native objects | precoloured graph, closed neighbourhoods, compressed 2-CNCF extension |
| Intended intuition | symmetry: a complete vertical-translation orbit partitions the cyclic columns |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 4.4, Theorem 4.5 |

## What the family is and why it is trustworthy

[Bodlaender, Kolay, and Pieterse, *Parameterized Complexity of Conflict-free Graph Coloring*](https://arxiv.org/abs/1905.00305) defines a 2-CNCF colouring as a red/blue vertex colouring in which every closed neighbourhood has a colour occurring exactly once. Section 4.4 reduces Monotone Exact SAT to extension of a partial 2-CNCF colouring. This generator hands the solver that precoloured graph in the paper's compact incidence representation. The requested list selects the variable classes whose occurrence vertices become blue; `verify` expands the full graph and counts both colours in every closed neighbourhood. It accepts any valid exact cover, not only the planted one, and never reads `inst["answer"]`.

Generation is inverse: a random base vector over `Z_n` is chosen first, and all `n` of its vertical translations form a known exact cover. Every decoy orbit is sampled by the same rule but has one random translation omitted. Rows are shuffled. Thus planted and decoy rows have identical size and the same individual marginal distribution; the certificate comes from construction, not search.

There is one arXiv-v1 inconsistency worth making explicit. The construction bullet says `u_i--R2`, but Figure 6 and the proof's three subsequent neighbourhood identities require `u_i--R1`. The literal `R2` edge makes every nontrivial constructed colouring fail at `R2`. The module follows Figure 6 and the proof (`u_i--R1`) and tests every resulting neighbourhood.

## Why Track B

Theorem 4.5 proves NP-hardness for unrestricted 2-CNCF-Coloring-VC-Extension, but that worst-case theorem is **not** claimed for this planted distribution. The generated subfamily has a disclosed polynomial algorithm: normalize every row by subtracting its first coordinate modulo `n`, group equal signatures, and take a group of size `n`. This costs `O(N·width)`; at shipping it used exactly 1,084 modular subtractions and at most 0.000914 seconds in the final eight-seed run. Theorem 4.4 also gives a polynomial kernel for the paper's `q=2` extension problem parameterized by vertex-cover size, while Theorem 3.1 gives a `(2q²)^t n^O(1)` treewidth DP. Here those parameters grow with the instance.

The compact route notices that the first coordinate difference already separates the generated orbit families. It needs 271 modular subtractions. In contrast, domain-standard MRV Algorithm X averaged 20,295 search nodes, 75,943,619 row-element compatibility probes, and 2.284 seconds at shipping (maximum 37,221 nodes, 137,559,040 probes, and 5.954 seconds). Algorithm X and the full signature scan are easy for a machine; neither is realistically executable row by row in the evaluated no-tool context. The challenge is recognizing the translation invariant that compresses the work below the 300-operation cap.

## Worked demo

This is the complete rendering for `make_instance(n=3, decoy_orbits=1, width=2, seed=7)`:

```text
Find a compressed 2-colour closed-neighbourhood conflict-free colouring.

A closed neighbourhood N[v] consists of v and every vertex adjacent to v.
A red/blue colouring is conflict-free on closed neighbourhoods (2-CNCF)
when, for every vertex v, at least one of the two colours occurs exactly
once in N[v].  Adjacent vertices are allowed to have the same colour.

The graph is specified compactly from the incidence table below.
Elements are pairs (c,a), with columns c=0,...,1 and values
a=0,...,2.  There is one candidate set V_j for each numbered row.
The row lists the value a in each column c, so it contains exactly the
elements (0,a_0),(1,a_1),... in that order.

Graph vertices: R1, R2, B1; one U_(c,a) per element; one V_j per set;
and one W_(c,a),j whenever row j contains element (c,a).
Precolour R1, R2, and every U_(c,a) red.  Precolour B1 and every V_j blue.
Edges are exactly R1--B1, R1--U_(c,a) for every element, R2--V_j for
every set, and W_(c,a),j--U_(c,a) plus W_(c,a),j--V_j for every incidence.
There are no other edges.

Your answer is a list S of exactly 3 set IDs.  It represents the full
extension that colours W_(c,a),j blue iff j is in S, and red otherwise.
Find S for which the resulting full red/blue colouring is 2-CNCF.
Set IDs are 1-based, repetitions are forbidden, order has no mathematical
meaning, and the submitted list must be in strictly increasing order.

n = 3; number of columns = 2; number of sets = 5
Incidence rows (set_id: a_0 a_1 ...):
1: 0 2
2: 0 0
3: 2 1
4: 1 1
5: 1 0

Give your final answer inside <answer></answer> tags, as a JSON array
of exactly 3 increasing set IDs.
Format example only (shown with three IDs): <answer>[1, 4, 9]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[1, 3, 5]</answer>`. `verify(inst, [1, 3, 5])` returns `(True, "ok")`; dropping one ID gives `verify(inst, [1, 3]) == (False, "expected exactly 3 set IDs")`. A person can solve this demo on paper by finding three disjoint rows covering all six `(column,value)` pairs.

## Difficulty presets

| preset | `n` selected | decoy orbits | width | candidate rows | status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 1 | 2 | 5 | hand-scale; skipped by hardener |
| easy | 13 | 8 | 6 | 109 | oracle solved 1/3; rejected as shipping level |
| medium | 17 | 11 | 6 | 193 | oracle solved 1/3; rejected as shipping level |
| **hard** | **19** | **14** | **5** | **271** | **ships; oracle solved 0/3** |

`escalate` first narrows the same 271-row instance to increase Algorithm-X backtracking without lengthening the answer, then grows `n` while keeping the compact scan below 300 rows.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 planted verifies | pass | 16/16 preset/seed instances; JSON round-trip included |
| G2 corruption | pass | drop, swap, duplicate, empty, and out-of-range all rejected with 5 distinct reasons |
| G3 parser | pass | tagged JSON recovered from prose and a Markdown fence |
| G4 guess resistance | pass | 0/200,000 uniform increasing 19-subsets; language size `C(271,19)` |
| G5 density + baseline | pass | shipping sampled density 0/200,000; demo exactly 1/10; Algorithm X mean 20,295 nodes and 75,943,619 probes |
| G6 adversaries | pass | four attacks, 0/8 each; Algorithm X and translation scan both solve 8/8 as Track B expects |
| G7 scale | pass | doubled `n=38` builds, verifies, and has a larger search space |
| G8 canonical key | pass | 20 arbitrary relabellings, 20 carried witnesses, 20 composed cyclic symmetries, 20/20 unrelated keys distinct |
| G9 suitability | pass | 73 chars, 19 atoms, about 19 tokens; intended route 271 exact operations |

The four failing G6 attacks were element-degree outlier ranking, no-backtracking MRV greedy, 256 random disjoint-packing restarts, and the in-context guess consisting of the first `n` displayed rows. Each was tested on eight fresh shipping instances.

## Bare oracle loop

| preset | seed | model | solved | outcome |
|---|---:|---|---|---|
| easy | 1118012909 | Gemini 3.8 Flash | yes | valid cover |
| easy | 628222403 | GPT-5.6 Terra | no | duplicate IDs |
| easy | 87364469 | GPT-5.6 Terra | no | expanded neighbourhood invalid |
| medium | 69429235 | Gemini 3.8 Flash | yes | valid cover |
| medium | 1803604800 | GPT-5.6 Terra | no | expanded neighbourhood invalid |
| medium | 1644613439 | GPT-5.6 Terra | no | expanded neighbourhood invalid |
| hard | 1380465127 | Gemini 3.8 Flash | no | expanded neighbourhood invalid |
| hard | 1808803570 | GPT-5.6 Terra | no | expanded neighbourhood invalid |
| hard | 975474805 | GPT-5.6 Terra | no | expanded neighbourhood invalid |

Every reply containing an answer parsed; the hard verdict is not a parser failure.

## G9 arms

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0/3 | the shipping prompt held |
| structural hint | 3/3 | naming the modular-difference invariant exposes the compact route |
| placebo hint | 0/3 | a matched nonstructural sentence did not help |

Hinted minus placebo is `+1.0`. This strongly supports the declared `symmetry` intuition: difficulty lies in finding the invariant, not in transcribing the 19-ID answer after it is known. One placebo attempt exhausted the harness's 32k completion budget and emitted no answer; the other two emitted parseable but invalid witnesses. G9(a,b) is diagnostic only. The gated G9(c) measurements are 73 characters, 19 atomic elements, approximately 19 tokens, and 271 exact arithmetic operations.

## Use

```python
import gen_1905_00305 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 1905.00305 20
```

## Caveats

This is Track B: the public modular coordinates deliberately admit the efficient full-signature algorithm above, so it must never be described as average-case NP-hard. Removing or scrambling those coordinates would remove the intended compact route, not strengthen this benchmark. The 0/200,000 guess figure is a point estimate under the exact declared prior—uniform size-19 subsets—not a confidence bound and not a claim about heuristic solvers. Algorithm X was implemented and measured, but no industrial SAT/ILP/CP solver or alternative dancing-links implementation was tried. The canonical key uses bipartite colour refinement plus intersection profiles rather than complete graph isomorphism; it is invariant under the tested relabellings but could theoretically collide on nonisomorphic incidence systems. Finally, the paper's `u_i--R2` typo is resolved from Figure 6 and the proof as explained above rather than from an erratum.
