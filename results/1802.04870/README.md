# Rejected: permuted-cyclic RAAG secret sharing (arXiv:1802.04870)

> Status: the preserved generator passes every local gate, but it **fails H on
> Track B**. A fresh script-owned bare oracle run defeated every named preset and
> all supported escalations, ending with `verdict: "too_easy"`. It is archived as
> `rejected_gen_1802_04870.py` and must not be emitted. See `REJECTED.md`.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | graph |
| Certificate form | exact rational `[numerator, denominator]` |
| Intended intuition | invariant: Feistel relabelling preserves cyclic components; consecutive-node interpolation recovers the secret |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed: Section 4, Theorem 4.1 and Proposition 4.2 |

## What the family is

The source is Flores, Kahrobaei, and Koberda,
[*Algorithmic problems in right-angled Artin groups: complexity and
applications*](https://arxiv.org/abs/1802.04870). A right-angled Artin group
(RAAG) has one generator per vertex of a graph, with commutation exactly along
the graph edges. Section 6.3.1 gives each participant a connected graph: if its
maximal join decomposition has `m_i` factors, a monic degree-`d` polynomial
satisfies `f(i)=m_i`, and the shared secret is `f(0)`.

Each generated presentation describes its noncommutation graph exactly as
permuted cyclic edges `{P(z),P(z+s)}`. The map `P` is an explicitly keyed Feistel
permutation. The generator first samples every `m_i`, sets `N=2^n` and
`s=m_i*a` for odd `a`, then samples `P`; hence the complement has exactly
`gcd(N,s)=m_i` components. This is inverse generation followed by a
structure-preserving relabelling, not solution of a generated instance. Because
`m_i>=4`, each RAAG defining graph is connected, as Section 6.3.1 requires.

The checker validates the presentation syntax, reads each component count by
exact integer gcd, and evaluates the exact interpolation identity. It never
reads `inst["answer"]`, and accepts any correctly encoded rational witness.

## Why this is Track B

Track A would be false. Proposition 4.2 explicitly solves maximal join
decomposition in polynomial time by forming the complement and merging the
endpoints of every complement edge. Section 2 also records linear-time word and
conjugacy algorithms and polynomial-time shortlex/geodesic algorithms; Section
3 gives a quasi-polynomial automorphism consequence. Those are easy regimes,
not hardness claims.

The included reference implementation runs Proposition 4.2 literally after
evaluating every Feistel-labelled edge. At the locally audited `easy` preset, seed
271828, it performs 327,680 edge iterations and 2,621,440 Feistel-round
evaluations in 0.6--1.2 local seconds across repeated audits. Across the
eight-seed G6 audit it solves 8/8 and performs 23,592,960 counted operations;
the latest exact wall time is recorded in `selftest_report.json`.

The compact route notices that Feistel only renames vertices. Since `N` is a
power of two and the hidden step multiplier is odd, `gcd(N,s)` is the lowest set
bit of `s`. The remaining value is

`f(0) = d! + sum_{i=1}^d (-1)^(i-1) C(d,i) m_i`

for the even degrees used here. The full shipping audit needs at most 127 exact
operations. The intended challenge was finding both invariants; millions of
mechanical operations are easy for software but impossible in the no-tool
context. The hardening run showed that this pool can nevertheless find and
execute the compact route reliably, so the proposed Track B claim does not hold.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders this complete instance:

```text
Recover the exact secret in a right-angled Artin group sharing instance.

A right-angled Artin group A(Gamma) has one generator for each vertex of
a finite simple graph Gamma.  Two distinct generators commute exactly when
their vertices are adjacent.  A join Gamma=Gamma_1*...*Gamma_r partitions
the vertices into nonempty parts so every pair from different parts is
adjacent.  A maximal join decomposition is one whose parts cannot be split
again; its r parts give the maximal direct-product factors of A(Gamma).

Below, every presentation has N=2^w generators x_(i,0),...,x_(i,N-1).
Each line supplies i, s, and a comma-separated list of Feistel keys.
To define its map P, put h=w/2 and split z=L*2^h+R with h-bit L,R.
For each key k from left to right, set
  M = (R*(2*k+1)+k) mod 2^h,
  F = M XOR rotl_h(R,1),  and  (L,R) = (R,L XOR F).
Here XOR is bitwise exclusive-or and rotl_h rotates an h-bit word left
by one bit.  After all keys have been processed, P(z)=L*2^h+R.
Distinct generators x_(i,a),x_(i,b) fail to commute exactly when there
is a z in {0,...,N-1} with {a,b}={P(z),P((z+s) mod N)}; every other
distinct pair commutes.  Thus each line is a complete exact RAAG
presentation, not a sample.  Subscripts are zero-based and lines may
appear in any order.

There is a unique polynomial f of degree exactly 4 with rational
coefficients and leading coefficient 1 (this is what 'monic' means),
such that f(i)=m_i for i=1,...,d, where m_i is the number of maximal
direct-product factors of presentation i and d is the displayed degree.
Find the secret f(0).  Intervals and bounds below are inclusive.

degree d = 4
label bit width w = 8 (so N = 256)
Feistel rounds per presentation = 2
answer numerator bound B = 504
presentation lines (i s keys):
  3 96 4,9
  1 160 15,12
  4 68 3,8
  2 160 15,11

Return one reduced exact rational num/den with gcd(|num|,den)=1,
den>0, den exactly 1, and -B <= num <= B.  The JSON certificate stored
by the generator is [num,den], but the answer block uses num/den text.

Give your final answer inside <answer></answer> tags, as num/den.
Example: <answer>-37/1</answer>
Output nothing else inside the tags.
```

The lowest set bits give `(m_1,m_2,m_3,m_4)=(32,32,32,4)`, so the answer
is `84/1`. This smallest setting is genuinely hand-solvable: the Feistel
permutations need not be evaluated, and four small interpolation terms suffice.

```python
>>> verify(inst, [84, 1])
(True, 'ok')
>>> verify(inst, [85, 1])
(False, 'incorrect polynomial secret')
```

## Difficulty presets

| Preset | Vertices per RAAG | Degree / shares | Feistel rounds | Varying counts | Status |
|---|---:|---:|---:|---:|---|
| demo | 256 | 4 | 2 | 1 | hand example; never ships |
| easy | 16,384 | 20 | 4 | 20 | defeated 3/3 |
| medium | 65,536 | 24 | 6 | 24 | defeated 2/3 |
| hard | 262,144 | 28 | 8 | 28 | defeated 2/3 |

`escalate()` raises both the label width and Feistel-round count while preserving
the two-atom answer. The revised, fully varying construction was still solved at
all three escalations; the final `(n,degree,rounds)=(24,28,14)` level was defeated
3/3. The hardening script therefore rejected the family as `too_easy`.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; all presets and three seeds; JSON round-trip |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged rational recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 samples; exact probability `1/4,865,804,016,420,388,801` (`2.06e-19`) |
| G5 | pass | exactly one shipping answer; demo count 1/1009; strongest failing attack uses 10 shares; reference uses 327,680 edges (exact time in report) |
| G6 | pass | four attacks each 0/8; reference union-find 8/8 as expected; compact route 8/8 |
| G7 | pass | two extra label bits raise counted reference work from 2,949,120 to 17,039,360 operations; answer remains two atoms |
| G8 | pass | 80/80 reordering, unit, reflection, and rekey tests invariant and real; 20/20 unrelated keys distinct |
| G9(c) | pass | 23 characters, 2 atoms, at most 127 exact operations |

The four failing attacks are: infer the answer from the most extreme displayed
step; use only the modal factor count; try 256 uniform bounded rationals; and
perform correct interpolation using only the first half of the shares.

## Oracle loop and G9 diagnostics

| Bare level | Solved / attempts | Result |
|---|---:|---|
| easy `(14,20,4)` | 3/3 | defeated |
| medium `(16,24,6)` | 2/3 | defeated |
| hard `(18,28,8)` | 2/3 | defeated |
| escalated `(20,28,10)` | 1/3 | defeated |
| escalated `(22,28,12)` | 1/3 | defeated |
| escalated `(24,28,14)` | 3/3 | defeated; terminal |

The bare transcript has 18 scored calls, 12 verified solves, and no API errors.
The script-owned verdict is `too_easy`. Earlier hinted and placebo scratch runs
contain only quota errors, so they supply no three-arm estimate and play no role
in the rejection. G9(c) still passes: 23 answer characters, two atoms, and at
most 127 operations at the locally audited preset (175 at the final escalation).

## Archival use

```python
from rejected_gen_1802_04870 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=0, **DIFFICULTY["demo"])
question = render(inst)
candidate = parse_answer("Reasoning omitted. <answer>84/1</answer>")
assert verify(inst, candidate) == (True, "ok")
```

The module uses only the standard library; `gvlib` is unnecessary because all
verification is exact integer arithmetic. Do not run `emit.sh` for this rejected
family.

## Caveats

- This is emphatically Track B, not a distributional-hardness or cryptographic-
  security claim. A software solver that recognizes the relabelling and cyclic
  structure immediately gets the same compact route.
- The presentations are succinct rules rather than the paper's explicit edge
  lists or adjacency matrices. The RAAGs and join factors are native, but this
  encoding deliberately creates the measured compression gap.
- G4 is uniform over the exact bounded rational language stated to the solver.
  It does not model a generator-aware prior near `d!`; the modal, extreme-step,
  and truncated-interpolation attacks separately probe simple such priors.
- No external CAS, symbolic interpolation package, or more sophisticated
  sequence-recognition attack was tested. Proposition 4.2 union-find is the
  required successful reference algorithm, not a failing adversary on Track B.
- The decisive caveat is empirical: 12/18 bare oracle calls solved, including all
  three calls at the largest supported level. Increasing only the implicit graph
  size does not hide the lowest-set-bit and interpolation invariants once seen.
