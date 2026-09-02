# Full rainbow matching generator

This module turns Chakraborti and Loh's [*Large rainbow matchings in edge-colored graphs*](https://arxiv.org/abs/2011.04650) into a witness problem. The solver receives triples `(colour, left vertex, right vertex)` and must choose one of every colour while using every left and right vertex once. This is precisely a full rainbow matching in the paper's properly edge-coloured bipartite-multigraph language, or equivalently a perfect matching in a 3-partite 3-uniform hypergraph. Verification is a linear scan: check membership, length, ranges, and uniqueness in all three coordinates.

## Why this is a defensible hard family

Section 1 of the source paper fixes the definitions of multigraph, proper edge-colouring, and rainbow matching. Its Theorem 1.7 and Section 4 prove existence through a nibble/local-lemma construction when each colour has more edges than the maximum degree by a prescribed slack; Proposition 2.4 gives the simpler `4e`-slack regime. Section 3/Theorem 1.9 gives another guaranteed regime with roughly twice as many colours as the requested matching size. This generator avoids all three: there are exactly `n` colours, the target has size `n`, and both colour-class size and maximum degree equal `d`.

Computational hardness is not a result of the source paper, so the claim also uses Le and Pfender's [*Complexity Results for Rainbow Matchings*](https://arxiv.org/abs/1312.7253): Theorem 1 states NP-completeness on edge-coloured bipartite graphs, and Theorem 8 proves APX-completeness on properly edge-coloured `P4`-free bipartite graphs with each colour used at most twice. A full matching here is the standard 3-dimensional perfect-matching witness. Their Section 5 notes FPT in solution size, which is why `n` grows rather than remaining a small parameter. The worst-case results do not prove this planted distribution hard; the attack panel and oracle loop provide distribution-specific evidence.

The answer is sampled first as two random permutations. Four further permutation layers are added at the shipping rung. Every layer is itself a full solution, every displayed edge lies in such a layer, every colour class is a matching, and every colour/left/right degree is exactly five. Thus an individual planted edge has no degree or frequency outlier.

## Worked easy example (`n=10`, `d=3`, seed 0)

The complete rendered instance is:

```text
Find a full rainbow matching in a coloured bipartite multigraph

There are three separately labelled sets, each of size 10:
- colours 0 through 9;
- left vertices L0 through L9; and
- right vertices R0 through R9.

Each input line `c l r` is one edge from left vertex Ll to right vertex Rr,
with colour c.  All labels are 0-indexed and both bounds are inclusive.
Different colours may give parallel edges with the same endpoints.  No exact
triple is repeated.  The order of the input lines has no meaning.

Choose exactly 10 listed triples so that every colour occurs exactly once,
every left vertex occurs exactly once, and every right vertex occurs exactly
once.  Thus the chosen edges are pairwise vertex-disjoint and have pairwise
distinct colours.  The order of your chosen triples has no meaning, and you
may not repeat a triple.

The 30 input edges are:
4 3 0
4 7 3
7 0 2
6 5 0
8 9 3
0 6 5
4 9 4
5 0 2
5 2 6
1 1 9
9 6 5
3 0 9
9 9 0
3 3 3
5 4 1
2 5 5
2 4 6
8 4 4
7 6 7
6 2 7
3 5 6
0 7 9
2 1 8
1 3 2
9 8 8
7 7 1
0 8 1
8 2 7
6 1 8
1 8 4

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 10 triples `[c,l,r]` using decimal integers.
Example of the syntax: <answer>[[0,2,1],[1,0,3]]</answer>
Output nothing else inside the tags.
```

One answer is `[[0,7,9],[1,8,4],[2,1,8],[3,5,6],[4,3,0],[5,4,1],[6,2,7],[7,0,2],[8,9,3],[9,6,5]]`. `verify(inst, answer)` returns `(True, "ok")`. Replacing its first triple by a duplicate of the second returns `(False, "a selected edge triple is duplicated")`.

## Difficulty

