# Forced Model RB witness generator (arXiv:2103.06649)

Status: the generator and all local gates pass, but this result is **not yet submission-ready**. The required oracle runs were attempted with `scripts/harden.py`; every request received OpenRouter HTTP 403 (`Key limit exceeded`), so there is no STEP 4 hardness verdict and the three G9 arms remain unmeasured.

## Profile

| field | value |
|---|---|
| track | **A** — structural hardness |
| native domain | logic |
| object regime | finite discrete |
| computational core | CSP/SAT |
| certificate | integer tuple: one complete assignment |
| native objects | growing-domain variables, ordered binary scopes, permitted tuple relations |
| intuition | constraint propagation: local value frequencies hide the plant; consistency is global |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

The family implements the native Model RB construction in Section 2 of Guangyan Zhou, [“Hiding solutions in model RB: Forced instances are almost as hard as unforced ones”](https://arxiv.org/abs/2103.06649). A solver receives variables with a common finite domain and random ordered binary constraints. Each constraint relation is shown exactly as a hexadecimal row-major bit mask. The solver must return one value per variable satisfying every relation.

Generation is inverse: an assignment is sampled first, and each relation is then sampled uniformly conditional on containing the assignment's induced tuple, exactly as in Section 2. `verify` never reads `inst["answer"]`; it checks ranges and all relation memberships. Thus the witness is known without solving the generated CSP and any satisfying assignment is accepted.

The Track A basis is the paper's Section 2/Theorem 4, which transfers algorithmic success between one-forced and unforced Model RB for fixed parameters, together with the paper's cited exponential lower bounds near the threshold. Shipping uses `k=2`, `alpha=3/5`, `p=1/2`, and `r=21/25=0.84`, satisfying `alpha>1/k`, `k>=1/(1-p)`, and `r<r_c=3/(5 ln 2)≈0.8656`. We avoid the many-solution region far below the threshold and the unforced-unsatisfiable region above it. The paper gives no polynomial algorithm producing the certificate.

## Worked demo

The `demo` preset with seed 3 renders in full as:

```text
Find a satisfying assignment for this forced Model RB binary constraint satisfaction problem.

There are n=4 variables x_0,...,x_3. Each variable takes one integer value in 0,...,1.
Repeated values are allowed. Variable indices and the output order are 0-based.
Each constraint lists an ordered scope [i,j] and a hexadecimal permitted-tuple mask.
Decode a candidate tuple (a,b) by q=a*2+b. It is permitted exactly when bit q of the mask is 1,
where bit 0 is the least significant (rightmost) bit. Leading hexadecimal zeroes carry no special meaning.
An assignment is satisfying only if its induced ordered tuple is permitted by every listed constraint.

The 4 constraints are:
C0: [0,2] 0x3
C1: [3,1] 0xc
C2: [1,0] 0x9
C3: [3,2] 0xc

Give your final answer inside <answer></answer> tags as one JSON array of exactly n integers.
Example of the required shape only: <answer>[0,0,0,0]</answer>
Output nothing else inside the tags.
```

`<answer>[0,0,1,1]</answer>` gives `verify(...) == (True, "ok")`. Dropping its last entry gives `(False, "answer length 3 != 4")`. This demo has exactly two satisfying assignments and is genuinely hand-solvable by decoding four 4-bit relations.

## Difficulty presets

| preset | n | r | d at preset | constraints at seed 0 | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 0.800 | 2 | 4 | hand example; never ships |
| easy | 100 | 0.840 | 16 | 387 | provisional shipping preset; all local attacks fail |
| medium | 120 | 0.845 | 18 | 485 | reserve escalation |
| hard | 140 | 0.850 | 19 | 588 | reserve escalation |

The earlier `n=59` candidate was rejected locally because MAC solved it in hundreds of branches. The attack-resistant `n=100` setting was deliberately moved to `easy`, ensuring that the no-tool loop cannot stop on a preset already broken by the standard algorithm.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; all answers JSON-round-trip |
| G2 | 5/5 corruption classes rejected with 5 distinct reasons |
| G3 | model-style prose and renderer example both parse |
| G4 | 0 hits / 200,000 structure-aware uniform assignments; 29.870161 s |
| G5 | shipping density 0/200,000 sampled; MAC exhausted 5,000 nodes in 12.168470 s; demo exact count 2 |
| G6 | outlier 0/8; greedy 0/8; min-conflicts 0/8 after 76,800 iterations; MAC 0/8 after 40,000 nodes and 135.045724 s |
| G7 | doubled `n=200` instance built in 0.243760 s and verified |
| G8 | 20/20 composed relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 338 characters, about 85 tokens, 100 atoms, 100 post-search recording operations; all within caps |

## Oracle loop and G9 diagnostics

The bare harness made four redraw attempts at `easy`; none counts as a model attempt because all were API errors.

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | x-ai/grok-4.6 | 833662359 | error | HTTP 403 key total limit |
| easy | anthropic/claude-sonnet-5 | 788080175 | error | HTTP 403 key total limit |
| easy | anthropic/claude-sonnet-5 | 1133115782 | error | HTTP 403 key total limit |
| easy | x-ai/grok-4.6 | 1176298256 | error | HTTP 403 key total limit |

| G9 arm | solved/attempts | conclusion |
|---|---:|---|
| bare | 0/0 | unavailable; only API errors |
| structural hint | 0/0 | unavailable; only API errors |
| placebo hint | 0/0 | unavailable; only API errors |

`hinted − placebo` is therefore undefined, not evidence that the hint has zero effect. The copied transcripts retain the script-owned error records so the infrastructure failure is auditable. Re-run all three arms after restoring OpenRouter capacity, then update `G9_ORACLE_RESULTS` and regenerate `selftest_report.json`.

## Use

```python
import importlib.util

path = "results/2103.06649/gen_2103_06649.py"
spec = importlib.util.spec_from_file_location("rb", path)
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

inst = rb.make_instance(seed=7, **rb.DIFFICULTY[rb.SHIPPING_DIFFICULTY])
statement = rb.render(inst)
candidate = rb.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert rb.verify(inst, candidate) == (True, "ok")
```

After a valid `harden.py` verdict, emit with `bash scripts/emit.sh 2103.06649 20` from the repository root.

## Caveats

- Theorem 4 is asymptotic and supplies no finite-size convergence rate; the `n=100` claim therefore rests materially on the measured panel, not theorem citation alone.
- Zero hits in 200,000 guesses is a sampled upper-bound signal, not proof of zero solution density. The sampler already enforces the complete stated answer grammar (length and domain); it does not condition on arc consistency, which would require running a solver.
- MAC is bounded at 5,000 branches. No industrial CP/SAT portfolio, belief propagation, or unbounded complete solver was run. Those are the most important missing attacks.
- The intended-operation count measures writing the 100 recovered values after the global consistency search; it does not pretend that the failed search itself takes 100 operations.
- `canonical_key` is exact for the tested invariant under constraint order, variable order, independent value renaming, and scope reversal, but it is a strong cheap invariant rather than a complete canonical form for binary-CSP isomorphism. Rare unrelated collisions can therefore occur.
- The named finite domains use an exact integer rounding convention asymptotic to `n^(3/5)`, and half-integral permitted-relation sizes round upward; these finite conventions are stated by `render` where they affect solving.
- Most importantly, STEP 4 and both non-bare G9 transcripts contain only infrastructure errors. This directory must not be submitted as hardened until those script-owned runs succeed.
