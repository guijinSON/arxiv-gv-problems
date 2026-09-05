# Shuffled telescoping factors from arXiv:2303.11655

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate | canonical sparse polynomial |
| Intended intuition | decomposition into exponent rays carrying power-of-two telescoping chains |
| Domain essentiality | native; no reduction |

This generator uses the algebraic engine of Amarra, Devillers, and Praeger's
[“Block-transitive 2-designs with a chain of imprimitive point-partitions”](https://arxiv.org/abs/2303.11655).
The solver receives shuffled sparse polynomials over `Q` and must return their
exact product.  Lemma 4.1 proves the factor identity that supplies the chain
parameters in Construction 4.3.  Independent monomial substitutions put three
copies on mixed exponent rays.  Verification reconstructs those chains from the
displayed factors and compares the claimed polynomial coefficient-for-coefficient
using exact rationals; it never reads `inst["answer"]`.

## Why Track B

This is not a complexity-theoretic hardness claim.  Lemma 4.1 explicitly gives
the compact identity, so Track A would be false.  A general exact method also
exists: repeatedly try every pair of current sparse factors and multiply the pair
whose product has smallest support.  On hard `n=30`, seed 0, that reference used
4,382,001 counted integer operations and 121,485 pair trials in 1.62 seconds.  It
succeeded on 8/8 seeds.  Once the exponent-ray structure is seen, each thirty-factor
ray collapses to one trinomial; forming the final 27 terms costs 153 exact
operations.  The benchmark tests finding that decomposition in a long shuffled
display without a CAS.

Sections 2.1–2.3 fix the paper's product coordinates, partition chain, strong
inner-pair classes, and array functions.  Theorem 1.3 gives the exact array
criterion for a 2-design.  Lemma 4.1 and Construction 4.3 are the relevant
construction and certificate source here.  The paper states no hardness theorem;
its displayed recurrence is precisely the easy result that forces Track B.
Ordered factors, a single short ray, or any solver that groups supports by their
primitive exponent direction makes this family easy.

## Worked demo

For `make_instance(n=2, chains=1, variables=1, seed=7)`, the complete factor
portion of the rendered problem is:

```text
Work in Q[x0]; [a0] denotes x0^a0.
F001 = [[[2],[1,1]],[[0],[1,1]],[[1],[1,1]]]
F002 = [[[1],[1,1]],[[2],[-1,1]],[[0],[-1,1]]]
Return exactly 3 terms in ascending (total degree, exponent vector) order.
```

Thus the two factors are `1+x0+x0^2` and
`-1+x0-x0^2`; their product is `-(1+x0^2+x0^4)`.  The exact answer is:

```json
{"nvars":1,"terms":[[[0],[-1,1]],[[2],[-1,1]],[[4],[-1,1]]]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Changing the middle
coefficient to `+1` returns
`(False, "claimed polynomial is not the exact product")`.  This demo is
deliberately hand-solvable.

## Difficulty presets

| preset | chain length `n` | rays | variables | factors | status |
|---|---:|---:|---:|---:|---|
| demo | 2 | 1 | 1 | 2 | hand example |
| easy | 18 | 3 | 3 | 54 | local gates pass; oracle unavailable |
| medium | 24 | 3 | 3 | 72 | local gates pass |
| hard | 30 | 3 | 3 | 90 | intended shipping preset; external hardening incomplete |

Difficulty grows the shuffled factor haystack while the 27-term answer stays
fixed.  `escalate()` adds six factors per ray until the 2,000-character output
cap approaches; doubling hard `n` builds 180 factors and still verifies.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 preset/seed planted answers verify and JSON-round-trip |
| G2 | 6/6 corruptions rejected with 6 distinct reasons |
| G3 | tagged, fenced, prose-surrounded answer parses and verifies |
| G4 | 0/200,000 structure-aware random candidates valid |
| G5 | demo has exactly 1 valid answer in 6 candidates; hard sampled density 0/200,000; reference cost 4,382,001 operations / 121,485 trials / 1.62 s |
| G6 | five attacks each 0/8; reference algorithm 8/8 as expected |
| G7 | `n=60` builds 180 factors and verifies |
| G8 | 100/100 equivalence-invariance checks, 100/100 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 1,246 characters, 312 estimated tokens, 136 atoms, 153 intended-route operations |

## Oracle loop and G9 arms

The required harness ran, but OpenRouter rejected every call with HTTP 403
`Key limit exceeded (total limit)`.  The harness therefore produced error
records and correctly refused to issue a hardness verdict.  These are
infrastructure errors, not model failures; this result is **not ready for release**
until the bare loop completes and chooses a shipping level.

| run | preset | completed solver attempts | solved | error records | conclusion |
|---|---|---:|---:|---:|---|
| bare | easy | 0 | 0 | 4 | unavailable; no hardness evidence |
| structural hint | hard | 0 | 0 | 4 | unavailable |
| placebo hint | hard | 0 | 0 | 4 | unavailable |

The hinted-minus-placebo diagnostic is undefined because neither arm completed;
the report stores `0.0` only as a machine-readable zero-attempt placeholder.  No
conclusion about the decomposition hint can be drawn.

## Use

From this directory:

```python
import random
import gen_2303_11655 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY["hard"])
question = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.random_candidate(inst, random.Random(1)) != inst["answer"]
```

After a successful bare hardening run, emit from the repository root with:

```bash
bash scripts/emit.sh 2303.11655 20 hard
```

## Caveats

This covers the paper's exact factor identity, not the broader combinatorics of
recognising block-transitive designs or automorphism groups.  A CAS, or the simple
act of grouping factors by primitive exponent direction and sorting their scales,
defeats it; the disclosed reference algorithm is expected to do so.  The attack
panel did not test a production CAS or a dedicated cyclotomic-factor recogniser.
The 0/200,000 density is an observed fraction under a prior that already enforces
the promised 27-term shape, signs, degree box, and forced endpoints; it is not a
statistical proof of the true probability and says nothing about structured
guesses exploiting exponent rays.  Timing is machine-dependent.  Most
importantly, the four-vendor oracle evidence is missing because the supplied key
was exhausted, so local gates alone do not establish no-tool hardness.
