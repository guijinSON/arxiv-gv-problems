# arXiv 2603.28313 — reduced-modulus recovery generator

> Status: the generator and every local gate pass, but the required external
> hardening evidence is **not complete**. OpenRouter returned HTTP 403 “Key limit
> exceeded” for every draw from both configured vendors. The harness-owned error
> records are preserved; this result must not be presented as oracle-hardened until
> the three runs are repeated with a funded key.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite discrete |
| Computational core | linear algebra |
| Certificate form | integer tuple `[q,s1,s2]` |
| Intended intuition | invariant: a common determinantal divisor of augmented modular equations |
| Domain essentiality | native |
| Reduction | none |

## The problem

The source is Hongjun Wu, [“Cryptanalysis of a Lightweight RFID Authentication
Protocol Based on a Variable Matrix Encryption Algorithm”](https://arxiv.org/abs/2603.28313).
Equation (1) defines encryption as `C = M*S mod q`. Section V-B, Equations
(21)–(24), observes ciphertexts of the same long-term two-coordinate secret under
a recovered matrix `A` and its transpose. An instance gives exactly those two
matrices and ciphertext vectors, a half-open candidate interval for the unknown
reduced modulus `q`, and bounds on `S`. The solver returns `[q,s1,s2]`.

Checking is cheap and exact: range-check the three integers, compute both 2-by-2
matrix-vector products, reduce modulo `q`, and compare four coordinates. The
verifier accepts any satisfying triple and never reads the planted answer.

## Why Track B

This is explicitly not a Track A claim. Section VI-C says the paper’s mechanical
method tests up to `2^32` candidate reduced moduli and estimates about `2^39`
small modular consistency checks. In this generator the same Section V-B method
scans the published `n`-value interval, solves one 2-by-2 congruence for each
candidate, and checks the transpose equations. At the configured hard preset it
solved 8/8 instances after 4,268,172 candidate trials in 11.102 seconds total
(533,521.5 trials and 1.388 seconds per instance on this host).

There is a compressed route. Append each ciphertext coordinate to its matrix row,
forming four integer rows of length three. Every 3-by-3 minor is divisible by the
hidden modulus. The generator accepts a draw only when the gcd of the four minors
is exactly `q`; one ordinary modular 2-by-2 solve then recovers `S`. The measured
route used 138–161 counted exact operations. The task tests noticing that invariant;
blindly executing the candidate scan is out of reach in a no-tool context.

The easy regimes are the paper’s own warning: the update tables have only 20
DBLTKM states, four SUEO orders, and eight moduli (Sections II-B and III), making
state reuse plausible. Matrix-column recovery itself is also easy once related
nonces are spotted (Section IV-A). This family therefore isolates the later
reduced-modulus consistency step and labels it Track B honestly.

## Worked demo

For `make_instance(seed=4, n=7, q_min=9, secret_bound=5)`, the complete rendered
data are:

```text
RECOVER A REDUCED RFID SESSION MODULUS

All arithmetic below is over the ordinary integers followed by modular
reduction.  For an integer q>1, x mod q means the unique remainder in
{0,1,...,q-1}.

There is an unknown modulus q and one reused secret column vector
S=[s1,s2]^T.  They obey the half-open bounds
9 <= q < 16
0 <= s1,s2 < 5

Each session below gives a 2 by 2 integer matrix M and a ciphertext
column C.  It is promised that C = M*S mod q, coordinate by coordinate.
The two displayed matrices are transposes of one another, as in the
cross-session A/A^T equations of the protocol.  The same q and S are
used in both sessions.  Exactly one triple [q,s1,s2] within the stated
bounds satisfies every displayed equation.

SESSIONS (entries are decimal integers; session order is irrelevant):
Session 0:
  M = [[5, 2],
       [3, 5]]
  C = [6, 3]
Session 1:
  M = [[5, 3],
       [2, 5]]
  C = [7, 0]

Return the unique triple as a JSON list [q,s1,s2].  It must contain
exactly three decimal integers in that order; intervals are half-open
as stated above, and no alternative residue representatives are allowed.

Give your final answer inside <answer></answer> tags in that exact JSON format.
Example: <answer>[13,2,4]</answer>
Output nothing else inside the tags.
```

The four augmented minors have absolute values `22, 33, 33, 22`, whose gcd is
`11`. Solving modulo 11 gives `<answer>[11,3,1]</answer>`. Thus
`verify(inst, [11,3,1]) == (True, "ok")`. Swapping the two secret coordinates
gives `(False, "ciphertext mismatch at session 0, coordinate 0: got 0, expected
6")`. This demo is genuinely hand-solvable; it has only 175 bounded candidates,
and the determinant shortcut uses small integers.

## Difficulty presets

| Preset | Candidate values `n` | `q_min` | Secret bound | Status |
|---|---:|---:|---:|---|
| demo | 7 | 9 | 5 | paper-scale illustration |
| easy | 65,536 | 1,000,000 | 65,536 | first oracle rung; oracle unavailable |
| medium | 262,144 | 2,147,483,648 | 1,048,576 | not reached |
| hard | 1,048,576 | 140,737,488,355,328 | 2,147,483,648 | configured shipping preset; local gates pass |

`escalate()` first widens the candidate interval and raises arithmetic precision,
then continues widening the interval. The witness always remains three integers.

## Local gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 20 planted/compact-recovery/JSON checks |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose and Markdown round-trip; garbage rejected |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `1/4,835,703,278,458,516,698,824,704` |
| G5 | pass | random-modulus baseline: 2,048 trials, 0 successes, 0.0063 s; demo exact count 1/175 |
| G6 | pass | four attacks at 0/8; reference scan 8/8 |
| G7 | pass | doubled `n` doubles the search language; build and witness still verify |
| G8 | pass | 60 invariance and 60 certificate-preservation checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 38 characters, 10 estimated tokens, 3 atoms, at most 161 operations |

The four failing G6 attacks were: guess one above the largest public value, scan
the first 256 interval values, try 256 random candidate moduli with an exact first
system solve, and assume the congruence has no wraparound. The successful reference
scan is reported separately, as Track B requires.

## Oracle loop and G9 arms

No valid oracle attempt occurred. Errors do not count as failures, and the harness
correctly stopped instead of manufacturing a hardness claim.

| Run | Preset | Harness draws | Valid attempts | Outcome |
|---|---|---:|---:|---|
| bare | easy | 4 | 0 | both configured vendors returned HTTP 403 key-limit errors |
| structural hint | hard only | 4 | 0 | HTTP 403 key-limit errors |
| placebo hint | hard only | 4 | 0 | HTTP 403 key-limit errors |

Consequently `hinted − placebo` is undefined and no conclusion about hint response
is justified. The intended structural hint only names the common determinantal
divisor; it does not state the recovery procedure. The transcript files contain
the harness-generated error records so the infrastructure failure is auditable.

## Use

```python
from gen_2603_28313 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>" + str(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, after replacing the failed oracle evidence:

```bash
python3 results/2603.28313/gen_2603_28313.py > results/2603.28313/selftest_report.json
bash scripts/emit.sh 2603.28313 20 hard
```

## Caveats

- The construction deliberately keeps only transcripts whose augmented minors
  have gcd exactly `q`. This is a certified benchmark distribution, not a claim
  that every real protocol capture has that property. Noise or a larger gcd can
  defeat or make ambiguous the shortcut.
- It isolates Section V-B. It does not simulate collecting repeated states,
  identifying DBLTKM/SUEO states, reconstructing all eight 64-bit moduli, or
  performing a full impersonation.
- The exact guess density is with respect to the declared uniform prior over the
  candidate interval and bounded secrets. It says nothing about structural attacks;
  those are why G6 and the determinantal analysis are separate.
- No lattice reduction, SMT solver, or specialized hidden-modulus package was run.
  The determinant/gcd route is itself a stronger computer algorithm than the
  paper’s interval scan; that is the intended Track B compression, not omitted
  evidence for Track A.
- Fifteen-digit entries keep the compact route below 300 arithmetic operations but
  still make hand arithmetic demanding. A future oracle run is needed to tell
  whether failures come from finding the invariant or executing the arithmetic.
- Most importantly, the required cross-vendor bare/hinted/placebo measurements are
  blocked by the exhausted OpenRouter key. Until rerun, this directory is a locally
  verified candidate generator, not a completed corpus submission.
