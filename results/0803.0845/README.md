# arXiv:0803.0845 problem generator

Status: the generator and every local gate pass. The required multi-vendor oracle
test is **not complete**: OpenRouter returned HTTP 403 `Key limit exceeded` for
every bare, structural-hint, and placebo call. The harness-authored error records
are retained, but they are not evidence that a model failed the problem. Do not
submit this result until those three runs are repeated with a funded key.

## Profile

| field | value |
|---|---|
| Track | B — no-tool compression |
| Native domain | number theory |
| Object regime | integer lattice |
| Computational core | other (Euclidean remainder/GCD) |
| Certificate form | integer tuple, represented as a two-field JSON object |
| Intended intuition | invariant: a highest forward difference exposes the pseudo-key |
| Domain essentiality | native |
| Reduction | none |

## Problem and provenance

The source is Laurent Evain, [*Knapsack cryptosystems built on NP-hard
instances*](https://arxiv.org/abs/0803.0845). Section 4.1 defines a pseudo-key as
an integer whose public-key remainders have total less than the key and form a
superincreasing sequence up to permutation. Section 4.2 defines Problem 4: all
but one remainder are supplied, the last lies in an interval, and one pseudo-key
must be found. Theorem 22 gives a probabilistic reduction from factoring a
semiprime to that problem.

This module hands the solver exactly those integer division equations. It samples
`q` first, builds a strictly superincreasing remainder sequence, and sets each
known-remainder value to `w_i = q P(i) + r_i`. The integer-valued polynomial
`P(i)` is sampled in the binomial basis with highest coefficient one, so its top
forward difference is exactly one. Therefore the same difference of `w_i-r_i`
is `q`; this composition of identities is the construction certificate, not a
solution computed after generation.

Checking a candidate uses only exact `%`, comparisons, sorting, and addition.
Moreover, every valid candidate divides every `w_i-r_i`. Their GCD is the planted
`q`, and the published bit interval excludes every proper divisor, proving that
there is exactly one valid certificate.

## Why Track B

This distribution is deliberately **not** claimed hard in the Track A sense.
Full multi-integer Euclid finds `gcd(w_i-r_i)=q` in polynomial time. On eight hard
instances it succeeded 8/8, averaging 481 Euclidean divisions; the run used
3,848 divisions total, a schoolbook bit-operation proxy of 1,100,876,215, and
about 0.001 seconds in Python. That is easy with software and out of reach as a
manual calculation on roughly 885-bit integers.

The compact route is different: sort the exact pairs by the displayed remainder,
subtract each remainder, and take the `(n-2)`-nd forward difference. At the hard
preset this is 23 exact arithmetic operations. The family tests recognition of
that invariant. Theorem 22 motivates and defines the native pseudo-key problem;
it is **not** used to pretend this specially structured subdistribution is
factorization-hard.

The paper also identifies regimes avoided here: Section 2.1 makes the hidden
superincreasing sequence itself an efficient decryption trapdoor; the
introduction explains low-density lattice attacks; Section 4.3 studies the
standard LLL ciphertext attack. Those concern message recovery from a knapsack
ciphertext. This benchmark instead uses the extra-remainder Problem 4, whose
honest reference algorithm on this generated distribution is GCD.

## Worked demo (`seed=7`)

The complete rendered instance is:

```text
Find one pseudo-key for this Euclidean-remainder instance.

Definitions and conditions.
For positive integers w and q, the Euclidean remainder w mod q is the unique r with 0 <= r < q and w = qv + r for an integer v.
A finite positive sequence is superincreasing if, after sorting it increasingly, every term is strictly greater than the sum of all earlier terms.
Your pseudo-key q must lie in the half-open interval [128, 256).
For every exact pair (w,r) below, it must satisfy w mod q = r.
For the final public integer, its remainder R must lie in the CLOSED interval [12, 15].
All the exact remainders together with R must be superincreasing, and their total sum must be strictly less than q.
The order in which the exact pairs are printed has no mathematical significance.

Exact (public integer w, required remainder r) pairs:
  3720988 , 3
  3582148 , 1
  3860041 , 7

Final public integer: 4088981
Closed interval for its remainder: [12, 15]

Give your final answer inside <answer></answer> tags as exactly one JSON object with decimal integers q and last_remainder.
Example: <answer>{"q": 173, "last_remainder": 19}</answer>
Output nothing else inside the tags.
```

After ordering by remainder, the adjusted integers are 3,582,147, 3,720,985,
and 3,860,034. Their second difference is
`3,860,034 - 2(3,720,985) + 3,582,147 = 211`; the last remainder is 12.
Thus the answer is `<answer>{"q":211,"last_remainder":12}</answer>`.
`verify(inst, answer)` returns `(True, "ok")`; changing `q` to 210 returns
`(False, "exact remainder mismatch at pair 0")`. A person can solve this demo
on paper with three subtractions and one final division.

## Difficulty presets

| preset | n | q bits | quotient bits | status |
|---|---:|---:|---:|---|
| demo | 4 | 8 | 10 | hand-scale illustration |
| easy | 7 | 40 | 80 | local gates pass; oracle unavailable |
| medium | 10 | 72 | 256 | local gates pass; oracle unavailable |
| hard | 13 | 104 | 768 | configured shipping preset; oracle verdict pending |

Escalation primarily raises quotient height, a fixed-answer-length haystack
axis, and also adds equations and increases the `q` interval. Doubling `n` from
13 to 26 still builds and verifies while the answer stays at two atoms.

## Gate results

| gate | result |
|---|---|
| G1 | 20/20 planted witnesses, JSON round trips, identity checks, and GCD uniqueness checks passed |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic prose/fenced response round-tripped; garbage rejected |
| G4 | 0/200,000 structure-aware guesses; exact density `2^-103` |
| G5 | exactly one shipping certificate; GCD reference solved 8/8 in 3,848 Euclidean divisions |
| G6 | five attacks, each 0/8; reference GCD 8/8 as Track B expects |
| G7 | doubled `n=26` verifies; answer remains two atoms |
| G8 | 60/60 reorder invariance and carried-certificate checks; 20/20 unrelated keys distinct |
| G9(c) | 61 worst-case characters, 16 estimated tokens, 2 atoms, 23 intended operations — within every cap |

The failing attacks were a single-equation scale guess, a 64-candidate greedy
scan from the lower bound, 256 random restarts, eight by-hand Euclid steps, and
the correct finite-difference ansatz applied without first undoing the shuffled
order.

## Oracle loop and G9 arms

| run | preset | valid solved/attempts | harness result |
|---|---|---:|---|
| bare | easy | 0/0 | four redraws, all HTTP 403 key-limit errors; no verdict |
| structural hint | hard | 0/0 | four redraws, all HTTP 403 key-limit errors; no verdict |
| placebo hint | hard | 0/0 | four redraws, all HTTP 403 key-limit errors; no verdict |

Because API errors do not count as attempts, `hinted - placebo` is not yet
defined (stored as diagnostic 0.0 only because both denominators are zero). No
conclusion about the claimed invariant can be drawn until the arms are rerun.
The structural hint names only the forward-difference invariant; it does not give
the subsequent calculation.

## Use

```python
from gen_0803_0845 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
answer = parse_answer('<answer>{"q":211,"last_remainder":12}</answer>')
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after successful oracle reruns, emit examples with:

```bash
bash scripts/emit.sh 0803.0845 20
```

## Caveats

The exact `2^-103` guessing probability is for a uniform prior over the stated
`q` interval with the dependent final remainder recomputed. It does not model an
informed solver: divisibility collapses the problem, and full GCD is intentionally
successful. The wall-clock number demonstrates that this is Track B only; it is
not real-world cryptographic hardness. LLL/BKZ, continued fractions, and external
CAS/solver attacks were not run because GCD already completely solves this
distribution. The finite-difference calculation still involves large integers,
so a failure may mix invariant recognition with exact-arithmetic reliability.
Most importantly, the multi-vendor and three-arm diagnostics are pending due to
external quota, so this directory is reproducible work in progress rather than a
submission-ready result.
