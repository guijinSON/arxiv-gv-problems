# 1408.5958 — bounded nonnegative integer equations

| profile field | value |
|---|---|
| Track | **B** — no-tool compression; an efficient exact algorithm exists |
| Native domain | `optimization` |
| Object regime | `integer_lattice` |
| Computational core | `linear_algebra` |
| Certificate form | `integer_tuple` |
| Intended intuition | `decomposition`: expose a permuted scalar-diagonal-plus-rank-one matrix |
| Domain essentiality | `native` |
| Reduction | none |

## Problem and construction

The source is Enea, Habermehl, Inverso, and Parlato, [*On the Path-Width of Integer Linear Programming*](https://arxiv.org/abs/1408.5958). Section 2 defines an ILP instance in standard form as integer equations `A x = b` with a nonnegative integer solution. The solver receives exactly those native objects—a square integer matrix, an integer right-hand side, and an inclusive coordinate bound—and must return any bounded nonnegative integer solution. `verify` checks the shape, bounds, and every matrix-vector equality using Python integers only.

Generation is inverse, not a hidden solve. It samples the answer `x` first, forms `A = qI + r u v^T` before independently permuting rows and columns, and computes `b = A x`. Here `u,v` are sign vectors and `q=(n+1)r+1`. Since `|v^T u| <= n`, the matrix determinant lemma gives `det(A)=q^(n-1)(q+r v^T u)>0`; therefore the planted vector is the unique rational solution and hence the unique answer in the bounded integer language. Proposition 1 in Section 3 confirms that these nonnegative assignments are exactly the vectors encoded by the paper's solution graphs; Lemma 1 and Theorem 2 provide the bounded-path-width representation, but the generator does not replace the native equations by a graph.

## Why Track B

This distribution is not Track A. A specialist can run dense exact Gaussian elimination in `O(n^3)` and solve every generated instance. At the shipping preset, the measured reference run solved 8/8 instances in 0.061966 seconds total, averaging 13,843 exact rational operations per instance. The paper itself lists branch-and-bound, cutting planes, LLL, the Omega test, and automata methods in Section 1; Section 5 builds the automaton/Boolean-program route, and Section 6 says that route gives a PSPACE procedure even though general ILP feasibility is NP-complete.

The compression insight is that each row has one exceptional coefficient and those positions form a row-column matching. After alignment, the matrix is a scalar diagonal matrix plus a rank-one sign matrix. A Sherman–Morrison calculation then recovers the 48 coordinates in at most `6n+4 = 292` exact operations. Without that decomposition, the displayed dense system calls for the 13,843-operation elimination route. Lower-bit rungs were solved by the oracle pool; 56-bit arithmetic at the same 48-element answer length is the first bare rung that held.

## Worked demo

The `demo` preset with seed 0 renders the following hand-scale system:

```text
Bounded nonnegative integer equations

An integer assignment is a vector x=(x_0,...,x_3) of exactly 4 integers.
Find any assignment satisfying every equation A x = b, where multiplication and
addition are over the ordinary integers.  Every coordinate must lie in the
inclusive interval 0 <= x_j <= 15.  Variable and column indices
are 0-based, the output order is x_0 through x_3, and repeats are allowed.

Each line below is one equation.  Before the vertical bar are its 4
coefficients in x_0,...,x_3 order; after the bar is its right-hand side.

0: 1 1 -1 5 | 92
1: 1 7 -1 -1 | 86
2: -1 -1 7 1 | 46
3: 5 -1 1 1 | 64

Give your final answer inside <answer></answer> tags as one JSON list of exactly
4 decimal integers in variable order.
Example format: <answer>[3, 17, 42]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[11, 14, 8, 15]</answer>`. `verify(inst, [11,14,8,15])` returns `(True, "ok")`. Changing the first entry to 12 returns `(False, "equation 0 fails: left side 93, right side 92")`. A person can solve this demo by ordinary elimination on paper.

## Difficulty presets

| preset | n | value bits | coupling bits | status |
|---|---:|---:|---:|---|
| demo | 4 | 4 | 1 | hand-solvable illustration |
| easy | 48 | 20 | 7 | a 20-bit instance was solved by Grok in the final bare ladder |
| medium | 48 | 44 | 7 | a 44-bit instance was solved by Grok in the final bare ladder |
| hard | 48 | 56 | 7 | **ships**; bare and structurally hinted panels both held |

The final named ladder was slid upward after `harden.py` found the holding 56-bit level through `escalate()`. The answer stays at 48 atoms while numeric entropy grows.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | planted answer verified on 12 preset/seed pairs |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered from prose and verified |
| G4 | pass | 0 hits / 200,000 structure-aware bounded-vector samples |
| G5 | pass | exactly 1 shipping solution; log10 density `-809.1686`; reference 110,744 operations over 8 solves |
| G6 | pass | four in-context attacks each scored 0/8; exact Gaussian reference scored 8/8 |
| G7 | pass | candidate languages strictly grow; a doubled `n=96` instance builds and verifies |
| G8 | pass | 60 key-invariance checks, 60 carried-witness checks, and 20/20 unrelated keys distinct |
| G9 | pass | hint verdict `hardened`; 865 chars, 217 estimated tokens, 48 atoms, 292 intended operations |

The four failing attacks were right-hand-side magnitude ranking, exceptional-coefficient diagonal rounding, 256 local random restarts, and a centered-residue lift. The successful dense exact elimination is reported separately, as Track B requires.

## Bare oracle loop

These are the script-owned calls in `llm_loop_transcript.jsonl`. API errors did not consume an attempt. The first 32-variable calibration level was later dropped when the ladder was slid.

| params | model | seed | outcome | reason |
|---|---|---:|---|---|
| n=32, bits=18 | Gemini | 23439615 | failed | wrong equation value |
| n=32, bits=18 | Claude | 1915330162 | solved | verified witness |
| n=32, bits=18 | OpenAI | 671152021 | solved | verified witness |
| n=48, bits=20 | Claude | 512680685 | failed | empty length-limited response |
| n=48, bits=20 | Grok | 720030391 | solved | verified witness |
| n=48, bits=20 | OpenAI | 756977522 | failed | coordinate outside the bound |
| n=48, bits=44 | Claude | 811569395 | failed | empty length-limited response |
| n=48, bits=44 | OpenAI | 2005635993 | failed | zero vector fails an equation |
| n=48, bits=44 | Grok | 485040181 | solved | verified witness |
| n=48, bits=56 | Grok | 377418096 | error | 900-second deadline; redrawn |
| n=48, bits=56 | Grok | 1431822647 | error | incomplete HTTP response; redrawn |
| n=48, bits=56 | OpenAI | 900460075 | failed | malformed tagged vector (`?`) |
| n=48, bits=56 | Gemini | 958329179 | failed | response truncated before closing tag |
| n=48, bits=56 | Claude | 863646402 | failed | empty length-limited response |

## G9 arms

| arm | solved / valid attempts | errors | conclusion |
|---|---:|---:|---|
| bare | 0/3 | 2 | hardened; errors were redrawn |
| structural hint | 0/3 | 0 | hardened |
| placebo hint | 0/2 | 4 | incomplete diagnostic; third slot exhausted the key limit |

The measured hinted-minus-placebo rate is `0.0`, but the placebo denominator is only two. The structural hint bought no observed improvement at 56 bits; this suggests the final failures are dominated by exact arithmetic execution rather than failure to recognize the decomposition. The third placebo slot was attempted, but every one of the four script-mandated redraws returned HTTP 403 after the OpenRouter key reached its total limit. This arm is recorded, never gated; the completed 0/3 structural arm is the G9(b) gate.

## Use

```python
import random
import gen_1408_5958 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 2 ** (56 * 48)
_ = g.random_candidate(inst, random.Random(1))
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 1408.5958 20
```

The module is standard-library-only and performs no file or network I/O on import.

## Caveats

- This is deliberately Track B. Exact Gaussian elimination solves the shipping distribution in milliseconds; the family must never be cited as average-case ILP hardness or as evidence for Track A.
- The structural signature is conspicuous, and the compact route is 292 operations—just under the 300-operation cap. At 865 answer characters, the benchmark may measure large-integer accuracy and transcription discipline as much as decomposition insight.
- Two of three decisive bare failures and two of three decisive hinted failures involved the 32,000-token reasoning/output ceiling. Raising `ORACLE_MAX_TOKENS` could change the verdict and should be tested when budget permits.
- G4 samples uniformly from the exact stated bounded-vector language. Its 0/200,000 result and exact `2^-2688` density measure guessing, not algorithmic difficulty; a solver using the matrix structure has a radically better prior.
- The adversary panel did not run branch-and-cut, LLL, the paper's automaton, or an external ILP package. Dense exact Gaussian elimination is already decisive for this nonsingular square subclass, so those omissions do not support a stronger claim.
- `canonical_key` handles all generator-preserving equation reorderings and variable relabellings tested, plus the sign-factor ambiguity of the recovered rank-one form. It does not canonicalize arbitrary unimodular row operations or equation rescaling.
- The placebo arm is incomplete at 0/2 because the external key limit prevented a third valid call. The transcript preserves all four rejected API attempts rather than converting them into false model failures.
