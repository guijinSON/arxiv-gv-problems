# arXiv 2203.02296 — paired prime cubes and powers of two

> **Status:** the generator and every local gate pass, but the required oracle
> run is **not complete**. In the latest bare run all three `easy` attempts
> solved; at `medium`, one attempt failed and one solved. OpenRouter then
> returned HTTP 403 “Key limit exceeded” on every redraw, before `hard` was
> tested or a verdict was written. The script-written partial and error
> transcripts are retained, but they are not shipping-level hardness evidence.

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | number theory |
| Object regime | integer lattice |
| Computational core | other (bounded Diophantine parameter search) |
| Certificate | exact symbolic `[q,j1,j2,e]` expansion |
| Intuition | invariant — two low-bit residues share a hidden prime factor |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

The solver receives two positive odd integers. It must represent each as one
prime, four cubes of primes, and the same `k` powers of two. In this bounded
subfamily the cube primes form symmetric progressions: row `i` uses two copies
each of `q-a_i` and `q+a_i`, the two ordered offsets are distinct, their
displayed algebraic cofactors are coprime, and every power is `2^e`. The
four-integer answer is an exact compressed witness; the checker expands it,
deterministically tests all displayed integers for primality, checks the gcd,
and substitutes into both equations using integer arithmetic only. It accepts
every witness in the stated language, not only the planted one.

