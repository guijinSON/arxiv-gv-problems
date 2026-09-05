# Vertex Separator Reconfiguration generator (arXiv:2004.10873)

> **Status:** all gated local checks pass, and the bare oracle loop hardened at
> `hard`. OpenRouter exhausted its account-wide key limit during the hinted and
> placebo diagnostics, so the hinted arm stopped after two completed attempts
> and the placebo arm has none. These arms are non-gating diagnostics.

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate form | polynomial |
| Intuition | invariant: the move codes are values of a low-degree permutation polynomial modulo a power of two |
| Domain essentiality | native |
| Reduction | none; the solver is handed the paper's peanut-like graph and separators |

## What the family is

The source is Gomes, Nogueira, and dos Santos, [*Some results on Vertex
Separator Reconfiguration*](https://arxiv.org/abs/2004.10873). Section 2 defines
an `s,t` separator and the token-jumping (TJ) rule. Section 4, Lemma 6 proves
that after adding one focus adjacent to each side of a bipartite graph, the
complement of every independent set is exactly an `s,t` separator.

An instance contains such a peanut-like bipartite graph, an initial separator,
and a target separator. Each task has vertices `L_x,R_x`. Moving the token
`R_x -> L_x` performs task `x`; non-focus edges impose precedences. The answer
is four coefficients `D,B,A,C`. The checker evaluates
`P(i)=D*i^3+B*i^2+A*i+C (mod q)` and replays the resulting `q` TJ moves. It
checks the coefficient language, permutation property, every token jump, every
separator by graph reachability, and the final endpoint. It never reads the
planted answer.

## Why Track B, and what makes the paper easy elsewhere

Theorem 8 and Corollary 9 make TJ separator reconfiguration NP-complete on
peanut-like bipartite graphs, but that is worst-case hardness and does **not**
justify a Track-A claim for this planted distribution. A direct algorithm for
these generated instances extracts the dependency DAG and applies Kahn
elimination, then interpolates the cubic. Its complexity is `O(|V|+|E|)` here;
over eight shipping instances it used 4,721 operations on average (4,826 max)
and 0.00059 seconds on average (0.00071 max). It solved 8/8, as expected.

The compact route recognizes the cubic invariant, obtains the first four
enabled moves, and uses finite differences/modular division to recover an
equivalent coefficient tuple in at most 47 exact arithmetic operations. This is
why the claim is Track B rather than Track A. Theorem 11 is explicitly
polynomial for tame classes via minimal-separator enumeration; Section 5,
Theorem 14 is also polynomial on `{3P1,diamond}`-free graphs, and Theorem 26
proves TJ always possible on series-parallel graphs. The generator avoids all
of those positive regimes.

## Worked demo

The `demo` preset is hand-scale. For seed 0 the full rendered instance is:

```text
VERTEX SEPARATOR RECONFIGURATION UNDER TOKEN JUMPING

A vertex separator for foci s and t is a set S of vertices, excluding
s and t, such that deleting S and all incident edges leaves no path
from s to t. A token-jump replaces exactly one member of S by exactly
one vertex outside S; every intermediate set must also be a separator
and therefore has the same cardinality.

This graph is bipartite and has 18 vertices, numbered 0 through 17.
The foci are s=7 and t=0.
The two bipartition classes are:
  A = 5 10 16 17 6 12 1 0 13
  B = 9 11 8 4 15 3 14 2 7

Each task code x names a pair (L_x,R_x). The rows are deliberately shuffled:
  code 3: L=5 R=15
  code 7: L=17 R=4
  code 6: L=1 R=3
  code 2: L=10 R=11
  code 1: L=16 R=9
  code 5: L=13 R=8
  code 0: L=12 R=2
  code 4: L=6 R=14

Undirected edges (u,v), in deliberately shuffled order:
  (10,11) (1,4) (17,7) (13,7) (7,1) (0,2) (16,3) (0,15) (4,10) (10,3)
  (13,8) (7,10) (0,3) (10,15) (4,0) (6,8) (12,7) (14,6) (15,5) (0,14)
  (1,3) (7,6) (2,12) (17,4) (9,12) (16,7) (13,11) (9,16) (16,4) (2,10)
  (0,9) (0,8) (5,7) (11,0) (2,5)

Initial separator S_start:
  2 9 11 15 14 8 3 4
Target separator S_target:
  12 16 10 5 6 13 1 17

Your four integers D,B,A,C define P(x)=D*x^3+B*x^2+A*x+C modulo q=8.
All coefficients must lie in 0..7; D and B must be even and A must be odd.
The values P(0),P(1),...,P(7) must be a permutation of task codes 0..7.
For each value x in that order, perform the token jump R_x -> L_x.
The resulting sequence of exactly q jumps must transform S_start into
S_target while every intermediate set remains an s-t separator.
Any four coefficients satisfying all of these conditions are accepted.

Give your final answer inside <answer></answer> tags as four comma-separated decimal integers D, B, A, C.
Example: <answer>2, 4, 3, 7</answer>
Output nothing else inside the tags.
```

Its planted answer is `[4,2,3,4]`. `verify(inst, [4,2,3,4])` returns
`(True, "ok")`; dropping the last coefficient returns
`(False, "wrong coefficient count: expected exactly four")`. A person can solve
this eight-task demo by hand by recovering the short precedence order and
fitting the four coefficients.

## Difficulty presets

| preset | task pairs `q` | random forward-edge rate | status |
|---|---:|---:|---|
| demo | 8 | 12% | hand example; skipped by hardener |
| easy | 32 | 10% | all 3 bare oracles solved |
| medium | 64 | 14% | 2/3 completed bare oracles solved |
| hard | 128 | 16% | **shipping candidate; 0/3 bare oracles solved** |

`escalate()` first raises edge crowding at fixed size, then doubles the graph
after that axis is exhausted; the witness remains four integers throughout.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 20/20 planted certificates verified; JSON round-trip included |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged answer recovered from surrounding prose/fence |
| G4 | pass | 0/400,000 parity-aware random certificates; language size 33,554,432 |
| G5 | pass | shipping density 0/400,000; demo exact count 4/512; reference 8/8, max 4,952 ops |
| G6 | pass | five attacks below solve 0/8; reference algorithm solves 8/8 |
| G7 | pass | doubled 256-task instance verifies; space grows to 536,870,912; answer stays 4 atoms |
| G8 | pass | 20/20 single and composed relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9 | pass | 13 characters, 4 atoms, and 47 intended-route operations; hinted/placebo remain incomplete non-gating diagnostics |

The failing attacks are input-first-occurrence fitting, numeric-code fitting,
static-indegree fitting, static degree-balance fitting, and 256 random
polynomial restarts. Each recorded 0 successes in 8 instances.

## Bare oracle loop

API-error rows are retained but do not consume attempts.

| preset | seed | model | result | reason |
|---|---:|---|---|---|
| easy | 292853864 | OpenAI Terra | solved | verified |
| easy | 1338181585 | Grok 4.6 | solved | verified |
| easy | 22559407 | Gemini 3.1 Pro | solved | verified |
| medium | 762010705 | Gemini 3.1 Pro | solved | verified |
| medium | 114063786 | Grok 4.6 | error | 900 s deadline; redrawn |
| medium | 924941173 | Claude Sonnet 5 | failed | illegal first move |
| medium | 1170586435 | OpenAI Terra | solved | verified |
| hard | 1172257587 | OpenAI Terra | failed | illegal first move |
| hard | 1432129462 | Claude Sonnet 5 | failed | illegal first move |
| hard | 505730928 | Grok 4.6 | error | 900 s deadline; redrawn |
| hard | 2145856087 | Grok 4.6 | failed | illegal second move |

The script-owned verdict is `hardened` at `hard` after two escalations.

## G9 arms

| arm | solved/completed attempts | diagnostic |
|---|---:|---|
| bare | 0/3 | hardened at shipping preset |
| structural hint | 0/2 | Terra returned an invalid witness; Gemini exhausted its response budget; the third attempt was blocked by account-limit errors |
| placebo hint | 0/0 | four account-limit errors prevented any completed attempt |

`hinted - placebo` is undefined until both arms have completed attempts; the
JSON records `0.0` only as a non-gating placeholder. The hint effect therefore
has no interpretation yet, but under the 2026-09-05 contract neither oracle arm
is a gate. The answer is 13 characters, about 4 tokens, and 4
atomic elements on the measured shipping instance (the measured family-wide
worst case is 5 tokens). The intended post-insight
route is 47 exact arithmetic operations, within the 300-operation cap.

## Use

```python
from gen_2004_10873 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
question = render(inst)
answer = parse_answer("<answer>" + ",".join(map(str, inst["answer"])) + "</answer>")
assert verify(inst, answer) == (True, "ok")
```

Emit from the repository root with:

```bash
scripts/emit.sh 2004.10873 20 hard
```

## Caveats

- This is not distributional NP-hardness. Recognizing the matched-pair gadget
  makes the successful linear-time reference algorithm available; that fact is
  the Track-B hardness basis, not hidden in an attack table.
- `0/400,000` estimates density only under the declared uniform prior on
  parity-constrained cubic coefficients. It is not a posterior for a solver
  using the graph, and the exact demo density is much larger (4/512).
- The hidden order is deliberately unique. A full dynamic topological
  elimination solves it, while one-shot degree rankings did not; stronger
  learned ranking, SAT/SMT encodings, and generic reconfiguration BFS were not
  benchmarked separately.
- Task codes are semantic attributes used by the polynomial certificate, not
  vertex identifiers. G8 permutes every raw graph vertex while retaining those
  attributes. Arbitrarily permuting the semantic codes changes the stated
  certificate problem and is not treated as a graph relabelling.
- The polynomial permutation condition over powers of two is rechecked by
  exhaustive evaluation in `verify`; no external algebra theorem or CAS is
  trusted by the checker.
- The hinted and placebo diagnostics are unresolved because of external quota.
  They provide no evidence about the hint effect; this does not alter the bare
  hardening result or the gated G9 size/effort caps.
