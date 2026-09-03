# Base-encoded exact-cover Diophantine equations

This generator turns the nonnegative linear equation studied in Eteri Samsonadze, [“Sufficient conditions for solvability of linear Diophantine equations, and Frobenius numbers”](https://arxiv.org/abs/2408.17266), into a witness-search problem. A solver receives one equation `sum(a_i*x_i)=b`, represented exactly by base-`B` support triples, and returns the indices whose variables equal 1. The checker reconstructs the exact integer coefficients and substitutes the candidate. There is no numerical tolerance and any valid solution is accepted.

## Construction and hardness

Section 2, equation (2.1), fixes the paper's object: all `x_i` are nonnegative integers. For `U=3q` and `B=q+1`, a triple `(u,v,w)` has raw coefficient

```text
A_i = B^U + B^u + B^v + B^w.
```

The raw target is `q*B^U + sum(B^j, j=0..U-1)`; all coefficients and the target are divided by their common gcd. Since the target is below `B^(U+1)`, any solution has `sum(x_i)<=q`. No lower digit can then carry in base `B`, so the high digit forces `sum(x_i)=q` and every lower digit forces exactly one selected triple to contain its element. Thus every nonnegative solution is exactly an Exact Cover by 3-Sets (X3C) witness. X3C is NP-complete; see the exact-cover lineage in [Karp (1972)](https://doi.org/10.1007/978-1-4684-2001-2_9) and the explicit restricted problem in [Monien and Sudborough (1981)](https://doi.org/10.1145/800076.802474). The encoding has polynomial bit length, while verification is one exact integer sum.

The target paper does **not** prove a complexity-hardness theorem, so the hardness claim here comes from this X3C encoding plus the measured gates and oracle loop—not from a theorem in the paper. The paper does identify regimes to avoid. Theorem 2.1 and Proposition 2.2 make sufficiently large targets automatically solvable; Proposition 2.5 supplies a two-variable solution when a suitable coprime pair is small relative to `b`; Proposition 2.22 directly reduces the range `b < 2*min(a_i)` to subset-sum membership. Generated targets are about `q` coefficient units, far below coefficient products and above the Proposition 2.22 range. Theorem 2.21's recurrence still requires constructing the combinatorial subset-sum set `T`.

Generation samples one uniformly random partition first, then adds independent random partition layers and shuffles every triple. Duplicate triples cause the entire draw to be retried. Conditioning is symmetric across layers: every triple has the same marginal distribution, every ground element has the same degree, and all layers are valid answers. The stored first layer is only one accepted witness.

## Worked example

This is the complete `example` instance from `make_instance(n=4, layers=2, seed=0)`:

```text
Find a nonnegative integer solution of one linear Diophantine equation.

Definitions and exact encoding.
There are m=8 variables x_1,...,x_8, indexed from 1.
Let q=4, B=5, and U=12. Ground-element labels are the integers 0 through 11.
Each variable i has a listed support triple (u,v,w) of three distinct ground elements.
Its raw coefficient is A_i = B^U + B^u + B^v + B^w. Let d=4.
The equation coefficient is the exact integer a_i=A_i/d.
The exact right-hand side is
    b = (q*B^U + sum(B^j for j=0,...,U-1))/d.
For this instance, b=259399414.
You must find nonnegative integers satisfying sum(a_i*x_i for i=1,...,m)=b.

The base encoding guarantees that every solution has exactly q entries equal to 1 and all other entries 0.
Therefore output exactly q distinct variable indices; omitted indices mean x_i=0 and listed indices mean x_i=1.
Order does not matter. Repeats are forbidden. Equivalently, the q listed support triples must cover every ground element exactly once.

Support triples, one per line in the parseable format `index: u v w`:
1: 2 4 8
2: 1 8 9
3: 0 3 5
4: 0 6 11
5: 3 4 7
6: 6 7 11
7: 1 9 10
8: 2 5 10

Give your final answer inside <answer></answer> tags, as exactly q comma-separated 1-indexed variable indices.
Example format: <answer>3, 17, 42, 58</answer>
Output nothing else inside the tags.
```

`<answer>2, 4, 5, 8</answer>` parses to `[2, 4, 5, 8]`, and `verify` returns `(True, "ok")`. Dropping the last index returns `(False, "wrong length: expected 4 indices, got 3")`.

## Difficulty

| Preset | `q=n` | Layers | Elements | Variables | Structure-aware candidate space | Status |
|---|---:|---:|---:|---:|---:|---|
| `example` | 4 | 2 | 12 | 8 | 70 | Readable example; oracle solved 3/3 |
| `hard` | 54 | 7 | 162 | 378 | 1.2403790563882879e66 | **Ships; hardened 0/3 solved** |

Two exploratory settings were removed from the ladder: `(n=18,layers=5)` fell to randomized greedy restarts on 8/8 seeds, and `(n=27,layers=6)` fell on 1/8. The earlier `(n=36,layers=7)` resisted those restarts but a standard bounded exact-cover backtracker found several lucky seeds quickly, so it was replaced by `n=54` before the final oracle run.

## Gate results

| Gate | Measurement | Result |
|---|---|---|
| G1 planted verifies | 5 seeds × 2 presets = 10/10 | pass |
| G2 corruptions | drop, replace, duplicate, empty, out-of-range: 5/5 rejected with 5 reasons | pass |
| G3 round trip | 54 indices recovered through prose and Markdown fencing | pass |
| G4 structure-aware guess | 0/200,000 uniform `q`-subsets; space `C(378,54)` | pass |
| G5 sparse | 6/134,596 on exact capped enumeration (`n=6,layers=4`) = 4.4578e-5 | pass |
| G6 attacks | smallest-coefficient, left-to-right, MRV greedy, 1,000 restarts, and 100,000-node exact search: each 0/8 | pass |
| G7 scaling | `n=108` builds and the plant verifies; candidate space increases | pass |
| G8 canonical key | 60/60 relabelling checks, 60 carried witnesses verified, 20/20 unrelated keys distinct | pass |

Exact details are in [`selftest_report.json`](selftest_report.json).

## Required oracle loop

The final run used reasoning effort `medium`. Error rows are retained but do not count toward the verdict.

| Preset | Model | Seed | Outcome | Why |
|---|---|---:|---|---|
| example | GPT-5.6 Terra | 210498842 | solved | valid witness |
| example | Claude Sonnet 5 | 223992451 | solved | valid witness |
| example | Gemini 3.1 Pro Preview | 1144492111 | solved | valid witness |
| hard | Grok 4.6 | 978409965 | error | 900 s hard deadline; redrawn |
| hard | Grok 4.6 | 146058958 | error | 900 s hard deadline; redrawn |
| hard | Gemini 3.1 Pro Preview | 912498930 | failed | parsed 54 indices; equation mismatch |
| hard | GPT-5.6 Terra | 1335875701 | failed | parsed 54 indices; equation mismatch |
| hard | Claude Sonnet 5 | 1059690047 | failed | exhausted 32k completion budget without an answer |

The script verdict was `hardened`, with shipping parameters `{"n":54,"layers":7}`. Full replies and timings are in [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl); run metadata are in `.meta.json`.

## Use

```python
import random
import gen_2408_17266 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer("<answer>1, 2, 3</answer>")
ok, reason = gen.verify(inst, candidate)
random_baseline = gen.random_candidate(inst, random.Random(9))
```

From the repository root, rerun the gates and emit instances with:

```bash
python3 results/2408.17266/gen_2408_17266.py
bash scripts/emit.sh 2408.17266 20 hard
```

## Caveats

- NP-completeness is worst-case evidence. There is no average-case hardness proof for this shuffled union-of-random-partitions distribution; the oracle and attack results are empirical.
- G4 samples uniformly from the fully structure-aware `q`-subset space. Its 0/200,000 result is not a confidence proof of a probability below `1e-6`, and says nothing about guided exact-cover, SAT, or ILP solvers.
- The bounded exact attack is one minimum-column branch ordering with a 100,000-node cap. An optimized Dancing Links implementation, SAT/ILP solver, alternative branching, message-passing attack, or much larger restart budget was not tested. The removed smaller settings demonstrate that parameter choice matters.
- Seven valid partition layers are planted, and accidental mixed covers may also exist. This is intentional because the checker must accept any witness, but it means solution uniqueness is neither claimed nor tested at shipping size.
- Exact hypergraph isomorphism/canonical labelling is nontrivial. `canonical_key` uses pair-codegree profiles plus eight invariant refinement rounds. It is proved invariant under variable reorder, arbitrary ground-set permutation, and their composition, but two non-isomorphic hypergraphs could still collide and be over-collapsed.
- One decisive oracle failure was completion-budget exhaustion, not a wrong witness. The other two returned parseable candidates that failed exact substitution. Grok's two timeouts were excluded from the decision.
