# arXiv 2107.03097 — transformed cubic Thue witnesses

## Profile and status

| field | value |
|---|---|
| `TRACK` | **B** — an exact solver exists and is disclosed |
| native domain | number theory |
| object regime | integer lattice |
| computational core | other (bounded binary-cubic/Thue search) |
| certificate form | integer tuple `[x,y]` |
| native objects | irreducible homogeneous binary cubic form over `Z`; bounded integer-lattice rectangle |
| intended intuition | change of variables: three transformed projective roots crowd around one primitive rational direction |
| domain essentiality | native |
| reduction | none |
| candidate shipping preset | `easy` |

The construction, verifier, density, attack, scaling, canonical-key, and output-cap gates all pass. The required external oracle claim is **not yet established**. The current repository harness obtained two scored bare failures—one empty length-limited response and one incorrect integer pair—but OpenRouter then returned HTTP 403 `Key limit exceeded (total limit)` before the third scored attempt. The separately run hinted and placebo arms received only 403 errors. The genuine script-written transcripts are retained, but this result must not be submitted as hardened until a funded key completes the bare arm.

## The problem

Ingrid Vukusic’s paper [*On a cubic Family of Thue Equations involving Fibonacci Numbers and Powers of Two*](https://arxiv.org/abs/2107.03097) proves in Theorem 1 that, for every integer `N >= 3`,

```text
Q_N(X,Y) = X(X-F_N Y)(X-2^N Y)-Y^3 = +/-1
```

has only the eight signed versions of `(1,0)`, `(0,1)`, `(F_N,1)`, and `(2^N,1)`. The generator chooses a primitive positive vector `v`, makes it the first column of a determinant-one integer matrix `A`, and publishes the expanded cubic `Q_N(A^-1(x,y))`. A supplied positive box contains `v` but none of the other seven transported solutions. The solver returns one primitive lattice point in that box; `verify` checks bounds, gcd, and the cubic substitution with exact integers.

This is generation by a structure-preserving transformation. The planted answer is carried from `(1,0)` before the public coefficients are assembled; `make_instance` never solves the generated equation. Theorem 1 proves that the box contains exactly one answer, while the grader needs no completeness theorem because a submitted witness is accepted solely by substitution.

## Why Track B

The unmodified paper family fails H immediately: `(1,0)` is a valid answer for every `N`, and Lemma 6 explicitly classifies all `|Y| <= 1` solutions. Asking for all solutions would not fix this, because an unchecked list is not a witness of completeness.

The coordinate transport creates a no-tool compression task, not a Track-A claim. A dependency-free complete scan of the shipping box succeeds on 8/8 instances, averaging 2,151,529 lattice evaluations and 8,637,629 counted exact operations. It took 2.05 seconds per instance on the final host run (earlier runs ranged from 0.22 to 3.80 seconds under varying load). The compact solver uses Vieta’s identity `-c1/(3*c0)` for the mean of the three roots of `c0*t^3+c1*t^2+c2*t+c3`, then continued-fraction reconstruction; it succeeds on 8/8 gate instances and 10,000/10,000 additional shipping-distribution seeds in at most 151 conservatively counted operations. The arithmetic operands have roughly 130 decimal digits, so even that compact route is not routine mental calculation. This mirrors the paper’s root-approximation viewpoint in Section 3 and its continued-fraction/Baker–Davenport computations in Section 4. Section 3 reports a couple of minutes for PARI/GP at `N <= 28`, Section 4 about one hour for all `29 <= N <= 1000`, and Section 6 finishes with LLL—clear reasons not to claim structural hardness.

## Worked demo

The `demo` preset is deliberately the unscrambled `N=4` equation and is hand-solvable:

```text
Find one primitive integer solution of this bounded binary cubic equation.

A primitive integer solution is an ordered pair (x,y) of ordinary base-10 integers with gcd(|x|,|y|)=1.  It must satisfy the displayed equation exactly; either right-hand sign is allowed.  Multiplication is written with *, and powers have their usual integer meaning.

Equation:
  x^3 - 19*x^2*y + 48*x*y^2 - y^3 = +1 or -1

Inclusive coordinate bounds:
  1 <= x <= 4
  1 <= y <= 4

Both endpoints are included.  The order matters: the first coordinate is x and the second is y.  No floating-point approximation is accepted.

Give your final answer inside <answer></answer> tags as a JSON list of exactly two base-10 integers [x,y].
Example: <answer>[3,-17]</answer>
Output nothing else inside the tags.
```

Here `F_4=3`, so `<answer>[3,1]</answer>` works because the middle factor vanishes and the remaining value is `-1`:

```python
>>> verify(inst, [3, 1])
(True, 'ok')
>>> verify(inst, [1, 3])
(False, 'exact substitution gives 349, not +1 or -1')
```

A person can solve this demo by inspection. The benchmark presets hide that factorization through a large unimodular coordinate change.

## Difficulty presets

| preset | box width `W` | paper `N` | offset scale | shear scale | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 4 | 1 | 1 | hand example, not scrambled |
| easy | 2,049 | 220 | 8 | 4 | configured shipping preset; local gates pass, oracle verdict incomplete |
| medium | 4,097 | 260 | 12 | 6 | available escalation |
| hard | 8,193 | 300 | 16 | 8 | available escalation |

No preset was rejected by a local gate. The external ladder scored two failures at `easy`, then stopped on quota before it could decide that rung.

## Gate results

| gate | result |
|---|---|
| G1 planted verifies | pass, 12/12 preset/seed instances; JSON round-trip also checked |
| G2 corruption | pass, 5/5 rejected with five distinct reasons |
| G3 parser | pass on prose plus fenced JSON; garbage returns `None` |
| G4 guessing | pass, 0/200,000 uniform primitive guesses; exact language size 2,553,640 |
| G5 density and cost | pass locally; Theorem 1 gives one answer, density `3.9159787597312074e-7`; strongest failing attack tested 65,536 candidates in 0.77 s total, while the exact reference scan averaged 2,151,529 evaluations and 2.05 s on the final run |
| G6 adversaries | pass: landmarks, 48-step residual descent, 8,192 restarts, and two-decimal centroid each score 0/8; reference scan scores 8/8 and compact reconstruction scores 8/8 plus 10,000/10,000 stress seeds |
| G7 scaling | pass; doubling width grows the primitive candidate space from 2,553,640 to 10,208,142 |
| G8 canonical key | pass, 320 invariance and carried-witness checks across the full 16-element presentation-symmetry group; 20/20 unrelated keys distinct |
| G9(c) caps | pass: 13 characters, about 4 tokens, 2 atoms, 151 intended-route operations |

## Oracle loop and G9 diagnostics

The bare harness wrote six schema-v2 records. Two are scored model failures and four are API errors that correctly do not count as attempts. The configured repository harness currently uses a two-vendor pool, despite older task prose describing four vendors.

| preset | seed | model drawn | scored? | reason |
|---|---:|---|---|---|
| easy | 888713556 | `google/gemini-3.8-flash` | failed | exhausted 32,000-token response budget without emitting an answer |
| easy | 1480841433 | `openai/gpt-5.6-terra` | failed | returned `[21809,21823]`; exact substitution rejected it |
| easy | 822185348 | `openai/gpt-5.6-terra` | unscored | HTTP 403 key total limit |
| easy | 684312897 | `openai/gpt-5.6-terra` | unscored | HTTP 403 key total limit |
| easy | 1077462433 | `openai/gpt-5.6-terra` | unscored | HTTP 403 key total limit |
| easy | 794901683 | `openai/gpt-5.6-terra` | unscored | HTTP 403 key total limit |

| G9 arm | solved / valid attempts | API errors | conclusion |
|---|---:|---:|---|
| bare | 0 / 2 | 4 | two genuine failures, but no completed verdict |
| structural hint | 0 / 0 | 4 | unavailable |
| placebo hint | 0 / 0 | 4 | unavailable |

`hinted - placebo` is not estimable from zero valid attempts in those arms; the stored numerical placeholder is `0.0` and must not be interpreted as evidence. The structural hint names only the crowded-root invariant, not the Vieta/continued-fraction procedure. The measured answer is 13 characters, about 4 tokens, and 2 atomic elements; the intended route is at most 151 counted exact operations.

## Use

From the repository root:

```python
import importlib.util

path = "results/2107.03097/gen_2107_03097.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
print(g.render(inst))
answer = g.parse_answer("<answer>[123,456]</answer>")
print(g.verify(inst, answer))
```

Because result directories are named with dots, ordinary package import is awkward; loading with `importlib.util.spec_from_file_location` is the reliable option used by the repository scripts. Emit examples with:

```bash
bash scripts/emit.sh 2107.03097 20
```

## Caveats

- This family becomes easy with exact rational arithmetic: the included centroid/continued-fraction solver recovered all 10,008 tested answers in at most 151 conservatively counted operations. That is the declared Track-B premise, not a hidden weakness.
- Operation counts treat arithmetic on roughly 130-digit coefficients as one exact operation; they are not bit-complexity counts. Measured reference-scan time varied from 0.22 to 3.80 seconds per instance with host load (2.05 seconds in the final report), while those same divisions are not realistic mental arithmetic.
- The reported random-guess probability is uniform over all primitive pairs in the displayed box. It does not model a solver’s strong prior for rational approximants, and the exact compact algorithm is much stronger than random guessing.
- PARI/GP, Sage, a general binary-cubic reduction package, and a separate LLL implementation were unavailable and were not run. The reference is a complete exact bounded scan; the compact route covers the paper’s continued-fraction idea only for this generated distribution.
- The adversary panel does not include arbitrary-precision numerical root isolation or general `GL(2,Z)` form equivalence. Either may make these instances mechanically easier; this is another reason the claim is only no-tool compression.
- `canonical_key` is exact under variable exchange, independent sign changes, global form negation, and their compositions. It is not a complete `GL(2,Z)`-equivalence classifier; such transformations generally turn the rectangular answer region into a parallelogram and are outside this presentation’s relabelling group.
- Most importantly, only two valid bare oracle responses were obtained, both failures; that is still one short of the harness requirement, and neither G9 comparison arm obtained a valid response. Local gates establish correctness and measured baselines, but not the required empirical no-tool hardness. Re-run all three harness arms after restoring OpenRouter quota, update `G9_RESULTS`, regenerate `selftest_report.json`, and only then treat `SHIPPING_DIFFICULTY` as final.
