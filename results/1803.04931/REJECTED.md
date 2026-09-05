# Rejected: arXiv 1803.04931

## Decision

The constructed family passes **G** and **V** but fails **H on Track B**.  It is
therefore not shipped.  The retained implementation is
`rejected_gen_1803_04931.py`; the unedited harness evidence is
`llm_loop_transcript.jsonl` with its verdict in `.meta.json`.

This is not a Track A family.  The paper gives explicit low-degree ideal
generators, and coefficient search is linear algebra.  The only defensible claim
was Track B: make the generic finite-field recovery costly while leaving a short
structural route.  The oracle pool found and executed that route reliably.

## Paper result and exact family

Section 2 defines the ideal as the polynomials that vanish on the characteristic
vectors of the blocks.  Section 5, Theorem 5.2 states that for the points and
projective subspaces of `PG(d,q)`, a line `L` and a pair `J` in that line give the
generator

`g_(L,J) = x^(L,2) - binom(q+1,2) x^J`.

For `q=2`, if the line is `{a,b,c}` and `J={a,b}`, this is the normalized
three-term polynomial

`-2*x_a*x_b + x_a*x_c + x_b*x_c`.

The instance labels the nonzero elements of `GF(2^D)` as powers of a primitive
element and supplies `a,b`; the requested polynomial requires the exponent `c`
of `alpha^a + alpha^b`.  Generation is by composition of identities, never by
solving: from the fixed primitive trinomial `z^D+z^S+1`, it applies a random
cyclic shift and Frobenius power to a known three-term relation and carries all
three exponents through.  Verification recomputes the field equation exactly,
checks the normalized rational polynomial, and exhausts the five possible
intersection patterns `0`, one of three singletons, and all three points.

## Why Track B fails

The mechanical certificate-producing algorithm is Shanks baby-step/giant-step
for a discrete logarithm in `GF(2^D)`.  It costs `O(2^(D/2))` exact field-group
operations and the same order of stored field elements.  At the shipping preset
`D=39`, the measured run used:

- 741,456 baby steps;
- 591,017 giant steps;
- 1,332,473 total table/group steps;
- 2.945125 seconds and about 124 MB peak process memory.

The compact route recognizes that Frobenius multiplication by `2^j` rotates
`D`-bit exponent differences modulo `2^D-1`, matches the three differences from
the defining trinomial, and restores the missing shifted exponent.  The measured
upper bound at `D=39` is 129 exact bit/integer operations.  The answer is only
142 serialized characters and 13 atomic elements.

Thus there is a real mechanical/compact gap; this family was not rejected merely
because an algorithm exists.  It fails because the compact route is itself easy
to discover and execute in context.  The bare oracle results were:

| rung | field degree | solved / attempts | result |
|---|---:|---:|---|
| easy | 25 | 2 / 3 | defeated |
| medium | 35 | 3 / 3 | defeated |
| hard (shipping candidate) | 39 | 2 / 3 | defeated |
| escalation 1 | 41 | 3 / 3 | defeated |
| escalation 2 | 79 | 3 / 3 | defeated |
| escalation 3 | 89 | 2 / 3 | defeated |
| escalation 4 | 127 | 2 / 3 | defeated |

One degree-127 response was empty after exhausting the response-token budget;
the harness correctly counted it as unsolved, not as an API error.  Every rung
still had at least one exactly verified solution, which is enough to defeat it.
The final harness verdict is `too_easy` after six escalations and after moving
both `n` and `twist_min`; the fixed answer length rules out `cap_bound`.

## Other regimes checked

The obvious alternatives do not repair H.  Section 4, Theorem 4.2 writes down
the generators for a Steiner system directly once a block and a contained
`t`-set are chosen.  Section 5, Theorem 5.1 gives symmetric-design quadratics by
an explicit formula from the blocks containing a point pair.  Generic bounded-
degree vanishing-polynomial recovery is exact coefficient matching followed by
Gaussian elimination.  Asking for the design itself would make the certificate
the entire block collection (well beyond the output cap at hard sizes), while
asking for one block through a specified subset reduces to a lookup or the
displayed construction.  The paper provides no distributional-hardness theorem
for any of these searches, so none supports Track A.

The instructions prohibit hand-retuning a family after the full hardening ladder
returns `too_easy`.  No hinted or placebo runs were purchased because the bare
family already failed the required hardness gate.
