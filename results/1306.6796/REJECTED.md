# Rejected: arXiv 1306.6796

This paper does not ship under the present no-tool hardening protocol. The
built family is retained as `rejected_gen_1306_6796.py`; it is mathematically
sound, but it failed the required oracle gates before submission.

## Gate diagnosis

| condition | result |
|---|---|
| G — generatable | **passes** by Theorem 3.2, affine transport, and the product construction of Lemma 3.1 |
| V — verifiable | **passes** by exact arithmetic over each `F_p`: conic fitting, polynomial substitution, a rank-one kernel, and determinant/orthogonality checks |
| H — Track A | **fails**: this generated distribution has efficient recovery algorithms, so no structural-hardness claim is made |
| H — Track B | the mechanical/compact gap is real, but the family **fails STEP 4/G9(b)** against the evaluated no-tool oracle pool |

The relevant native definition is Section 2, Definition 2.9. The construction
is Section 3, Theorem 3.2, and products are licensed by Section 3, Lemma 3.1.
Section 4.1 records translation invariance. These are the paper's finite
abelian-group objects; no graph or convenience reduction was used.

## Mechanical cost and compact route

The domain-standard recovery method forms the directions of every ordered
difference in each factor and finds the one absent projective line. Its cost is
`O(sum p_i^2)` field operations. On the tested easy instance with primes 1847
and 1657 it performed **6,153,554 ordered-difference operations in 0.881718
seconds** in the final selftest (an independent repeat took 1.495461 seconds).
On the permitted medium retry with primes 2731 and 2579 it performed
**14,104,292 operations in 3.495459 seconds**.

The compact route fits the unique conic through any five displayed points in
each factor, reads the kernel of its rank-one homogeneous quadratic part, and
uses the perpendicular projective direction for the formal dual. The retained
implementation counts **260 exact field operations** for the two conic solves.
Thus the existence of an efficient method is *not* the rejection reason; the
gap is a legitimate Track B construction. Track A would nevertheless be false.

## Oracle evidence

The initial easy bare run was hardened: **0/3** oracles solved it. The structural
hint was deliberately limited to the invariant—“Each factor lies on a conic
whose rank-one quadratic part has the missing difference direction as its
kernel.”—and did not give the perpendicular step or any coefficient. With that
hint, Grok 4.6 returned a verified witness, so easy failed G9(b): **1/3 solved**.

The protocol permits one move up the declared ladder. At medium, the bare panel
was already defeated: Grok 4.6 and Gemini 3.1 Pro both returned verified
witnesses (**2/3 solved**). The medium hinted panel was also defeated when Grok
4.6 returned a verified witness (**1/3 solved**). No further rung was tried,
because that would tune the family past the one G9 allowance.

| run | solved / attempts | evidence |
|---|---:|---|
| easy bare | 0 / 3 | `llm_loop_transcript.jsonl` |
| easy structural hint | 1 / 3 | `g9_hinted_transcript.jsonl` |
| medium bare retry | 2 / 3 | `g9_medium_bare_transcript.jsonl` |
| medium structural hint retry | 1 / 3 | `g9_medium_hinted_transcript.jsonl` |

All successful records have `parsed=true`, `verify_ok=true`, and
`verify_reason="ok"`; they are not parser artifacts. One Claude response was
empty after exhausting its reasoning budget, but the rejection rests on the
verified successes, not on that failure. The placebo arm was not run after the
gated structural-hint failure; consequently `hinted_minus_placebo` is recorded
as `null`, not as a fabricated diagnostic estimate.

## Why no alternate family was substituted

The paper's other theorem-backed positive examples are TITO and products or
inflations of the same explicit constructions, which expose at least as much
recoverable algebraic structure. Proposition 4.3 and Section 5 are
nonexistence/classification results; their proofs do not furnish a scalable
bounded witness language for arbitrary generated negatives (the Barlow proof
ultimately enumerates the remaining cases by computer), while the Best-packing
obstruction is the immediate divisibility condition `|S||T|=|G|`. The open
classification questions in Section 6 provide no construction certificate.
Accordingly there is no second native family in this paper that clears the
required G/H/V and no-tool gates without inventing a surrogate problem.
