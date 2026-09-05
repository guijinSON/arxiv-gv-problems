# arXiv 1205.0852 — workflow satisfiability generator

> Status: the module and every local gate pass, but the result is **not yet
> shippable**. The required oracle and G9 calls were made with `harden.py`; all
> revised calls received HTTP 403 `Key limit exceeded (total limit)`, so no model
> failure can honestly be recorded and STEP 4 remains incomplete.

| Profile | Value |
|---|---|
| Track | B — a polynomial reference algorithm exists and is disclosed |
| Native domain / regime | combinatorics / finite discrete |
| Computational core | CSP satisfiability (authorization matching) |
| Certificate | integer tuple: one concrete workflow plan |
| Intended intuition | invariant: authorization-row sums have constant modular difference in step-residue order |
| Domain essentiality | native; `reduction_kind=none` |

## Problem and trust basis

This generator follows Crampton, Gutin, and Yeo, [*On the Parameterized
Complexity and Kernelization of the Workflow Satisfiability
Problem*](https://arxiv.org/abs/1205.0852). A solver receives the paper's native
objects: workflow steps, users, the step-user authorization relation, and one
counting constraint `(1,S)`. Section 2.2 defines that constraint to require a
different user for every step in `S`. The answer is a plan assigning one
authorized user to every step. Verification is only exact membership and
distinctness checking.

The generator samples a slope and a set of offsets in `Z_p`. Every authorization
edge has the form `user_residue = slope * step_residue + offset (mod p)`; each
offset therefore gives a full valid plan. All displayed edges belong to one of
these certificate-bearing matchings, so there is no locally exceptional planted
edge. One offset is sampled as `inst["answer"]`; the completed instance is never
solved during generation.

This is Track B, not Track A. Theorem 3.6 says WSP with counting constraints is
FPT. More specifically, the proof of Theorem 6.5 constructs the authorization
bipartite graph and invokes Hopcroft–Karp. For this all-different special case a
full matching is already the complete answer, in
`O(|A| sqrt(|S|+|U|))`. Across eight shipping instances, the implementation
solved 8/8 in 0.056531 seconds total and scanned 71,368 edges (8,921 per
instance; the asymptotic bound evaluates to 79,401 at this preset). The compact
route instead sums the rows with step residues 0 and 1, obtains the common
difference, and fills the residue-indexed matching. It needs 238 modular field
operations. Random step-residue labels prevent the answer itself from appearing
as an arithmetic progression in step-ID order.

## Worked demo (`seed=0`)

```text
WORKFLOW SATISFIABILITY: AUTHORIZED ALL-DIFFERENT PLAN

There are 7 workflow steps S0,...,S6 and 7 users U0,...,U6.
There are no precedence restrictions. A plan assigns exactly one user to
each step. It is authorized when the assigned user occurs in that step's
authorization row.

The counting constraint is (1,1,{all steps}): all seven assigned users differ.
For every i, both Si and Ui carry residue i in Z_7.

S2: U0,U4
S0: U6,U3
S3: U4,U1
S1: U3,U0
S6: U6,U2
S5: U5,U2
S4: U1,U5

Return seven integer user IDs in fixed order S0,...,S6.
```

The answer `[6, 3, 0, 4, 1, 5, 2]` gives `(True, "ok")`. Replacing its
last entry by `6` gives `(False, "counting constraint (1,1,S) is violated by a
repeated user")`. This seven-row demo is genuinely hand-solvable.

## Difficulty and gates

| Preset | Steps/users | Users per row | Rendered chars | Status |
|---|---:|---:|---:|---|
| demo | 7 | 2 | 1,554 | hand-scale illustration |
| easy | 101 | 10 | 9,088 | first oracle rung; revised run blocked by quota |
| medium | 151 | 15 | 17,063 | locally verified |
| hard | 199 | 20 | 27,248 | selected shipping preset; locally verified |

| Gate | Measured result |
|---|---|
| G1 | pass: planted and compact-route plans verified on 12/12 preset/seed cases |
| G2 | pass: drop, swap, duplicate, empty, and out-of-range corruptions got five distinct rejection reasons |
| G3 | pass: 199 entries round-trip through prose, fences, tags, and JSON |
| G4 | pass: 0/200,000 valid structure-aware guesses, sampled uniformly from all `199!` user permutations |
| G5 | pass locally: shipping density 0/200,000; demo has exactly 2/5,040 valid plans; strongest reference cost 71,368 edge scans over 8 cases |
| G6 | pass: outlier, row-minimum, greedy, 256-restart greedy, and slope-one attacks each solved 0/8; Hopcroft–Karp solved 8/8 as expected |
| G7 | pass: a 401-step, degree-40 instance built and verified |
| G8 | pass: 20/20 composed relabelings preserved key and carried witness; 20/20 unrelated keys were distinct |
| G9(c) | pass: 687 characters, 172 estimated tokens, 199 atoms, 238 field operations |

## Oracle loop and G9 diagnostics

The current transcripts are script-authored evidence of an external blocker,
not hardness evidence. Every row below is `solved="error"`; API failures are
correctly excluded from attempts. A superseded ordered-label prototype was
solved by both available vendors before the quota ran out, which is why the
current generator independently permutes step residues. Those old replies do
not count for the revised family.

| Arm / preset | Calls | Scored attempts | Result |
|---|---:|---:|---|
| bare / easy | 4 | 0 | all HTTP 403 quota errors |
| structural / hard | 4 | 0 | all HTTP 403 quota errors |
| placebo / hard | 4 | 0 | all HTTP 403 quota errors |

Thus bare, hinted, and placebo are each `0/0`; hinted-minus-placebo is undefined,
and the hinted verdict is `pending`. No conclusion about structural help is
possible until the account limit is replenished and all three arms are rerun.

## Use

```python
from gen_1205_0852 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
question = render(inst)
wire = "<answer>" + ",".join(map(str, inst["answer"])) + "</answer>"
answer = parse_answer(wire)
assert verify(inst, answer) == (True, "ok")
```

After replenishing the OpenRouter limit, rerun the bare loop here:

```bash
python3 ../../scripts/harden.py gen_1205_0852.py
```

Run structural and placebo modes in separate scratch directories, copy their
script-generated transcripts back, update `G9_ORACLE_RESULTS`, regenerate
`selftest_report.json`, and only then emit with:

```bash
bash scripts/emit.sh 1205.0852
```

## Caveats

This family is easy with any matching library; that is the declared Track B
mechanical route, not a hidden hardness claim. The 0/200,000 density estimate is
only for a uniform prior over permutations after enforcing the obvious
all-different rule; it is not an average-case complexity result. The arithmetic
coordinate structure is synthetic benchmark structure, not a theorem asserting
that real workflows look affine. The adversary panel does not include ILP or SAT,
because exact maximum matching already strictly specializes and solves this
family. Canonicalization is exact for opaque ID permutations and affine changes
of the displayed cyclic coordinates; it does not claim to solve arbitrary
bipartite graph isomorphism. Most importantly, STEP 4 has no scored revised call,
so the family must not be submitted or described as oracle-hardened yet.
