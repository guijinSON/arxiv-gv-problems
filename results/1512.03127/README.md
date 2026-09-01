# Positive 1-in-3 witnesses from a hidden cubic edge-colouring

This generator turns Marcel Jackson's [*Flexible constraint satisfiability and a problem in semigroup theory*](https://arxiv.org/abs/1512.03127) into a witness problem.  The solver sees Boolean variables divided into three-variable choice groups plus additional three-variable check clauses.  It must select exactly one variable from every group and every clause.  A checker simply substitutes the selected set and counts to one in each triple, so it accepts any satisfying assignment, not only the plant.

Generation samples the answer first: three independent uniform perfect matchings are a 3-edge-colouring of a cubic graph.  The graph is accepted only when it is simple, connected, non-bipartite, and has girth at least five.  Its line graph has every edge in exactly one triangle.  Section 6's A2/B2 construction then creates one choice clause per line-graph vertex and one check clause per triangle and colour.  All SAT variables occur once in a choice group and twice in checks, and all names and input rows are shuffled.

## Why the regime is hard

Section 1 fixes positive 1-in-3SAT as the relation `{(1,0,0),(0,1,0),(0,0,1)}`.  Section 5, Theorem 5.1 proves NP-completeness of robust 3-colourability even when every graph edge lies in exactly one triangle.  Section 6, Theorems 6.1–6.2 transfers that regime to positive 1-in-3SAT and proves the relevant NP-hard gap.  On this generator's line graphs, a satisfying assignment is exactly a 3-edge-colouring of the hidden cubic graph.  Cubic 3-edge-colourability is NP-complete by [Holyer (1981)](https://doi.org/10.1137/0210055), and [Kamiński–Lozin (2007), Theorem 2.1](https://doi.org/10.55016/ojs/cdm.v2i1.61890) proves NP-hardness even for cubic graphs of any fixed minimum girth, covering the girth-five filter used here.

The paper also identifies what does *not* create hardness.  Section 3, Proposition 3.2 reduces fixed-level robustness to the underlying CSP with constants; the following example notes that robust 2-colouring stays in logspace.  The generator therefore asks for ordinary positive 1-in-3 satisfaction, not a robustness certificate.  It rejects disconnected and bipartite cubic graphs (the latter have polynomial-time edge-colouring), and girth below five, which would add short alternating-cycle structure and invalidate the exact Section 6 triangle correspondence.

## Worked `easy` example

This is the complete output of `make_instance(n=12, min_girth=5, seed=0)`:

