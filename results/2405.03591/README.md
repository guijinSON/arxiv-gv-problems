# Telescoping spherical equations (arXiv:2405.03591)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | telescoping |
| Certificate form | exact symbolic sparse group assignment |
| Intended intuition | invariant — prefix-weighted coefficient vectors telescope |
| Domain essentiality | native; no reduction |

## What the family is

The source is Alexander Ushakov, [*Constrained inhomogeneous spherical equations: average-case hardness*](https://arxiv.org/abs/2405.03591). An instance is a spherical equation in the paper's finite metabelian group

`G_(p,d) = Z_p^d ⋊ Z_p*`, with `(x,a)(y,b)=(x+ay,ab)`.

It gives `m` ordered group coefficients by an exact formula and asks for a one-support assignment of conjugators: all `z_i` are the identity except one `z_j=(lambda*v,1)`. The answer is the exact symbolic object `{"index":j,"scale":lambda}`. `verify` substitutes it into Lemma 4.1's weighted vector congruence and compares the residual to zero modulo `p`; it never reads the planted answer. Literal group multiplication is independently checked on every demo seed.

Local construction and verification are fully audited. The required external hardness claim is **not yet validated**: OpenRouter rejected every hardening call with HTTP 403 `Key limit exceeded (total limit)`. The script-owned error transcript is retained, and no API error is counted as a model failure.

## Why this is Track B

The paper itself rules out Track A for this distribution. Section 4.1 proves that an unconstrained equation with any coefficient scalar `beta_i != 1` has an explicit polynomial-time sparse solution; such equations are strongly generically easy. Section 5's average-case Theorem applies instead to uniformly random constrained `CISE_{1,2}` or `CISE_{1,2,3}` instances satisfying `n log(p) < m < p/(2n^4)`. This generator is structured and unconstrained, so it does not borrow that average-case claim.

The successful reference algorithm is the Section 4.1 prefix-product and weighted-coefficient sum. Even after exploiting the displayed common vector direction, it expands all 262,144 coefficients: the final audit measured 1,310,761 modular operations and about 1.20 seconds on average over eight seeds (`O(m)` here, `O(md)` on explicitly expanded vectors). The compact route notices

`B_i * c_i.vector = (t-1)t^(i-1)v`,

so the entire sum is `(t^m-1)v`. Binary modular exponentiation and one Euclidean inverse measured at most 70 operations over the audited seeds; the conservative cap accounting is 168. That is the intended no-tool compression gap.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders in full as:

```text
Find a sparse solution of a spherical equation in a finite semidirect-product group.

All residues below are least nonnegative integers modulo the prime
p=101.  Let G be the set of pairs (x,a), where x is a length-2 vector over
Z_p and a is a nonzero residue modulo p.  Define the group operation by

    (x,a)*(y,b) = (x + a*y mod p, a*b mod p).

Its identity is (0,1), where 0 is the all-zero vector.  Vector addition and
scalar multiplication are coordinatewise modulo p.  Inverses and powers of
nonzero residues are also taken modulo p.

This instance has m=4 ordered coefficients c_1,...,c_m.  Put

    rho = 99,    rho_inverse = 50,
    t = 55,
    v = [6 34].

For each one-based index i=1,...,m, define beta_i and the vector part of c_i by

    beta_i = rho                  if i is odd,
             rho_inverse          if i is even;

    a_i = (t-1)*t^(i-1)           if i is odd,
          rho_inverse*(t-1)*t^(i-1) if i is even;

    c_i = (a_i*v mod p, beta_i).

The order of the m factors is significant.  Find a one-support assignment to
the variables z_1,...,z_m such that

    z_1^(-1)*c_1*z_1 * z_2^(-1)*c_2*z_2 * ... * z_m^(-1)*c_m*z_m = (0,1).

Your assignment must have the following compressed form: choose one index j
with 1 <= j <= m and one scale lambda with 0 <= lambda < p, set
z_j=(lambda*v mod p,1), and set every z_i=(0,1) for i != j.  Any valid j is
accepted.  Indices are one-based, repetitions are not relevant because exactly
one index is returned, and both interval bounds above are inclusive.

Return a JSON object with exactly the integer fields "index" and "scale".
Give your final answer inside <answer></answer> tags, as that JSON object.
Example: <answer>{"index":1,"scale":0}</answer>
Output nothing else inside the tags.
```

The planted answer is `{"index":4,"scale":93}`. It is genuinely hand-solvable: `55^4 = 25 (mod 101)`, the even-index denominator is `99*(50-1)=3 (mod 101)`, and `-24/3=93 (mod 101)`.

```python
>>> verify(inst, {"index": 4, "scale": 93})
(True, "ok")
>>> verify(inst, {"index": 4, "scale": 94})
(False, "spherical group equation is not satisfied")
```

## Difficulty presets

| Preset | `m` | dimension | prime bits | Answer atoms | Status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 2 | 7 | 2 | hand-solvable illustration |
| easy | 262,144 | 16 | 61 | 2 | intended shipping preset; external run blocked |
| medium | 524,288 | 24 | 61 | 2 | available |
| hard | 1,048,576 | 32 | 61 | 2 | available |

No preset has been rejected. `escalate` continues doubling the coefficient haystack while the two-field answer remains fixed.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; 3/3 literal demo group products; both primes rechecked |
| G2 | pass | drop, swap, duplicate, empty, and range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON round-trip from surrounding prose and a markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `1/(2^61-1)` |
| G5 | pass | 262,144 valid answers among 604,462,909,807,314,587,090,944 candidates; reference and attack costs recorded |
| G6 | pass | four attacks each 0/8; disclosed reference and compact algorithms each 8/8 |
| G7 | pass | doubled `m=524,288` builds and verifies with the answer still two atoms |
| G8 | pass | 140/140 coordinate relabellings invariant, 140/140 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 43 actual / 44 worst-case answer characters, 2 atoms, 168 conservative intended-route operations |

## Oracle loop

No scored oracle attempt exists yet. The harness selected the `easy` preset, but all four redraws failed before inference:

| Preset | Seed | Model | Result |
|---|---:|---|---|
| easy | 1,491,937,583 | xAI Grok 4.6 | HTTP 403 key limit |
| easy | 835,726,881 | xAI Grok 4.6 | HTTP 403 key limit |
| easy | 1,402,481,239 | OpenAI GPT-5.6 Terra | HTTP 403 key limit |
| easy | 1,605,078,455 | xAI Grok 4.6 | HTTP 403 key limit; harness aborted |

This is infrastructure evidence only, not a hardness result. Re-run the bare arm after restoring OpenRouter quota; do not submit the current transcript as a hardened verdict.

## G9 arms

| Arm | Solved / valid attempts | Status |
|---|---:|---|
| bare | 0 / 0 | blocked before inference |
| structural hint | 0 / 0 | attempted in its scratch run; blocked before inference |
| placebo hint | 0 / 0 | attempted in its scratch run; blocked before inference |

Both script-owned G9 error transcripts are retained. Hinted minus placebo is unavailable (`null` because neither arm has a scored attempt), so no conclusion about the invariant can be drawn. The answer is 43 characters (about 11 tokens), and the intended route is bounded at 168 exact operations, with 70 observed in the eight-seed compact-route audit.

## Use

```python
from gen_2405_03591 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer('<answer>{"index":1,"scale":0}</answer>')
ok, reason = verify(inst, candidate)
```

From the repository root, after a successful hardening run, emit instances with:

```bash
bash scripts/emit.sh 2405.03591 20 easy
```

## Caveats

- This is emphatically Track B. Python's modular arithmetic solves every generated instance quickly; it is not evidence for the paper's conditional average-case hardness theorem or for lattice hardness.
- The coefficients are given parametrically rather than expanded into millions of field entries. This preserves the paper's native group equation while deliberately making the representation itself carry the telescoping structure.
- G4 samples the exact stated compressed language: a uniform index and uniform field scale. Its exact `1/p` density incorporates the freely visible fact that the conjugator is a multiple of `v`; it says nothing about informed symbolic guesses, which G6 probes only partially.
- The four failing attacks cover endpoint magnitude, a linearized greedy sum, sixteen small symbolic scales, and 256 uniform restarts. Lattice reduction, external CAS simplification, and alternative symbolic summation systems were not run. The disclosed Section 4.1 reference is expected to succeed and is not counted as a failing attack.
- `canonical_key` is complete for changing the nonzero coordinate direction by `GL(d,p)`. It intentionally does not treat arbitrary coefficient reordering as a symmetry because the group is noncommutative and the factor order is part of the instance.
- The structural hint has not been tested, and the required multi-vendor Step 4 evidence is absent until OpenRouter quota is restored. This is the main remaining blocker.
