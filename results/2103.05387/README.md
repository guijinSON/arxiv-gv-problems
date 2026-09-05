# Temporal-star exploration generator for arXiv:2103.05387

> Status: all local gates pass, but the result is **not yet shippable**. The
> required OpenRouter runs received account-level HTTP 403 responses before any
> oracle answered. Those errors are preserved and are not counted as failures.

| profile field | value |
|---|---|
| track | B — no-tool compression |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | permutation / bipartite matching |
| certificate form | integer tuple: one visit slot per temporal-star edge |
| intended intuition | invariant: odd-cardinality row XORs expose a hidden affine map over binary vectors |
| domain essentiality | native |
| reduction | none |

## What the problem is

The family uses `StarExp`, the temporal-star exploration problem defined in
Section 2 of Bumpus and Meeks, [*Edge exploration of temporal
graphs*](https://arxiv.org/abs/2103.05387). A solver receives a star whose leaf
edges are active at specified integer times and must give a closed strict
temporal walk visiting every leaf.

There are `n` two-time visit slots. Slot `s` means traversing a leaf edge out at
time `2s+1` and back at `2s+2`. The answer assigns every edge one allowed slot;
all slots must be distinct. Exact membership and permutation checks followed by
temporal replay verify any submitted witness in linear time. An exploration has
at least `2n` traversals, while these instances have exactly `2n` distinct
global times, so every exploration is necessarily a slot-aligned permutation;
the encoding does not discard a different kind of valid exploration.

Generation samples a dense invertible linear map on binary vectors and several
translation offsets. Every offset gives a permutation of the slots; one is
sampled uniformly and carried as the certificate. No matching or exploration
search occurs during generation.

## Why Track B is the honest claim

This distribution is not claimed hard in the Track A sense. Theorem 3.1 and
Corollary 3.2 prove that general `StarExp(k)` is NP-complete for `k >= 4`, and
each generated hard edge has six appearances, but a worst-case theorem says
nothing about this structured distribution.

Here the domain-standard method is Hopcroft–Karp on the edge/slot incidence
graph, in `O(E sqrt(V))`. At provisional shipping parameters `n=256`, degree 3,
seed 271828, it solved the instance in 0.000210 seconds using 1,280
availability-edge inspections. Across eight audit seeds it solved 8/8 using
11,376 inspections in 0.001140 seconds. This algorithm is intentionally
disclosed: tool access defeats the family.

The compact no-tool route uses a different invariant. Because every row has odd
size, XORing its entries reveals the hidden affine image of the edge label up to
one constant. Row 0 and the eight power-of-two rows recover the map's columns;
one allowed slot for edge 0 then extends by XOR. This is 281 exact XOR operations
at `hard` (299 after the fixed-length degree-5 escalation). The intended test is
recognizing that invariant, not executing matching unaided.

The paper also identifies the easy regimes that had to be recorded: `StarExp`
with at most three appearances per edge is polynomial-time solvable (Section 1),
Corollary 4.5 gives an `O(w^3 2^(3w) Lambda)` algorithm parameterized by
interval-membership-width, and Corollary 5.5 makes evenly-spaced instances FPT
in the appearances-per-edge parameter. The present Track B matching shortcut is
stronger than those paper algorithms on this deliberately structured subclass.

## Worked demo

`make_instance(n=8, degree=3, seed=0)` renders this availability table:

```text
EDGE : AVAILABLE SLOTS
0 : 5 6 7
6 : 4 5 6
2 : 0 2 3
3 : 4 5 7
5 : 4 6 7
1 : 0 1 2
7 : 1 2 3
4 : 0 1 3
```

A person can solve this demo on paper. The carried answer is
`[5, 2, 0, 7, 3, 4, 6, 1]`:

```python
verify(inst, [5, 2, 0, 7, 3, 4, 6, 1])
# (True, "ok")
verify(inst, [5, 2, 0, 7, 3, 4, 6])
# (False, "wrong length: expected exactly 8 slots")
```

## Difficulty presets

| preset | leaves / slots `n` | allowed slots per edge | candidate-space bits | status |
|---|---:|---:|---:|---|
| demo | 8 | 3 | 15.3 | hand-scale illustration |
| easy | 64 | 3 | 296.0 | oracle rerun blocked before scoring |
| medium | 128 | 3 | 716.2 | not reached |
| hard | 256 | 3 | 1684.0 | provisional `SHIPPING_DIFFICULTY` |

If `hard` is solved, `escalate()` raises the decoy degree to 5 without changing
the 256-element answer. The compact route then costs 299 operations. Beyond
that, the answer and intended route are at the published caps, so the module
returns `cap_bound`.

An earlier cyclic-arithmetic version was discarded after the oracle exposed its
constant-step answer: Gemini solved 2/3 easy attempts and 1/3 medium attempts.
Those replies motivated the binary-linear hardening; they are not reused as
evidence for the revised family.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified across all presets |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0 hits / 200,000 structure-aware permutation samples |
| G5 | pass | hard density 0/200,000; demo exactly 81/40,320; strongest failing attack used 256 restarts in 0.030705 s |
| G6 | pass | four attacks at 0/8; Hopcroft–Karp at 8/8 as expected |
| G7 | pass | doubled build at `n=512`; candidate space grows from 1684.0 to 3875.2 bits |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 1,170 chars, 293 estimated tokens, 256 atoms, 281 operations |

## Oracle loop and G9 arms

The current script-owned bare transcript contains four retries at `easy`, all
unscored because OpenRouter returned the account-level total-limit 403. The
harness correctly stopped without a verdict.

| arm / preset | scored solves / attempts | API errors | conclusion |
|---|---:|---:|---|
| bare / easy | 0 / 0 | 4 | no hardness claim possible |
| structural hint / hard | 0 / 0 | 4 | diagnostic pending |
| placebo / hard | 0 / 0 | 4 | diagnostic pending |

`hinted - placebo` is undefined until both arms receive scored calls. The local
G9(c) cap is a gate and passes; the three oracle arms are diagnostic, but Step 4
still requires a successful bare hardening run before shipping.

## How to use it

```python
from gen_2103_05387 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
```

After OpenRouter quota is restored, rerun the bare harness here, run structural
and placebo copies in separate scratch directories, update the transcript-owned
counts, rerun `selftest()`, and only then emit:

```bash
python3 ../../scripts/harden.py gen_2103_05387.py
bash ../../scripts/emit.sh 2103.05387
```

The module is standard-library-only; `gvlib` is unnecessary for these exact
integer and XOR checks.

## Caveats

The most important caveat is that Step 4 is incomplete because of external
quota, so `hard` is provisional rather than empirically hardened. The measured
reference/compact gap is 1,280 versus 281 counted operations on the fixed audit
seed—enough to separate a bookkeeping-heavy matcher from the invariant route,
but much smaller than a million-operation reference benchmark.

The 0/200,000 guess result samples uniformly from all slot permutations, already
enforcing the obvious distinct-slot rule. It is not an estimate under an
availability-aware or XOR-aware prior. The attack panel covers slot-frequency
outliers, deterministic first fit, 256 randomized greedy restarts, and the
ordinary modular-shift ansatz. It does not cover every matching heuristic,
SAT/ILP encoding, or learned binary-pattern recognizer; Hopcroft–Karp already
shows that any ordinary tool-enabled matching implementation wins. The
canonical key is complete for leaf relabelling and row presentation order while
integer time labels remain fixed; it deliberately does not quotient by arbitrary
time permutations, which do not preserve strict temporal order.