```text
Positive 1-in-3 Boolean witness problem

There are 54 Boolean variables numbered 0 through
53 inclusive.  Your answer is the set of variables
assigned TRUE; every variable not listed is assigned FALSE.

A triple is satisfied when exactly one of its three distinct variable numbers
is TRUE.  "Exactly one" means one, not zero and not two or three.  The choice
groups below partition all variables.  Select exactly one variable from every
choice group, and also make every check clause contain exactly one selected
variable.

CHOICE GROUPS (18 triples)
G0: 47 46 0
G1: 13 5 27
G2: 17 36 49
G3: 18 15 43
G4: 45 34 50
G5: 44 30 39
G6: 16 22 4
G7: 32 7 37
G8: 25 42 26
G9: 28 14 40
G10: 6 29 52
G11: 31 8 2
G12: 12 33 11
G13: 20 19 53
G14: 35 24 21
G15: 23 41 1
G16: 10 38 9
G17: 51 3 48

CHECK CLAUSES (36 triples)
C0: 8 20 30
C1: 49 39 21
C2: 3 8 5
C3: 25 23 53
C4: 25 15 9
C5: 36 35 44
C6: 14 6 34
C7: 44 31 53
C8: 27 22 37
C9: 45 29 40
C10: 47 45 51
C11: 16 12 36
C12: 52 24 38
C13: 18 0 33
C14: 28 41 32
C15: 42 1 19
C16: 9 29 35
C17: 47 12 15
C18: 14 37 1
C19: 17 33 4
C20: 43 10 42
C21: 19 2 39
C22: 30 24 17
C23: 18 38 26
C24: 41 20 26
C25: 22 49 11
C26: 6 10 21
C27: 50 28 52
C28: 0 50 3
C29: 31 13 51
C30: 11 43 46
C31: 40 23 7
C32: 48 34 46
C33: 32 4 5
C34: 2 27 48
C35: 16 13 7

Return exactly 18 distinct integers.  Variable numbering is
0-based, order does not matter, and repeated numbers are forbidden.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly 18 variable numbers.
Example syntax: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

The planted output is `<answer>1, 6, 8, 9, 13, 22, 24, 26, 32, 33, 36, 39, 40, 43, 47, 48, 50, 53</answer>`.  `verify(inst, inst["answer"])` returns `(True, "ok")`.  Dropping the final `53` returns `(False, "wrong number of selected variables: expected 18")`.

## Difficulty presets

| Preset | Cubic vertices `n` | SAT variables | Choice groups | Check clauses | Status |
|---|---:|---:|---:|---:|---|
| `easy` | 12 | 54 | 18 | 36 | Oracle solved 3/3; demo only |
| `medium` | 200 | 900 | 300 | 600 | **Ships; all 3 deciding vendors failed** |
| `hard` | 280 | 1,260 | 420 | 840 | Available, not needed |
| `extreme` | 360 | 1,620 | 540 | 1,080 | Available, not needed |

`escalate()` adds 80 cubic vertices.  The original `n=76` draft is not retained as a preset: its min-conflicts attack solved 8/8 seeds, which is why the shipping floor moved to `n=200` before the oracle run.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 plants verified: 4 presets × 3 seeds |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | Tagged answer round-tripped through prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; prior is one uniform choice per public group; space is `3^300 ≈ 1.369e143` |
| G5 | Exact control: 18/531,441 answers valid, fraction `3.3870e-5`; shipping enumeration capped to `None` |
| G6 | Degree/frequency outlier 0/8; left-to-right greedy 0/8; 16-restart min-conflicts 0/8 |
| G7 | Doubled `n=400` builds, plant verifies, witness length doubles 300→600, and search space squares |
| G8 | 80/80 key invariance checks and 80/80 carried witnesses; 20/20 unrelated keys distinct |

## Oracle hardening loop

Every response parsed.  There were no API errors or empty responses.  Full replies, timings, and finish reasons are in `llm_loop_transcript.jsonl`.

| Preset | Model | Seed | Result | Checker reason |
|---|---|---:|---|---|
| `easy` | `google/gemini-3.1-pro-preview` | 1596361348 | solved | `ok` |
| `easy` | `x-ai/grok-4.6` | 1575089792 | solved | `ok` |
| `easy` | `anthropic/claude-sonnet-5` | 1492337226 | solved | `ok` |
| `medium` | `google/gemini-3.1-pro-preview` | 1144525471 | failed | check clause 3 violated |
| `medium` | `openai/gpt-5.6-terra` | 1217290052 | failed | check clause 0 violated |
| `medium` | `anthropic/claude-sonnet-5` | 663777776 | failed | wrong length; expected 300 |

Verdict: `hardened`, one escalation, shipping preset `medium`.

## Use

```python
import gen_1512_03127 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(**params, seed=123)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 1512.03127 20 medium
```

## Caveats

- The cited theorems are worst-case hardness results.  They do not prove average-case hardness for this planted random distribution; the attack panel and four-vendor loop are empirical evidence only.
- `0/200,000` is the observed rate under the exact one-choice-per-group prior.  It is not a proof that the true probability is below `1e-6` and says nothing about SAT, ILP, perfect-matching, spectral, or algebraic algorithms.
- The restart panel used 16 independent starts and at most 10 moves per choice group.  It did not test tabu search, simulated annealing, a blossom-based perfect-matching search, industrial SAT solvers, or exhaustive alternating-cycle repair.
- Generated instances are satisfiable but are not certified `<=2`-robust.  Robustness is the paper's hardness vehicle; the witness requested here is ordinary positive 1-in-3 satisfaction because it is cheap to verify.
- Multiple witnesses can exist.  `verify` accepts all of them; no uniqueness or optimality claim is made.
- Exact graph isomorphism is not known to have a simple cheap canonical form.  `canonical_key` uses the reconstructed cubic graph's distance profiles and root-individualised colour refinement.  It passed all required invariance/diversity tests, but adversarial non-isomorphic graphs could collide.
