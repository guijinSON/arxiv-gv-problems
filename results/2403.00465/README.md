# Succinct unweighted Polyamorous Scheduling

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | combinatorics / finite field |
| Core / certificate | graph / exact symbolic affine-factor schedule |
| Intuition | change of variables: two coefficient moments expose an arithmetic progression |
| Domain essentiality | licensed reduction |
| Paper result | Section 5, Proposition 5.1 |
| Shipping preset | **hard**: `n=56`, `p=262139` |

## Problem and trust model

The source is Gąsieniec, Smith, and Wild, [*Polyamorous
Scheduling*](https://arxiv.org/abs/2403.00465). An instance is an unweighted
bipartite polycule on people `L_x,R_y` over `F_p`; a displayed polynomial
defines a relationship precisely when `F(x,y)=0`. The solver returns three
field elements `a,b,s` asserting

`F(x,y) = product_(j=0..n-1) (y-a*x-(b+j*s))`.

Each factor is a perfect matching, so the factor number is its day in a
period-`n` schedule. Exact coefficient expansion checks the candidate, and the
degree-`n` core proves heat `n` is optimal. The generator samples `a,b,s`
first, multiplies the factors, and never factors its generated polynomial.
Three small disjoint cycles receive a fixed canonical schedule and provide
structural diversity without identifying a core matching.

This is paper-licensed rather than a claim that the finite-field encoding
appears in the paper: Proposition 5.1 proves that unweighted heat-`h`
scheduling is exactly `h`-edge-colouring. The statement still hands the solver
the paper's relationship graph and a periodic matching schedule, albeit by an
exact succinct predicate.

## Why Track B

Track A would be false. Section 2 gives a polynomial `Delta+1` edge-colouring;
Section 5 identifies the exact unweighted problem with chromatic index; and
regular bipartite graphs have polynomial exact edge-colouring. Theorems 1.5
and 1.6 additionally give polynomial approximation schedules. Section 4's
exponential configuration graph concerns general DPS and is not a hardness
claim for this distribution.

The measured reference algorithm evaluates `F(0,z)` at every `z in F_p`, then
reconstructs its arithmetic-progression roots. It is `O(p*n+n^3)`, succeeds
8/8, and at shipping used at most **29,984,225 exact field operations** and
**1.452 s**. The compact route obtains the common slope from the top homogeneous
layer and the step/start from the first two root moments. It succeeds 8/8 in
**112 counted operations**. The benchmark asks whether a no-tool solver sees
that compression instead of executing the mechanical scan.

## Worked demo

`make_instance(n=4, p=11, seed=0)` is hand-solvable. It renders:

```text
SUCCINCT UNWEIGHTED POLYAMOROUS SCHEDULING

All arithmetic below is in the prime field F_11; residues are integers 0,...,10.
There are two sets of people L_x and R_y, one person for each x,y in F_11.
They form an undirected bipartite relationship graph: L_x is related to R_y
exactly when F(x,y)=0. There are no other relationships in this core.
Every relationship has unit desire growth per day.

The polynomial F is given by total-degree rows.  In a row labelled k,
entry i (0-indexed) is the coefficient of x^i*y^(k-i); omitted
monomials have coefficient 0.  Row and entry order do not otherwise matter:
  degree 0: 10
  degree 4: 1,2,7,6,9
  degree 1: 7,9
  degree 2: 8,8,2
  degree 3: 2,3,7,3

The full graph also has three disjoint cycle components of lengths 3, 4, 5.
For the compact certificate below, those cycles use their canonical schedule:
an even cycle alternates days 0 and 1; an odd cycle alternates days 0 and 1
on all but its closing edge, which uses day 2. Cycle vertices and edges are
indexed consecutively from 0 solely for this convention.

Find slope a != 0, start b, and step s != 0 in F_11 such that
  F(x,y) = product over j=0,...,3 of (y - a*x - (b+j*s)).
The 4 values b+j*s must be distinct.  Your object denotes this complete
period-4 schedule: on day j, schedule every core relationship satisfying
y=a*x+b+j*s, together with the canonical cycle edges assigned to day j.
Days and coefficient exponents are 0-indexed; the period is cyclic; order
within a day's matching is irrelevant.  A valid factorization proves the
schedule has heat 4, which is optimal because every core vertex has degree 4.

Output one JSON object with exactly the integer keys slope, start, and step.
Each value must be its canonical residue in 0,...,10; slope and step cannot be 0.
Give your final answer inside <answer></answer> tags.
Example: <answer>{"slope":2,"start":3,"step":4}</answer>
Output nothing else inside the tags.
```

Its answer is `<answer>{"slope":5,"start":8,"step":9}</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; changing the slope to
11 returns `(False, "slope must lie in 1..10")`. A person can solve the demo by
using the two leading coefficient rows and checking four factors.

## Difficulty and hardening

The bare harness solved the first three attempted levels, so the ladder was
slid upward and the first held escalation became `hard`.

| Current preset | `n` | `p` | Bare evidence |
|---|---:|---:|---|
| demo | 4 | 11 | hand illustration; skipped by harness |
| easy | 32 | 16363 | 3/3 solved when named `medium` |
| medium | 48 | 65519 | 3/3 solved when named `hard` |
| **hard** | **56** | **262139** | **0/3 solved; ships** |

The dropped `n=18,p=4091` rung was also solved 3/3. At shipping, one bare
oracle exhausted its 32k completion budget; the other two returned parseable
but incorrect first/second moments. The script-owned `.meta.json` records the
`hardened` verdict. The current harness used its configured two-vendor pool
(OpenAI and Google), with three independently seeded attempts per level.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted answers verify; all are JSON-native |
| G2 | empty, dropped, out-of-range, swapped, and duplicated fields rejected with five distinct reasons |
| G3 | fenced model-style prose round-trips; garbage returns `None` |
| G4 | 0/200,000 uniform bounded guesses; exact density `2 / 18,013,230,303,543,116` |
| G5 | demo count 2/1,100; shipping reference 29,984,225 operations, 1.452 s max |
| G6 | four attacks each 0/8; reference and compact routes each 8/8 |
| G7 | doubled `n=112` builds, grows 1,653 to 6,441 coefficients, and verifies with the same 3-field answer |
| G8 | 60/60 invariance and carried-witness checks; 20/20 unrelated structural keys distinct |
| G9(c) | 42 answer characters, 11 estimated tokens, 3 atoms, 112 intended operations |

The G6 failures are largest-coefficient outlier guessing, low-degree greedy
guessing, 256 uniform restarts, and the by-hand unit-step ansatz.

## G9 diagnostics

| Arm at shipping | Solved / scored | API errors |
|---|---:|---:|
| bare | 0 / 3 | 0 |
| structural hint | 1 / 3 | 0 |
| placebo hint | 1 / 2 | 4 |

The placebo arm's third scored attempt could not be obtained because the
OpenRouter key reached its total limit. Therefore `hinted - placebo` is
recorded as `null`, not inferred from unequal denominators. The observed hint
rate shows that naming the moment invariant can make a seed solvable, but the
incomplete placebo control prevents attributing that effect to structural
information rather than prompt variation. G9(a/b) are diagnostic, so this does
not override the bare `hardened` verdict or G9(c).

## Use

```python
from gen_2403_00465 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2403.00465 20
```

## Caveats

- This is a no-tool compression benchmark, not evidence of computational or
  average-case scheduling hardness. A computer solves every shipping instance.
- G4 samples uniform valid-shape parameter triples. It measures uniform density,
  not the informed prior that exploits coefficient moments.
- The reference scan is pseudo-polynomial in `p`; generic finite-field
  factorisation and explicit bipartite matching were identified but not run.
- The core graphs for fixed `n,p` are isomorphic under affine coordinate
  changes. Seed diversity comes from the cycle-component length multiset;
  those decorations do not increase core difficulty. The key is complete for
  this constructed family, not a general graph-isomorphism algorithm.
- A polynomial predicate is a succinct representation of a very large graph
  (`2p` core people and `np` relationships). The exact schedule semantics are
  native, but this representation is a paper-licensed benchmark construction,
  not a representation studied by the authors.
- The placebo G9 transcript is incomplete due quota. Re-run that isolated arm
  with a funded key before treating the three-arm comparison as an estimate.
