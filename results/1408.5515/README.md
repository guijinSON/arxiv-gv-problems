# Primary decomposition certificates from arXiv:1408.5515

Status: the generator and local gates G1--G8 pass, but this result is **not
shippable yet**.  The required oracle experiment aborted when OpenRouter returned
`Key limit exceeded`; G9 and the bare hardening verdict are therefore unmeasured.
The partial `llm_loop_transcript.jsonl` is script-owned and retained as evidence,
but its API errors are not counted as model failures.

| Profile field | Value |
|---|---|
| Track | B -- no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | exact symbolic |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## The problem

The source is Idrees, Sadiq, and Tassaddiq, [*On primary decomposition of
modules*](https://arxiv.org/abs/1408.5515).  Definition 1.3 defines a reduced
primary decomposition of a submodule of `Q[X]^s`; this family stays in those
native objects at rank `s=1`.  The solver receives an expanded sparse polynomial
`F` defining the principal ideal `(F)` and returns a bounded affine-coordinate
certificate for two prime (therefore primary) principal components.

Generation samples a triangular affine coordinate chain `z_i`, a center `c`,
and a positive gap `p`, then expands

```text
F = (product(z_i) + c)^2 - p^2.
```

In the certified coordinates the two factors are `product(z_i)+(c-p)` and
`product(z_i)+(c+p)`.  Their constants are nonzero, so each primitive polynomial
is irreducible and hence prime.  They differ by the nonzero rational unit `2p`,
so they are comaximal and their intersection equals their product `(F)`.
`verify` checks the coordinate bounds and the complete expanded identity using
exact rational arithmetic; it never reads `inst["answer"]`.

## Why Track B

This paper is algorithmic, not a hardness result.  Algorithm 2.15 and the
procedures in Section 3 compute module primary decompositions using associated
primes, Ext, localization, saturation, Gröbner bases, and equidimensional hulls.
That rules out Track A.  For this bounded principal-ideal family the executable
reference is exact multivariate square-root extraction followed by bounded
affine trial division.  At the current `medium` preset it solves 8/8 instances,
averaging 1,519,764 exact coefficient operations and 1.9--2.9 seconds across
the final local runs
(`O(T^2+n^2 m^2 T^2)` for `T` sparse terms).

The compact route is independently implemented as `_compact_route`.  The top
homogeneous layer determines the hidden path order and link coefficients; the
next layer gives offsets by a backward recurrence; a two-state path recurrence
then gives the center and gap.  It reconstructs and verifies the shipping
witness in 107 exact operations.  The intended challenge is recognizing those
coefficient layers in a 4,000-term expansion without a CAS.

## Worked demo

For `make_instance(n=2, variables=2, seed=11)`, the complete polynomial input is:

```text
  8/1 | [0, 3]
  -20/1 | [1, 0]
  -2/1 | [1, 1]
  4/1 | [0, 4]
  21/1 | [0, 0]
  4/1 | [1, 3]
  1/1 | [2, 2]
  12/1 | [1, 2]
  -20/1 | [0, 1]
  -16/1 | [0, 2]
  4/1 | [2, 0]
  4/1 | [2, 1]
```

The answer is

```json
{"order":[0,1],"links":[[2,1]],"offsets":[[-2,1],[2,1]],"center":[-1,1],"gap":[2,1]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Removing the last
offset returns `(False, "offsets must contain exactly 2 rationals")`.  This demo
is genuinely hand-scale: expanding `(x0+2*x1-2)(x1+2)-1` recovers the displayed
difference of squares.

## Difficulty

| Preset | `n` | Variables | Typical sparse terms | Status |
|---|---:|---:|---:|---|
| demo | 2 | 2 | 7--12 | hand-solvable illustration |
| easy | 14 | 5 | about 940 | oracle verdict incomplete |
| medium | 14 | 6 | about 4,053 | provisional shipping preset |
| hard | 20 | 6 | about 4,053 | not reached by completed run |

`n` raises coefficient entropy and the bounded trial-division haystack while
leaving the 32-atom answer shape and the 107-operation compact route fixed.

## Local gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified |
| G2 | pass | 5/5 corruptions rejected with distinct reasons |
| G3 | pass | tagged JSON round-trip verified |
| G4 | pass | 0 hits / 200,000 structure-aware samples; space 70,536,298,020,848,271,360 |
| G5 | pass | demo has exactly 1 answer in 384; shipping sampled density 0/200,000; baseline 1,519,764 ops |
| G6 | pass | four attacks had 0/8 successes each; reference solved 8/8 |
| G7 | pass | doubling `n` verifies; search-space ratio floor 8,343 |
| G8 | pass | 60 invariance and 60 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | **not run** | 158 worst-case chars, 40 estimated tokens, 32 atoms, 107 verified exact operations; oracle component missing |

## Oracle loop and G9 arms

The latest bare run did not finish a level and made no shipping verdict:

| Preset | Model | Seed | Outcome | Reason |
|---|---|---:|---|---|
| easy | Claude Sonnet 5 | 126647211 | failed | empty length-limited response; scored by harness |
| easy | Grok 4.6 | fresh seeds | error | two 900 s deadlines, followed by OpenRouter 403 key-limit errors |

| G9 arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0 / 0 at shipping preset | not measured |
| hinted | 0 / 0 | not measured; G9(b) does not pass |
| placebo | 0 / 0 | not measured |

No hinted-minus-placebo inference is possible.  After the key is reset, rerun the
bare ladder, select the rung that actually holds, then run the structural and
placebo copies in separate scratch directories as specified by the task.

## Use

```python
import gen_1408_5515 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
statement = g.render(inst)
answer = g.parse_answer('<answer>' + __import__('json').dumps(inst['answer']) + '</answer>')
assert g.verify(inst, answer) == (True, 'ok')
```

From the repository root, once all oracle gates pass:

```bash
bash scripts/emit.sh 1408.5515
```

## Caveats

- The current result is blocked on external oracle quota and must not be counted
  as hardened.  `selftest_report.json` intentionally has `all_passed=false`.
- G4 samples the declared bounded certificate language after all obvious shape
  constraints.  Zero hits bounds that sampling prior; it is not a proof of
  uniqueness at shipping size.  Exact enumeration establishes uniqueness only
  for the demo.
- The standard Singular implementation from the paper was not available in the
  environment.  The reported reference algorithm is a family-specific exact
  factor-and-trial implementation, not a timing of Singular's full Algorithm 2.15.
- The adversary panel does not include a production CAS factorizer.  Such a tool
  is expected to solve the family and is precisely why the claim is Track B.
- `canonical_key` is exact under input-term reorderings and variable
  permutations.  General affine equivalence of multivariate polynomials is not
  canonicalized; the key uses the strongest cheap incidence invariant implemented
  here, so rare collisions or missed affine isomorphisms are possible.
- A solver that immediately notices the top-layer coefficient order can execute
  the 107-operation route; that is the intended insight, not a hardness claim
  against equipped algebra systems.
