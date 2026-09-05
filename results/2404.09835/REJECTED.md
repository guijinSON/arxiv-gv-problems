# Rejected after G9(b): arXiv 2404.09835

Paper: Mikkel Abrahamsen and Jack Stade,
[*Hardness of Packing, Covering and Partitioning Simple Polygons with Unit
Squares*](https://arxiv.org/abs/2404.09835) (2024).

## Decision

No family is shipped.  The retained native implementation passes inverse
generation, exact geometric verification, guess resistance, scaling, and the
local adversary panel, but it fails **H on Track B** at the mandatory
polarity-flipped G9(b) gate.  The one-sentence structural hint enabled a fresh
oracle to return a key accepted by the exact checker even after the single
permitted move to a harder rung.

The implementation is retained as `rejected_gen_2404_09835.py`.  The final
replacement bare evidence is `llm_loop_transcript.jsonl`, and the decisive
hinted evidence is `g9_hinted_transcript.jsonl`.  The earlier easy-rung evidence
is retained separately.  A placebo arm was not run after the second hinted
failure, because the instructions require the build to stop at that point.

## What the paper actually establishes

Section 1 defines `2x2-Square-Packing`: given a polygon and `k`, place `k`
closed, axis-aligned 2-by-2 squares inside it with pairwise disjoint interiors.
Theorem 1 proves NP-hardness even for orthogonally convex grid polygons.
Theorems 2 and 3 prove the analogous hardness of minimum small-polygon covering
and partitioning for simple grid polygons.

Section 2.2 supplies the exact facts used by the attempted family.  Lemma 6 says
that an integer-coordinate packing exists whenever any packing of the requested
cardinality exists.  Lemma 7 says that each such 2-by-2 square covers exactly
one odd/odd unit reference centre.  Consequently a packing with one square per
reference centre is perfect and has a cheap exact certificate.  Section 5 also
identifies the general packing problem with maximum independent set in a grid
graph with diagonals, but this build did not replace the polygon by that graph.

The paper is explicit about easy regimes.  Section 1.1 cites polynomial-time
optimal algorithms for some families of simple grid polygons and a PTAS for
grid polygons with holes.  Its Theorem 1 is a worst-case result; it does not
claim distributional hardness for polygons inverse-generated around their own
packing.  The orthogonally-convex reduction in Section 4 is especially large:
the proof of Theorem 1 states that an `m`-clause formula produces
`O(m^8)` squares.  Those facts ruled out an honest Track A claim for the tested
distribution and made a compact Track B certificate the only plausible route.

## The retained Track B family

The solver receives an actual simple integer-coordinate orthogonal polygon and
a public modular decoder.  A witness is a pairwise-distinct one-row matrix
`[[x_0,...,x_47]]` over `GF(p)`.  Decoding expands it to 48 concrete
integer-coordinate 2-by-2 squares.  `verify` recomputes the matrix product,
checks all four unit cells of every expanded square against the displayed
polygon by exact ray crossing, and checks every square pair for strict interior
overlap.  It never reads `inst["answer"]`.

Generation is inverse.  It samples the key `x` first and samples a directed
cycle `rho`.  If `(Pz)_i=z_rho(i)` and `B=I+3P`, the finite geometric identity

```text
B^-1 = (1-(-3)^n)^-1 * sum(j=0..n-1, (-3)^j P^j)
```

constructs the dense decoder `A=B^-1`.  The generator computes `y=A*x` and
draws a height-two comb polygon whose unique tooth in lane `i` admits the square
with offset `y_i`.  The certificate therefore exists before the instance and
is never recovered by solving it.

This is a native geometric witness—the expanded objects are the paper's grid
polygon and squares—but an intentionally easy geometric special case.  Reading
the tooth positions gives `y` immediately.  The difficulty claim was only the
no-tool compression step from those positions to the required bounded symbolic
key; it was never presented as average-case packing hardness.

## Mechanical cost and compact route

The reference algorithm first enumerates the polygon's unique integer square
position in every lane and then solves `A*x=y` by generic modular Gaussian
elimination.  Its stated generic complexity is `O(V+n^3)` exact operations.
At the final tested preset (`n=48`, `p=65537`), eight deterministic instances
were solved 8/8 with **139,946 counted operations total**, or **17,493 per
instance**, in **0.004931 seconds total** and **0.000630 seconds median**.

The compact route recognizes `A=B^-1` and evaluates
`x_i=y_i+3*y_rho(i) (mod p)`.  Counting one exact offset extraction, one modular
multiplication, and one modular addition per coordinate gives **144 exact
operations**.  Thus the mechanical and compact costs are not comparable: there
is a genuine roughly 121-to-1 operation-count gap.  This is why the family was
tested on Track B instead of being rejected merely because a polynomial
algorithm exists.

## Local gate evidence

`selftest_report.json` records G1--G8 passing and G9 failing:

| Measurement | Final tested result |
|---|---:|
| Planted/JSON checks | 12/12 |
| Candidate language size | `65537! / (65537-48)!` |
| Certified valid keys | 1 |
| Exact valid fraction | `6.548200633491954e-232` |
| Structure-aware guesses | 0/200,000 |
| Outlier offset-rank attack | 0/8 |
| Greedy diagonal fit | 0/8 |
| Random restart, 256 per seed | 0/8 |
| Direct-offset-as-key ansatz | 0/8 |
| Reference algorithm | 8/8, as expected |
| Canonical-key invariance | 80/80, including translation and axis reflections |
| Carried-witness checks | 80/80 |
| Unrelated canonical keys | 20/20 distinct |
| Serialized answer | 282 characters, 48 atoms, about 71 tokens |
| Worst observed answer over 200 seeds | about 73 tokens |
| Intended route | 144 exact operations |

The random prior is uniform over pairwise-distinct field rows, so it already
enforces every syntactic, range, length, and distinctness condition stated to a
solver.  Its tiny success probability says only that blind keys are ineffective;
it does not establish computational hardness.

## Decisive oracle evidence

The structural hint was:

> Along the displayed directed cycle, the dense offset matrix is the inverse of
> a two-tap linear operator.

This names one invariant.  It does not give the formula for the inverse action,
chain a next step, state any derived coordinate, or disclose an answer.

At the initial easy rung (`n=48`, `p=4099`), the bare pool hardened 0/3.  The
hinted pool then solved 2/3, so the rules permitted one move upward.  At the
replacement medium rung (`n=48`, `p=65537`), answer length and route length were
unchanged; only coefficient entropy increased.

| Rung / arm | Solved / counted attempts | Outcome |
|---|---:|---|
| easy bare | 0/3 | hardened |
| easy hinted | 2/3 | broke the rung |
| medium bare | 0/3 | hardened |
| medium hinted | **1/3** | **G9(b) failure** |

In the decisive medium hinted run, one Grok call reached the 900-second hard
deadline and was correctly recorded as an API error, not a failed attempt.  Its
redraw failed.  Claude also failed.  Gemini 3.1 Pro Preview, on seed
`399095794`, returned a parsed matrix for which `verify` returned `(True,
"ok")` in 117.18 seconds.  That single verified solve is sufficient to fail
G9(b).  More escalation would violate the one-rung rule.

## Final gate diagnosis

| Requirement | Result |
|---|---|
| G — generatable | Pass: inverse generation plus an exact finite geometric-series identity. |
| V — verifiable | Pass: exact modular expansion, exact polygon containment, exact overlap checks. |
| H — Track A | Fail: the paper proves only worst-case hardness, while this comb distribution has a polynomial exact recovery method. |
| H — Track B | **Fail at G9(b): a hinted oracle executed the compact route after the one allowed increase.** |
| Overall | **Rejected; no module is shipped.** |

This is not a `cap_bound` result.  The 48-atom answer and 144-operation route
are comfortably within the published caps.  It is also not a rejection based
on the mere existence of Gaussian elimination: the mechanical/compact gap is
real and measured.  The rejection is the twice-confirmed oracle behavior under
an invariant-only hint.
