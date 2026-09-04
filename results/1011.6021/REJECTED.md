# Rejected: arXiv 1011.6021

Paper: Prabhanjan V. Ananth and Ambedkar Dukkipati,
[*Border basis detection is NP-complete*](https://arxiv.org/abs/1011.6021)
(2010).

## Decision

No family from this paper met **G, H, and V** simultaneously.  The strongest
native candidate passed construction and exact-verification checks but failed the
mandatory STEP 4 oracle loop with verdict `too_easy`.  The failure is structural:
the paper supplies a worst-case reduction from 3,4-SAT, not an average-case
hardness result for answer-first planted formulas.  The particular distribution
that can be generated with a compact certificate has a linear-time projective
interpolation algorithm, and language models executed that compact route at every
allowed size.

The experimental module and the script-owned bare transcript are retained as
rejection evidence.  There is deliberately no `selftest_report.json`, shipping
`README.md`, or G9 transcript: those are shipping artifacts, and the instructions
require stopping after `harden.py` returns `too_easy`.

## What the paper actually proves

Section 2 defines an order ideal as a finite divisor-closed set of monomials and
its border as all one-variable multiples outside the ideal.  An
`O`-border prebasis has exactly one border monomial in each polynomial; it is an
`O`-border basis when the residue classes of `O` form a vector-space basis of the
quotient.  The quoted Buchberger criterion checks neighboring border polynomials
by exact constant-coefficient reductions.

The subsection **BBD is in NP** gives an executable certificate.  A proposed
border monomial set `B` is checked using three necessary-and-sufficient monomial
conditions, with costs stated as
`O(m^2 N^2)`, `O(N m^2)`, and `O(N m^3)`.  Divisibility then checks that the input
is a border prebasis, and the Buchberger criterion checks that it is a border
basis.  This is a polynomial-time *verifier*, not a certificate-producing
algorithm.

The Reduction subsection maps a 3,4-SAT formula to sparse polynomials.  Its exact
source promise matters: every clause has three variables, each Boolean variable
has at most four total clause occurrences, both signs occur, and no clause
contains a variable together with its complement.  Besides variable and clause
polynomials, the construction includes every degree-eight monomial as a singleton
polynomial and a second forced singleton family built from monomial children.
The main theorem proves that the SAT formula is satisfiable exactly when this
system is a border basis for some order ideal.

Given a satisfying assignment, the proof explicitly constructs the border set:
choose one of the two degree-seven terms in every variable polynomial, choose a
term belonging to a true literal in every clause polynomial, and include every
forced singleton.  Thus the reduction gives G and V when the generator already
knows a satisfying assignment.  It does **not** say that formulas planted around
such an assignment are hard on the generated distribution.

## STEP 0 discriminating test

The prior-triage proposal was to choose an order ideal and border basis first and
emit its generators.  For that direct construction, the generator itself writes
the border terms into the supports.  Recovering the intended certificate is then
support inspection or direct execution of the construction, so it cannot support
Track A.

The only paper-backed route to hide the choices is the central 3,4-SAT reduction.
But a random satisfying bounded-occurrence formula has no hardness guarantee from
the paper: NP-completeness is worst-case, while the prompt requires hardness for
the generated distribution.  Starting with an arbitrary hard 3,4-SAT instance
would restore the theorem's regime but lose G, because the generator would have
to solve it to obtain the assignment.

I therefore tested the remaining honest option, Track B, and disclosed the
certificate-producing algorithm before hardening.

## Track B candidate that was tested

For a prime `q`, take two copies of the projective line over `GF(q)`.  Superpose
three projective perfect matchings obtained from three symmetrically sampled
conjugated affine maps.  For each point vertex with incident edge variables
`e1,e2,e3`, use the complementary clause pair

```text
( e1 OR  e2 OR  e3)
(-e1 OR -e2 OR -e3).
```

Every edge variable occurs exactly four times—positively and negatively at each
endpoint—so this is precisely inside the paper's 3,4-SAT promise.  Any one of the
three projective matchings satisfies all clauses, and Section 3's proof decodes
that assignment to a border-term certificate.  All three matchings are drawn from
the same distribution and all three are valid; there is no distinguished plant.

The writable witness consists of three source-image pairs.  Three distinct pairs
determine a unique `PGL(2,q)` transformation, so exact verification interpolates
its 2-by-2 matrix and substitutes all `q+1` projective points into the edge table.
This is a concrete finite witness and never consults the planted answer.

The fatal reference algorithm is equally direct.  Choose any three source rows.
Each has at most three neighbors, so enumerate at most `3^3 = 27` image triples,
interpolate their projective maps, and scan the edge table.  This takes
`O(q log q)` bit operations.  At the initial shipping candidate `q=211`, the
implementation used a median 5,334 counted modular operations and 708 point
evaluations over eight seeds, solving 8/8 in about 0.0003 seconds.  A shared
source-image pair reduces the intended by-hand route further, to at most 286
exact field operations.

Local checks did not rescue the family:

| measurement at `q=211` | result |
|---|---:|
| planted certificates verified | 12/12 across all presets |
| structure-aware random guesses | 0/200,000 |
| exact valid fraction | `3 / 9,393,720` = `3.193622973646223e-7` |
| min-target attack | 0/8 |
| local greedy attack | 0/8 |
| 256-restart full-language attack | 0/8 |
| identity ansatz | 0/8 |
| disclosed interpolation algorithm | 8/8 |
| serialized witness | 40 characters in the measured seed |

Those numbers establish generation, verification, and low random density.  They
do not establish hardness, and the efficient reference algorithm is why the
candidate was Track B rather than Track A.

## Mandatory oracle result

The bare `scripts/harden.py` run used the prescribed fresh four-vendor pool at
medium reasoning effort.  A level is defeated when any oracle solves it.

| level | parameter | solved / scored attempts | outcome |
|---|---:|---:|---|
| easy | `q=211` | 3/3 | defeated |
| medium | `q=307` | 3/3 | defeated |
| hard | `q=401` | 3/3 | defeated |
| maximum allowed escalation | `q=547` | 1/3 | defeated |

The two failures at `q=547` were one invalid projective map and one empty
length-limited response.  Grok 4.6 nevertheless returned a verified certificate,
so the level was solved under the harness rule.  The script-owned metadata says:

```json
{
  "verdict": "too_easy",
  "escalations_used": 3,
  "reason": "the oracle pool solved every level through 3 escalations"
}
```

Increasing `q` is not a meaningful remedy: the witness is still recovered from a
constant number of rows, while the rest is only a mechanical validation scan.
Hand-tuning past the maximum escalation would violate STEP 4 and would turn input
length into the difficulty source.

## Other variants considered

| candidate | outcome | reason |
|---|---|---|
| Directly plant an order ideal and its border prebasis | H fails | The chosen border monomial is exposed by the construction/support pattern. |
| Use the paper's full reduction on a random planted 3,4-SAT formula | Track A unsupported | The paper proves worst-case NP-completeness, not hardness of that planted distribution; sparse random formulas may be easy. |
| Start from a genuinely hard 3,4-SAT instance | G fails | Obtaining the satisfying assignment would require solving the source instance. |
| Output the entire border set from the reduction | G9(c) fails | The forced degree-eight family makes the explicit certificate and rendered instance enormous; compression is necessary. |
| Use the projective compression above | **STEP 4 fails** | A constant-size interpolation route is executable by the oracle pool even at the maximum escalation. |
| Ask for a NO instance | witness rule fails here | The paper gives a soundness reduction, not a bounded per-instance refutation certificate. |

## Gate outcome

| requirement | result |
|---|---|
| G — known certificate by construction | Pass for the tested reduction: sample three projective matchings first and carry one satisfying assignment through Section 3. |
| V — cheap exact verification | Pass: exact projective interpolation, incidence substitution, and the paper's deterministic border decoder. |
| H — hard in the declared track | **Fail: the disclosed linear-time algorithm is easy enough for the no-tool oracle pool; `harden.py` returned `too_easy`.** |
| Overall | **Rejected.** |

G9 hinted/placebo arms were not run because the stronger prerequisite—the bare
hardening loop—already failed.  Reporting placeholder arm counts or a passing
self-test after this verdict would be misleading.
