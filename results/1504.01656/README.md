# Exact constant-multiplier SOS refutations

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | algebra |
| object regime | rational exact |
| computational core | linear algebra |
| certificate form | rational vector encoding an SOS refutation |
| intended intuition | invariant — a common missing Walsh frequency |
| domain essentiality | native |
| reduction | none |

This generator is based on Lauria and Nordström,
[“Tight Size-Degree Bounds for Sums-of-Squares Proofs”](https://arxiv.org/abs/1504.01656).
It presents exact linear polynomial equations over Q. The solver returns one
constant rational multiplier per equation; the checker accumulates every
polynomial coefficient and accepts exactly when the resulting identity is
`-1`. This is the paper's native SOS-refutation object from Definition 2.2,
not a SAT, graph, or finite-field surrogate.

Trust status: all local gates G1–G9 pass, but the family is **rejected because
H fails on Track B**. The no-tool oracle pool solved the named hard preset 3/3
and also solved the first escalated preset. The retained module is therefore
named `rejected_gen_1504_01656.py`; see `REJECTED.md` for the decision record.

## Family and construction

Rows are labelled by the nonzero vectors `x` in `F_2^b`. Generation first
chooses a hidden nonzero mask `s` and the multiplier
`lambda_x=(-1)^(s dot x)`. It then samples every public coefficient column `a`
inside the exact hyperplane `lambda dot a=0`. Every displayed polynomial has
constant term 1, while character orthogonality gives
`sum_x lambda_x=-1`. Thus the planted identity

```text
sum_x lambda_x p_x(X) = -1
```

is known before the public system exists. No emitted instance is solved during
generation. The verifier does not read `inst["answer"]`.

## Why Track B

The paragraph before Section 1.1 explains that degree-`d` SOS proof search is
an SDP/coefficient-matching problem solvable in `n^O(d)` time. Here it
specializes further to exact linear elimination. The implemented modular
Gaussian reference algorithm, followed by rational validation, solves 8/8
shipping-candidate instances in `O(n*m^2+m^3)`. It averaged 671,237 exact
field operations and about 0.029 seconds per instance in the recorded run.

The compact route treats one coefficient column as a function on five-bit
labels, restores its value zero at label `00000`, and notices its missing
Walsh frequency. A 32-point transform and Gray-code sign generation take 222
exact operations. That is below the no-tool route cap, but the oracle results
show that the invariant is visible enough for current models to execute.

The paper's headline lower-bound family is not used to make a false Track A
claim. Theorem 3.6 only gives high-probability properties for random 3-XOR,
Theorem 3.9 fixes a good sample by existence, and Theorem 4.12's relativized
instances require huge SOS proofs. Those facts neither certify every random
sample nor fit the benchmark's witness-size cap.

## Worked demo

`make_instance(n=12, label_bits=3, coeff_bound=3, seed=0)` renders these seven
equations; every row has the common constant term 1:

```text
E00 label=110: 1 3 0 3 0 -3 -3 0 3 1 3 1
E01 label=011: 3 -2 -3 -3 -1 -1 3 0 -1 -2 2 -3
E02 label=101: 1 0 0 2 -2 -2 -3 -1 1 -2 3 -3
E03 label=111: 2 -1 1 1 -1 0 1 -1 -1 -3 -3 0
E04 label=010: 0 -2 -2 1 -3 -1 1 3 -1 3 3 -3
E05 label=100: 0 -3 2 2 -2 -1 -3 1 -1 1 -2 -1
E06 label=001: -1 -1 0 2 -3 2 2 0 -2 -2 0 -3
```

A valid response is:

```text
<answer>-1, -1, 1, 1, 1, -1, -1</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last
multiplier returns `(False, "missing multipliers: expected 7, got 6")`. The
demo is hand-solvable: its 8-point Walsh transform is short enough to carry
out on paper.

## Difficulty presets

| preset | variables / columns | row-label bits | equations | coefficient bound | matrix entries | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 12 | 3 | 7 | 3 | 84 | hand example; hardening skips it |
| easy | 96 | 5 | 31 | 7 | 2,976 | defeated: 2/3 solved |
| medium | 256 | 5 | 31 | 11 | 7,936 | defeated: 1/3 solved |
| hard | 640 | 5 | 31 | 17 | 19,840 | **rejected candidate: 3/3 solved** |

`escalate()` doubles the number of coefficient columns at the same 31-entry
witness length, then raises coefficient range. It grows the input rather than
the answer, but the oracle run showed that this does not harden the compact
route because any one column suffices.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified; all answers JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic prose/fence response parsed; garbage returned `None` |
| G4 | 0/200,000 structure-aware guesses; exact density `1/300,540,195` |
| G5 | unique candidate certificate; demo count 1/35; reference average 671,237 operations |
| G6 | row norm, greedy prefix, 256 balanced restarts, and obvious Walsh ansatz all 0/8; reference 8/8 |
| G7 | doubled 1,280-column instance verified with unchanged answer length |
| G8 | 80/80 relabelling checks and 80/80 carried witnesses; 20/20 unrelated keys distinct |
| G9 | pass under the current rule: 203 chars, 62 atoms, 222 route operations |

Exact values and wall-clock measurements are in
[`selftest_report.json`](selftest_report.json).

## Oracle loop and G9 arms

The bare ladder was invoked only through `scripts/harden.py`. It defeated every
named level and one automatically escalated level before the key reached its
total limit. The isolated G9 arms had previously stopped after four consecutive
403 responses, so they remain diagnostic with zero completed attempts.

| bare level | completed attempts | solved | result |
|---|---:|---:|---|
| easy (`n=96`) | 3 | 2 | defeated |
| medium (`n=256`) | 3 | 1 | defeated |
| hard (`n=640`) | 3 | 3 | defeated |
| escalated (`n=1280`) | 2 | 1 | defeated before quota stopped the third slot |

| G9 diagnostic arm | completed attempts | solved | provider errors |
|---|---:|---:|---:|
| bare | 3 | 3 | 0 |
| structural hint | 0 | 0 | 4 |
| placebo hint | 0 | 0 | 4 |

The hinted-minus-placebo diagnostic is numerically recorded as `0.0`, but it
has no evidentiary meaning with zero completed attempts. The candidate answer
is 203 serialized characters, 51 conservative tokens, and 62 atomic integers;
the intended route is 222 exact operations. All size/effort caps pass.

## Use

```python
from rejected_gen_1504_01656 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

The module is retained for audit and local inspection; it must not be emitted
as a shipping family.

## Caveats

- This is Track B. Gaussian elimination efficiently solves every instance;
  there is no average-case computational-hardness claim.
- `0/200,000` is a sampled diagnostic. Uniqueness and the exact
  `1/300,540,195` density additionally follow from the measured full rank over
  a large prime, which certifies full rank over Q.
- The sampling prior already enforces answer length, the `{-1,+1}` alphabet,
  and the freely deducible constant sum (exactly fifteen `+1` entries). It does
  not condition on recognizing the Walsh family; doing so is the intended
  insight, not a free syntactic constraint.
- The adversary panel did not treat a full Walsh transform, covariance
  eigensolver, or rational nullspace package as a failing attack. Those are
  tool algorithms and are covered by the successful Track-B reference route.
- The canonical key handles equation and variable permutations by weighted
  color refinement. It is not a complete canonizer under arbitrary rational
  row operations, so equivalent linear presentations could receive different
  keys.
- The hard prompt is about 60k characters, yet all three hard-preset oracle
  attempts solved it. Increasing the number of columns does not raise the
  222-operation compact route, because any one column exposes the same Walsh
  frequency.
- The OpenRouter key-limit errors are external missing data and were never
  counted as model failures. The rejection rests on completed valid answers,
  not on those errors.