This is a native symmetric subfamily of the simultaneous system (1.7) in Xin Chen,
[“On pairs of one prime, four prime cubes and powers of 2”](https://arxiv.org/abs/2203.02296).
No graph, finite field, or other surrogate replaces the integer equations.
Generation samples the primes and exponent first and computes the targets last,
so it never solves an emitted instance.

## Why Track B, not Track A

Theorem 1.1 proves that sufficiently large comparable positive odd pairs have a
representation when `k=231`. Sections 2–3 prove positivity of a weighted count
by the circle method. They give neither an effective threshold nor an algorithm
that outputs a representation, and they say nothing about computational
hardness of this inverse distribution. The theorem is therefore context, not a
Track A hardness claim and not the certificate-producing procedure.

An algorithm does exist for this restricted family. A definition-driven scan
tries the allowed `q` values and derives both offsets and `e`; it uses `O(n)`
exact divisions and constant memory. At shipping `n=6,000,000`, the eight-seed
reference run solved 8/8, averaging 1,687,770 recorded operations and 1.09 s
per instance in the latest eight-seed run. The machine-readable timing is in
`selftest_report.json`.

The compact route uses

`2(q-a)^3 + 2(q+a)^3 = 4q^3 + 12qa^2`.

Modulo `2^B`, each target is therefore `q(4q^2+12a_i^2+1)`. Construction makes
the two cofactors coprime, so their gcd is `q`; two exact divisions and integer
square roots recover the offsets, the public floor formula recovers `j1,j2`,
and the high quotient recovers `e`. The measured route is at most 76 exact
operations. The benchmark tests whether a no-tool solver finds this invariant,
not whether the unrestricted Waring–Goldbach problem is hard.

## Worked demo

The complete `demo`, `seed=0` statement is hand-scale:

```text
PAIRED PRIME-CUBE REPRESENTATION

All quantities are ordinary nonnegative integers and every interval below is inclusive.  Repeated prime terms and repeated powers of two are allowed.

N1 = 24155151
N2 = 23832447
k = 5
B = 22
q_min = 50
q_max = 99
j_start = 5
j_last = 12
offset_scale = 16
e_min = 22
e_max = 29

Find four integers q, j1, j2, e.  They must obey
  q_min <= q <= q_max,
  j_start <= j1,j2 <= j_last (order matters; j1 and j2 must differ),
  e_min <= e <= e_max.
For i=1,2 define exactly
  a_i = 2 * floor(j_i*q / (2*offset_scale)).
The three integers q-a_i, q, q+a_i must all be prime for each i.
Also define c_i = 4*q^2 + 12*a_i^2 + 1; gcd(c_1,c_2) must equal 1.
They must give the two exact identities
  N1 = q + 2*(q-a_1)^3 + 2*(q+a_1)^3 + k*2^e,
  N2 = q + 2*(q-a_2)^3 + 2*(q+a_2)^3 + k*2^e.
Thus each row is one prime, four cubes of primes, and the same k powers of two: the four cube primes are two copies each of q-a_i and q+a_i, and all k power exponents equal e.

Give your final answer inside <answer></answer> tags as the JSON array [q,j1,j2,e], using base-10 integers.
Example format: <answer>[50,5,6,22]</answer>
Output nothing else inside the tags.
```

Its answer is `[83,6,5,22]`; `verify` returns `(True, "ok")`. Changing the
exponent to 23 returns `(False, "first exact integer identity does not hold")`.
A person can solve this 160-candidate language on paper; the gcd identity
makes it much shorter.

## Difficulty and gates

| preset | n | offset choices | k | exponent slots | exact language | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 50 | 8 | 5 | 8 | 160 | hand example |
| easy | 10,000 | 24 | 231 | 64 | 23,680 | solved by 3/3 oracle attempts |
| medium | 200,000 | 40 | 231 | 128 | 757,248 | solved by 1/2 completed attempts |
| hard | 6,000,000 | 64 | 231 | 256 | 34,353,664 | configured shipping candidate; not reached |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify and are JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged JSON round-trips through prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; space 34,353,664; exact planted-word chance 1/23,356,416 |
| G5 | shipping density 0/200,000; demo exact count 1; 256-restart attack 0/256 in 0.002 s |
| G6 | four attacks each 0/8; reference bounded scan 8/8 at 1.094 s mean |
| G7 | doubled `n` and exponent haystack build; witness still has four atoms and verifies |
| G8 | 40/40 key invariances, 40/40 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 21 chars / 6 estimated tokens / 4 atoms; at most 76 route operations |

## Oracle loop

The latest bare harness run completed five real calls, then made four erroring
redraws and stopped without a verdict. `easy` was solved on all three attempts.
At `medium`, Gemini returned one invalid witness and GPT-5.6-terra returned a
valid one, so `medium` is defeated regardless of the missing third attempt.
The run never reached `hard`.

| arm / preset | models reached | valid attempts | result |
|---|---|---:|---|
| bare / easy | GPT-5.6-terra, Gemini 3.8 Flash | 3 | 3/3 solved |
| bare / medium | GPT-5.6-terra, Gemini 3.8 Flash | 2 | 1/2 solved; then four HTTP 403 redraw errors |
| bare / hard | — | 0 | not reached; no verdict |
| structural hint / hard | Claude Sonnet 5, GPT-5.6-terra | 0 | prior run: four HTTP 403 errors |
| placebo hint / hard | Claude Sonnet 5, Gemini 3.1 Pro | 0 | prior run: four HTTP 403 errors |

The G9 shipping-level arms therefore have zero completed attempts.
`hinted − placebo` is not statistically defined; the report stores `0.0` only
because both denominators are zero and labels the verdict `not_run`. Nothing
can yet be concluded about whether the hint isolates the intended invariant.
Re-run the bare shipping candidate and both G9 arms after restoring OpenRouter
quota.

## Use

From this directory:

```python
import json
import gen_2203_02296 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
statement = gen.render(inst)
answer = gen.parse_answer(
    "<answer>" + json.dumps(inst["answer"]) + "</answer>"
)
assert gen.verify(inst, answer) == (True, "ok")
```

From the repository root, after a successful oracle rerun:

```bash
bash scripts/emit.sh 2203.02296 20
```

## Caveats

- This is a deliberately symmetric restriction of (1.7), not the distribution
  in Theorem 1.1 and not evidence that Waring–Goldbach representation is hard.
- The 0/200,000 guess figure uses the exact planting prior: `q` is uniform over
  eligible primes, the ordered distinct coprime offset pair is uniform given
  `q`, and `e` is uniform in its interval. It does not model a solver that
  recognizes the gcd invariant, which solves deterministically.
- Repeated cube primes and repeated exponents are permitted by the paper’s
  variables, but the benchmark relies heavily on those repetitions to keep the
  certificate writable.
- The outlier, cube-root greedy, random-restart, and bounded divisor attacks were
  tested. A generic SMT solver, integer-factorization package, lattice method,
  and learned pattern recognizer were not. The full bounded divisor scan is the
  successful reference baseline.
- The canonical key exactly handles exchange of the two identically defined
  rows. It is not claimed to canonicalize arbitrary Diophantine equivalences.
- The paper’s “sufficiently large” threshold is ineffective here; inverse
  generation supplies validity independently of that theorem.
- Exact primality is deterministic for the module's declared unsigned 64-bit
  parameter range. The shipping ladder and six automatic escalations remain
  far below that implementation boundary.
- The OpenRouter quota failure is the only unfinished mandatory step. The
  current transcripts cannot support submission or a hardness claim.
