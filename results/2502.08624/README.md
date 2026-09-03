# Verified sum-free-subset generator for arXiv:2502.08624

## What the problem is

The source paper is Benjamin Bedert, [*Large sum-free subsets of sets of integers via L1-estimates for trigonometric series*](https://arxiv.org/abs/2502.08624). A set `B` is sum-free when it has no `x,y,z` (repetitions allowed) with `x+y=z`. The solver receives a finite positive-integer set `A` and returns a fixed-size deletion set `D`; the retained set `B=A\D` must be sum-free. This complement representation keeps the witness short. Verification is exact: check membership and cardinality, then test every encoded sum relation.

Generation is inverse. First the module samples one true literal occurrence in every clause of a balanced planted 3-CNF. It then builds the usual clause/contradiction graph, whose sampled occurrences are an independent set, and encodes every graph edge as the unique relation `v_i+v_j=e_ij` in `A`. Keeping every edge label and the planted independent-set vertices is therefore sum-free. Any valid deletion witness is accepted; `verify` never reads `inst["answer"]`.

## Why this is in a hard regime

Bedert's Section 1 and Theorem 1.1 fix the exact definition and guarantee `|A|/3+c log log |A|`; Section 2 gives the easy torus-interval construction behind the one-third bound. Those are extremal existence results, not computational-hardness results, so this generator deliberately asks far above one third. Edwards and Noble, [*The complexity of solution-free sets of integers*](https://arxiv.org/abs/1812.09259), Corollary 3.4 and Theorem 3.5 reduce Independent Set to `x+y=z`-free subset and prove strong NP-completeness even for positive integers. Their Theorem 5.3 also identifies the threshold to avoid: fixed-density requests at or below `kappa=1/3` are trivial yes-instances, while rational densities above it are strongly NP-complete. The shipped retained density is `5250/5850`.

Worst-case NP-completeness does not establish average-case hardness for this planted distribution. The evidence specific to the generator is the local attack panel below and the independent four-vendor oracle run.

## Worked example (`demo`, seed 0)

```text
SUM-FREE SUBSET WITNESS

You are given a finite set A of distinct integers. Produce a deletion set D of exactly 12 distinct elements of A such that the retained set B = A \ D has exactly 51 elements and is sum-free.

Definition: B is sum-free when there do not exist x, y, z in B with x + y = z. The variables are not required to be distinct, so x = y must also be checked. Ordinary integer addition is used (not modular arithmetic).

The answer is the unordered deletion set D, not the retained set B. Output each deleted integer exactly once. Every output integer must occur in A. No other compression or ranges are allowed.

|A| = 63
Required |D| = 12
Resulting |B| = 51
A = 52502, 53152, 27901, 54524, 54482, 60494, 58488, 53182, 58478, 53816, 55162, 54572, 49882, 65890, 33285, 59860, 31251, 49858, 61828, 49210, 61840, 51848, 56612, 66572, 53812, 22645, 53222, 65894, 57802, 53200, 29905, 25915, 50532, 57206, 63872, 59818, 60486, 25257, 51832, 53168, 57886, 23947, 59828, 28567, 26575, 24601, 55900, 64536, 29235, 47242, 31927, 56480, 27237, 33967, 57152, 23295, 32605, 30577, 59140, 55930, 57184, 51172, 57914

Give your final answer inside <answer></answer> tags, as a comma-separated list of base-10 integers.
Example syntax: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

Answer:

```text
<answer>22645, 23947, 24601, 25915, 26575, 27237, 27901, 29235, 29905, 31251, 31927, 32605</answer>
```

`verify(inst, answer)` returns `(True, "ok")`. Dropping the last entry returns `(False, "wrong_length")`.

## Difficulty presets

| Preset | Variables `n` | Occurrences/sign | Graph vertices | `|A|` | `|D|` | Retained `|B|` | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 3 | 3 | 18 | 63 | 12 | 51 | Readable example; oracle solved 3/3 |
| easy | 50 | 9 | 900 | 5,850 | 600 | 5,250 | **Shipping; hardened** |
| medium | 65 | 9 | 1,170 | 7,605 | 780 | 6,825 | Available escalation |
| hard | 80 | 9 | 1,440 | 9,360 | 960 | 8,400 | Available escalation |

An earlier `easy-v1` setting (`n=9`, occurrences `6`) was rejected even though one oracle run held: dynamic greedy solved 7/8 local seeds and 64 random restarts solved 4/8. It was replaced before the final transcript.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 planted verifies | pass | 16/16, four seeds for every preset |
| G2 corruption | pass | 5/5 rejected with five distinct reasons |
| G3 round-trip | pass | all 600 shipped witness integers recovered from prose/fence/tags |
| G4 structure-aware guess | pass | 0/200,000 hits; candidates already delete only graph-vertex labels |
| G5 sparse exact probe | pass | 28/376,740 valid (`7.432181345224824e-5`) on encoded `K7` |
| G6 outlier | pass | 0/8 seeds across six position/degree/triangle rankings |
| G6 greedy | pass | 0/8; best sizes 288-297 versus target 300 |
| G6 random restart | pass | 0/8 with 64 restarts/seed; best sizes 271-279 versus 300 |
| G7 scaling | pass | doubled from 900 to 1,800 graph vertices; `|A|` 5,850 to 11,700; plant verifies |
| G8 canonical key | pass | 80/80 invariance and carried-witness checks; 20/20 unrelated keys distinct |

The naive shipped candidate count and structure-aware count are recorded exactly in `selftest_report.json`; both are huge, but only the structure-aware 0/200,000 experiment is used for G4.

## Oracle hardening loop

Effort was `medium`; the final deciders at the shipping rung were OpenAI, Anthropic, and Google. Error rows are retained but do not count as failures.

| Preset | Seed | Model | Outcome | Why |
|---|---:|---|---|---|
| demo | 1566796349 | Claude Sonnet 5 | solved | valid 12-element deletion set |
| demo | 1609712736 | GPT-5.6 Terra | solved | valid 12-element deletion set |
| demo | 1865114471 | Grok 4.6 | solved | valid 12-element deletion set |
| easy | 667661860 | Grok 4.6 | error | hard 900-second deadline; excluded |
| easy | 1929392340 | GPT-5.6 Terra | error | hard 900-second deadline; excluded |
| easy | 1885707135 | GPT-5.6 Terra | failed | parsed 583 integers; required 600 |
| easy | 1540752306 | Claude Sonnet 5 | failed | length-limited empty response after 32,000 completion tokens |
| easy | 1905125711 | Gemini 3.1 Pro Preview | failed | length-limited, truncated inside an unclosed answer tag |

Verdict: `hardened`, one escalation, shipping parameters `{"n": 50, "occurrences": 9}`. See `llm_loop_transcript.jsonl` and `.meta.json` for the complete machine-owned records.

## How to use it

```python
import random
import gen_2502_08624 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=12345, **params)
prompt = gen.render(inst)
candidate = gen.parse_answer(model_output)
ok, reason = gen.verify(inst, candidate)
fallback_guess = gen.random_candidate(inst, random.Random(7))
```

From the repository root, emit verified samples with:

```bash
bash scripts/emit.sh 2502.08624 20 easy
```

Run the local gates with `python3 results/2502.08624/gen_2502_08624.py`.

## Caveats

- The NP-completeness theorem is worst-case. It does not prove the balanced planted formulas are average-case hard; the oracle and attacks are empirical evidence only.
- The zero-hit estimate is for a deliberately strong but specific prior: uniformly choose which 300 of 900 graph vertices remain, while keeping every structurally recognizable edge label. It does not model a SAT solver, and 200,000 zero-hit trials do not statistically prove a true probability below `1e-6`.
- Equal degrees, balanced signs, randomized positions, triangle rankings, greedy rules, and random-order restarts were tested. Spectral recovery, belief propagation, clause learning, integer programming, and sophisticated local search were not.
- The integer encoding exposes the underlying graph after computing all `x+y=z` relations. This is intentional—the hardness claim is the encoded independent-set search, not obscurity of the reduction.
- `canonical_key` is invariant under input reorder, nonzero global scaling, graph relabelling, and their tested compositions. Exact graph isomorphism is not attempted; the key uses common-neighbour histograms and per-vertex local signatures, so rare non-isomorphic collisions are possible.
- Bedert's constant `c` is not made explicit, and these instances operate far above the paper's extremal one-third frontier. The paper supplies the exact sum-free object and the easy baseline; the computational regime comes from the cited complexity reduction.
