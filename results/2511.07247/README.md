# arXiv 2511.07247 — constrained voltage-lift witnesses

Status: the generator and every local gate pass, but the mandatory external oracle evidence is **not complete**. The supplied OpenRouter key returned HTTP 403 `Key limit exceeded` for both configured vendors before a single response could be scored. The three transcript files are genuine `harden.py` outputs recording that infrastructure failure; they are not hardness evidence. Do not submit this family until those three runs are repeated with a usable key.

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT (finite per-edge choices with modular constraints) |
| Certificate | 12×2 matrix over `C_45 × C_n` |
| Intuition | invariant: switching fixes loop voltages; an invertible loop exposes the automorphism, and corrected non-loop differences form a coboundary |
| Domain essentiality | native |
| Reduction | none |

## The problem and why the certificate is trustworthy

The source is Exoo, Goedgebeur, Jooken, Stubbe, and Van den Eede, [*New small regular graphs of given girth: the cage problem and beyond*](https://arxiv.org/abs/2511.07247). Figure 4(d) gives a six-vertex voltage graph over `C_45` whose 270-vertex lift is 4-regular with girth 9. An instance displays that reference assignment and, for each of its twelve directed edge roles, a short list of allowed voltages over `C_45 × C_n`. The solver must choose a 12×2 matrix that is one common componentwise group automorphism and one vertex switching of the reference.

Generation is inverse, never search: the module samples the automorphism and switching first, computes the answer, and mixes every row with same-marginal decoys. Projection to the paper's `C_45` lift rules out short cycles, while `(1,0)` and `(28,1)` generate the product group. `verify` does not read `inst["answer"]`; it checks list membership, reconstructs the common automorphism and switching potentials, checks connectivity by exact gcds, and enumerates all 515 closed non-reversing-walk coefficient constraints of lengths below 9. An independent expansion of three demo lifts confirmed 1,890 vertices, degree 4, connectedness, and girth exactly 9.

## Why Track B

This is explicitly not a complexity-hardness claim. Sections 3.2 and 3.4.1 give canonical pruning and exhaustive BTA, and Table 3 shows that the paper's full pruning stack reduces a smaller lift search from 16,460.9 seconds to 0.5 seconds. A mechanical algorithm exists here too: enumerate the `24 φ(n)` componentwise automorphisms, reject them with the four invariant loops, then intersect switching differences. Its regime at the shipping value `n=50021` contains 1,200,480 automorphisms; on seed 314159 the implementation used 636,344 primitive probes and 0.069 seconds. Across eight attack-panel seeds it used 10,258,080 probes in 1.097 seconds and solved 8/8, as expected.

The no-tool route is shorter: a candidate on the loop with reference voltage `[28,1]` determines both multipliers because both coordinates are units. The other loops test that choice, and subtracting the transformed reference from each non-loop list exposes one common switching difference. Seed 314159 took 127 exact group/set operations (the family bound is below 190). This gap—not computational intractability—is the Track B claim.

## Worked demo

For `make_instance(n=7, width=2, seed=23)`, the complete data table is:

```text
role  dart   reference    allowed voltages
 0    0->1    [0,0]        [19,3] [1,4]
 1    0->2    [0,0]        [1,4] [33,2]
 2    0->3    [0,0]        [12,2] [1,4]
 3    0->4    [0,0]        [0,1] [1,4]
 4    1->5    [0,0]        [1,4] [1,0]
 5    4->5    [1,0]        [31,3] [18,4]
 6    3->3    [42,2]       [42,5] [39,2]
 7    2->2    [28,1]       [26,1] [31,1]
 8    1->1    [5,3]        [40,3] [10,1]
 9    4->4    [38,4]       [16,4] [28,1]
10    2->5    [9,5]        [23,4] [19,2]
11    3->5    [24,6]       [36,2] [4,3]
```

The answer is `[[1,4],[1,4],[1,4],[1,4],[1,4],[18,4],[39,2],[26,1],[40,3],[16,4],[19,2],[4,3]]`. `verify(inst, answer)` returns `(True, "ok")`; dropping the last row returns `(False, "wrong row count: expected 12")`. A person can solve this demo on paper: `[26,1]` at the anchor induces the only multipliers consistent with all four loops, and `[1,4]` is the common corrected difference on the non-loop rows.

## Difficulty presets

| preset | `n` | choices/row | lift order | bounded answer space | status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 2 | 1,890 | 4,096 | exact enumeration: one answer |
| easy | 1,009 | 6 | 272,430 | 2,176,782,336 | oracle unavailable |
| medium | 10,009 | 8 | 2,702,430 | 68,719,476,736 | not reached |
| hard | 50,021 | 10 | 13,505,670 | 1,000,000,000,000 | intended shipping preset; oracle pending |

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify; all JSON-native |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and Markdown fences; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses at hard; candidates sampled uniformly from the exact per-row lists |
| G5 | pass | hard density sample 0/200,000; demo exact count 1/4,096; reference scan 636,344 probes, 0.069 s |
| G6 | pass locally | five attacks × 8 seeds: 0 successes each; reference algorithm 8/8 as expected |
| G7 | pass | doubled `n` builds a verified 27,011,340-vertex virtual lift with the same 24-atom answer |
| G8 | pass | 20/20 composed invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 123 characters, about 31 tokens, 24 atoms, 127 intended-route operations on the measured hard instance |
| STEP 4 / G9 arms | **blocked** | OpenRouter returned HTTP 403 before any scored oracle attempt |

The generic failing attacks were lexicographic outlier selection, template-nearest greedy selection, a zero-switch ansatz, raw-coordinate frequency, and 256 uniform random restarts. The successful scan is correctly outside `attacks` under Track B.

## Oracle and G9 diagnostics

| run | requested preset | scored solved/attempts | outcome |
|---|---|---:|---|
| bare | easy | 0/0 | four API retries, all HTTP 403; no verdict |
| structural hint | hard | 0/0 | four API retries, all HTTP 403; no verdict |
| placebo hint | hard | 0/0 | four API retries, all HTTP 403; no verdict |

`hinted − placebo` is therefore undefined, not zero, and no conclusion about hint sensitivity is warranted. The transcript rows deliberately retain `solved: "error"`. Re-run each arm with a funded OpenRouter key; never reinterpret these errors as model failures.

## Use

```python
import gen_2511_07247 as g

inst = g.make_instance(n=50021, width=10, seed=123)
question = g.render(inst)
candidate = g.parse_answer(model_reply)
ok, reason = g.verify(inst, candidate)
```

After successful oracle reruns, emit from the repository root with:

```bash
scripts/emit.sh 2511.07247 20 hard
```

## Caveats

This benchmark tests recovery of a hidden symmetry of a known voltage construction; it does not ask for a new cage, certify extremality, or claim Track A hardness. A solver that notices the invariant can and should solve it quickly, and ordinary code solves it in well under a second. The `0/200,000` density estimate is with respect to uniform independent choices from the displayed allowed lists; it is not a proof that the shipping instance has a unique answer (only the demo was exhaustively counted), nor does it describe a solver with a correlated symmetry prior.

The paper's full BTA, tabu search, GAP group machinery, SAT/SMT encodings, and a general graph-isomorphism attack were not reimplemented. The exact reference scan is tailored to the generated componentwise automorphism family. Canonicalization covers vertex relabelling, input/list reordering, non-loop dart reversal, componentwise automorphism, arbitrary switching, and their composition; it does not attempt arbitrary isomorphism of voltage bases that also permutes the semantic role IDs. Finally, the mandatory multi-vendor hardening evidence remains missing because of the external quota failure, so this directory is a verified build awaiting oracle evaluation—not a shippable result yet.
