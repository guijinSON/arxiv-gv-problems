# Structured exact LPN recovery

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field (`F_2`) |
| Computational core | exact linear algebra / maximum-likelihood LPN recovery |
| Certificate | integer tuple: support of a nonzero binary secret |
| Intended intuition | change of variables: recognize a permuted quadratic Boolean evaluation table |
| Domain essentiality | native; no reduction |

This module turns Carrier, Debris-Alazard, Meyer-Hilfiger, and Tillich’s
[*Statistical Decoding 2.0: Reducing Decoding to LPN*](https://arxiv.org/abs/2208.02201)
into exact witness problems. The solver receives labeled samples `(x,a,b)` over
`F_2` and an exact noise weight, and must return any nonzero secret `z` for which
exactly that many equations `b=<z,a>` disagree. Verification reconstructs all
predicted bits with integer xor and compares one exact Hamming weight. The
generator samples `z` first, builds the responses around it, and never recovers
the answer by solving its own instance.

## Why Track B

Problem 1.2 defines LPN, while Sections 3.1–3.2 turn restricted dual checks into
LPN samples and prove that the Walsh coefficient at `z` is `N-2d`, where `d` is
the response distance. Thus maximum likelihood is a Walsh–Hadamard transform in
`O(s 2^s)`. Shipping has secret dimension `s=21`; the measured transform used
44,040,192 additions plus 4,194,301 comparisons—48,234,493 exact operations in
2.313 seconds. A stronger bit-packed exact scan succeeded on 8/8 instances,
visiting a median 1,435,390 candidates (4,306,170 word operations) in 0.330
seconds. It is easy for a
computer and not executable unaided in context—the defining Track B gap.

The compact route is different. Feature coordinates secretly permute all
nonconstant degree-at-most-two Boolean monomials in six variables. Singleton
labels isolate the six linear features. For every pair `{i,j}`, xor its feature
row with the two singleton rows to isolate one quadratic feature; the same xor
of response bits gives its coefficient. All noise labels have Hamming weight at
least three, so those equations are exact. Fifteen pairs times four xors is a
verified 60-operation route.

The sample code is a zero-constant subcode of `RM(2,m)`, whose minimum distance
is at least `2^(m-2)`. Noise is `2^(m-3)-1`, strictly below half that distance,
so the planted secret is unique. Section 1.1’s generic easy cases were also
kept out of the Track A draft: decoding becomes polynomial in its high-noise
band and additional solutions proliferate above the Gilbert–Varshamov distance.
Here the relevant easy cases are zero noise with an exposed basis, or revealing
the hidden monomial coordinate map; only the demo deliberately uses zero noise.

## Worked demo

`make_instance(n=8, noise_weight=0, seed=11)` renders this complete statement:

```text
Exact finite Learning Parity with Noise (LPN)

All arithmetic is over the binary field F_2: addition is xor and <z,a> is the
parity (0 or 1) of the coordinates where binary vectors z and a both have a 1.

There are 8 labeled samples. Each line has a public 3-bit label x,
a feature vector a in F_2^6 written as exactly 2
hexadecimal digits, and one response bit b. In a, feature 0 is the
least-significant bit of the hexadecimal integer, feature 1 is the next bit,
and so on. The x label is exact public instance data; line order has no
mathematical significance.

Find the unique nonzero secret z in F_2^6 for which
exactly 0 displayed equations b=<z,a> disagree. Output the
support of z: precisely the feature indices whose secret coefficient is 1.

The support must be a nonempty JSON list of distinct integers, strictly
increasing, with every index between 0 and 5
inclusive. Indices are zero-based, repeats are forbidden, and all data and
comparisons are exact.

number of samples: 8
secret dimension: 6
required number of disagreements: 0
sample table (x_binary  a_hex  b):
011  26  1
010  04  1
110  0d  0
000  00  0
001  02  0
100  01  0
101  13  0
111  3f  0

Give your final answer inside <answer></answer> tags as one nonempty JSON list
of strictly increasing feature indices.
Example format: <answer>[0, 3]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[2, 3]</answer>`. `verify` returns `(True, "ok")`.
Dropping feature 3 gives `[2]` and returns
`(False, "candidate disagrees with 2 samples, expected exactly 0")`. A person
can solve this smallest setting on paper: there are only six secret features,
and its singleton/pair identities require 12 xors.

## Difficulty presets

| preset | samples `n` | label bits `m` | secret bits `s` | noise | legal-space bits | rendered chars (seed 0) | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 8 | 3 | 6 | 0 | 5.977 | 1,364 | hand-scale illustration |
| easy | 64 | 6 | 21 | 7 | 21.000 | 2,434 | **shipping**; all local gates pass |
| medium | 128 | 7 | 28 | 15 | 28.000 | 3,846 | reserve rung |
| hard | 256 | 8 | 36 | 31 | 36.000 | 7,174 | reserve rung |

`escalate` doubles the sample table and raises the noise radius while the answer
stays compact; it reports `cap_bound` only when the verified post-insight route
would exceed the 300-operation G9 limit.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted secrets verify and are JSON-native |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | prose plus fenced tagged JSON round-trips exactly |
| G4 | pass | 0/200,000 legal nonzero secrets; exact probability `1/2,097,151 = 4.768e-7` |
| G5 | pass | shipping exact count 1 measured by WHT and guaranteed by distance; demo exactly 1/63; reference ML 8/8 |
| G6 | pass | correlation, greedy, 2,048 restarts, and noise-free-basis ansatz all 0/8 |
| G7 | pass | doubled `n=128,s=28` instance verifies; legal space grows from 21 to 28 bits |
| G8 | pass | 20/20 feature, sample, and label relabelings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | pass | 21 chars / 8 atoms on the gate seed; 54-char worst case; compact recovery verified in 60 xors |

Track B’s successful standard algorithm is deliberately outside `attacks`: the
exact Gray-order maximum-likelihood implementation is 8/8, as expected. The
paper’s WHT count and the measured word-parallel count are both reported in
`selftest_report.json`.

## Oracle hardening loop

The mandatory bare run was executed on the shipping preset. OpenRouter returned
HTTP 403 `Key limit exceeded (total limit)` on every redraw, so the script
aborted without scoring an attempt. The transcript is genuine failed-run
evidence, but **no oracle hardness verdict is claimed**.

| arm/preset | provider calls | scored attempts | solved | outcome |
|---|---:|---:|---:|---|
| bare / easy | 4 | 0 | 0 | provider key limit; no verdict |
| structural / easy | 4 | 0 | 0 | provider key limit; no verdict |
| placebo / easy | 4 | 0 | 0 | provider key limit; no verdict |

Hinted minus placebo is therefore unavailable, not zero. The structural hint
only names the degree-two Möbius invariant; it does not chain the interpolation
steps. All three script-owned transcripts correspond to isolated runs and retain
the provider errors rather than counting them as model failures.

## Use

```python
from gen_2208_02201 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=11, **DIFFICULTY["demo"])
candidate = parse_answer("<answer>[2, 3]</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit deterministic instances with:

```bash
bash scripts/emit.sh 2208.02201 20
```

Once the OpenRouter quota is repaired, rerun bare hardening from this directory:

```bash
python3 ../../scripts/harden.py gen_2208_02201.py
```

## Caveats

- This is a structured Track B distribution, not evidence that ordinary i.i.d.
  LPN samples are easy or hard. The public labels and the restriction of noise
  to labels of weight at least three deliberately create the short route. The
  objects and checker are native `F_2` LPN objects, but the distribution is not
  the i.i.d. Bernoulli oracle distribution of Problem 1.2.
- The `4.768e-7` guessing probability is for a uniform nonzero-secret prior and
  uses the unique-witness distance guarantee. It says nothing about an informed
  solver that recognizes the quadratic table—which is precisely the intended
  distinction.
- The panel did not run an external SAT/SMT solver, a dedicated Reed–Muller
  decoder, or an optimized WHT library. It did run an exact full ML objective in
  bit-parallel Gray order; its short wall time is why the family is Track B.
- `canonical_key` handles sample reordering, arbitrary feature-coordinate
  permutation, label-variable permutation, and their tested compositions. It
  does not solve general binary-code equivalence or identify all linearly
  equivalent presentations.
- The current OpenRouter credential is the remaining external blocker. Until a
  scored script-owned bare transcript exists, this directory is locally verified
  but must not be represented as oracle-hardened or submitted as such.