| preset | `n` | choices/degree `d` | edges | status |
|---|---:|---:|---:|---|
| easy | 10 | 3 | 30 | all three oracles solved it; example only |
| **medium** | **32** | **5** | **160** | **ships; all three oracle attempts failed** |
| hard | 56 | 5 | 280 | available; oracle loop did not need it |

An earlier candidate `(n=36,d=4)` was rejected before the oracle run because 256 randomized greedy restarts solved 1/8 gate seeds. Increasing crowding to five choices made the same attack solve 0/8 at `n=32`.

## Gate results at the shipping preset

| gate | measured result |
|---|---|
| G1 | 15/15 plants verified across every preset and five seeds |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | 32/32 triples recovered through prose, tags, whitespace, and a Markdown fence |
| G4 | 0/200,000 valid guesses; prior chooses one genuine edge independently per colour; space `5^32 = 23,283,064,365,386,962,890,625` |
| G5 | exactly 2 solutions among 16,384 candidates (`n=14,d=2`), fraction `0.0001220703125` |
| G6 | outlier 0/8, deterministic greedy 0/8, 256-restart greedy 0/8; all coordinate degrees `[5,5]` |
| G7 | doubling `n` from 32 to 64 built 320 edges and the plant verified |
| G8 | 140/140 invariance checks, 120/120 carried witnesses, 20/20 unrelated keys distinct |

## Oracle loop

Effort was `medium`; the master seed and full replies are in `.meta.json` and `llm_loop_transcript.jsonl`.

| preset | model | seed | result | why |
|---|---|---:|---|---|
| easy | Gemini 3.1 Pro Preview | 1664781888 | solved | witness verified |
| easy | Claude Sonnet 5 | 221841994 | solved | witness verified |
| easy | GPT-5.6 Terra | 1274454748 | solved | witness verified |
| medium | Claude Sonnet 5 | 540318649 | failed | empty length-limited reply after 32,000 completion tokens |
| medium | Grok 4.6 | 1695385519 | error | 900-second total deadline; not scored |
| medium | Grok 4.6 | 206699008 | error | 900-second total deadline; not scored |
| medium | Grok 4.6 | 168402772 | error | 900-second total deadline; not scored |
| medium | Gemini 3.1 Pro Preview | 504034648 | failed | parsed witness repeated a left endpoint |
| medium | GPT-5.6 Terra | 348281915 | failed | parsed witness repeated a left endpoint |

The harness verdict is `hardened`, with one escalation and shipping parameters `{"n":32,"choices":5}`. The Anthropic result is weaker evidence than a wrong parsed witness because its reasoning exhausted the output budget; the two remaining deciding vendors did return checkable, wrong answers.

## Use

From the repository root:

```python
import importlib.util
import json

path = "results/2011.04650/gen_2011_04650.py"
spec = importlib.util.spec_from_file_location("rainbow_gen", path)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
answer = gen.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert gen.verify(inst, answer) == (True, "ok")
```

Emit a corpus with `bash scripts/emit.sh 2011.04650 20 medium`.

## Caveats

- Worst-case NP-completeness does not establish average-case hardness of these regular, resolvable instances. In particular, the promise that all edges decompose into solution layers could admit a specialized future algorithm.
- G4 samples independent uniform choices from each colour class. It incorporates valid-edge, answer-size, and one-per-colour constraints, but it does not model backtracking, exact-cover/SAT/ILP solvers, or a sampler conditioned on endpoint-disjointness.
- The tested attacks were endpoint-pair outliers, deterministic MRV/least-conflict greedy, and 256 randomized restarts. No spectral/tensor method, dancing-links solver, sophisticated local search, or layer-factorization attack was tested.
- Sequential forbidden-permutation sampling can leave higher-order correlations even though every individual coordinate degree is identical.
- `canonical_key` is invariant under input order, independent relabelling, and all six coordinate-role permutations, but rooted colour refinement is not a complete hypergraph-isomorphism canon; rare nonisomorphic collisions are possible.
- Small `n` is easy, as both the easy oracle results and the solution-size FPT observation warn. The claim applies to the shipping preset, not the worked example.
