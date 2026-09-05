# Rejected: arXiv 2506.17521

Paper: [Structural Optimal Jacobian Accumulation and Minimum Edge Count are
NP-Complete Under Vertex Elimination](https://arxiv.org/abs/2506.17521).

## STEP 0 triage

The prior “reconfiguration by reversing an elimination sequence” hypothesis is
not the problem studied in the paper. The native problems are optimization
problems on a DAG. Section 1 defines vertex elimination, Markowitz cost, total
elimination sequences, Structural Optimal Jacobian Accumulation, and Minimum
Edge Count. Section 3, Theorem 1 proves the former NP-complete by a linear
reduction from Vertex Cover; Section 4, Theorem 2 proves the latter NP-complete
from Independent Set on 2-degenerate subcubic graphs of girth at least five.

The witness and checker are sound: an elimination sequence is polynomial-size,
and exact replay computes its cost or remaining edge count in polynomial time.
Section 5 also matters at triage: Proposition 3 gives an `O(2^n n^3)` exact
algorithm for Minimum Edge Count, and Proposition 4 gives an `O(2^n n^4)`
exact algorithm for optimal Jacobian accumulation (plus an `O(4^n n^3)`
polynomial-space variant). These are exponential rather than disqualifying
polynomial certificate producers, but the NP-completeness theorems are
worst-case results and provide no average-case guarantee for an inverse-planted
generator distribution.

## Family attempted

I therefore tested an explicit **Track B** construction rather than making an
unsupported Track A claim. It uses the paper's exact Vertex Cover gadget. A
known independent-set complement is planted first as two translated exponent
cosets in `GF(p)*`; its complement is carried through Theorem 1 to the proof's
four-phase total elimination sequence. The verifier checks independence,
builds the paper's DAG, and replays every elimination exactly. The successful
reference algorithm is disclosed: repeated multiplication by `g^7` decodes
the two cosets in `O(n)` exact modular arithmetic (205 operations or fewer at
the largest named preset).

This construction passed the local checks before oracle hardening: planted
witnesses verified on all presets, five corruptions had five distinct rejection
reasons, parsing round-tripped, structure-aware guessing scored `0/200000`,
five non-reference attacks scored `0/8` each, size doubling verified, and the
canonical key passed 60 relabelling checks and distinguished 20/20 unrelated
instances. Those facts establish generation and verification, not hardness.

## Decisive failure: STEP 4

The unmodified `scripts/harden.py` run returned:

```json
{
  "verdict": "too_easy",
  "escalations_used": 3,
  "reason": "the oracle pool solved every level through 3 escalations"
}
```

The result by rung was:

| rung | parameters | oracle outcomes |
|---|---:|---|
| easy | `n=112, degree=8` | Terra, Claude, and Gemini all solved |
| medium | `n=196, degree=10` | Gemini, Grok, and Terra all solved |
| hard | `n=336, degree=10` | Gemini and Claude failed; Grok solved |
| escalated | `n=420, degree=10` | Claude failed; Gemini and Terra solved |

The exact seeds, replies, parse results, and verifier results are preserved in
`llm_loop_transcript.jsonl`; `.meta.json` records master seed
`11872176673125796580` and the `too_easy` verdict.

Because at least one oracle solved every rung through the mandatory cap, this
family fails **H / STEP 4**. Per the task rules it is given up on: I did not
raise the size again, retune the algebraic tag, run the G9 arms, or manufacture
shipping reports. The draft module and harness transcript remain only as
reproducible rejection evidence and must not be emitted as a dataset family.

No alternate family in this paper fixes that failure without losing one of the
required properties. A direct inverse-elimination construction has no
distributional hardness theorem and exposes its reverse signature; the Section
3 and Section 4 reductions inherit arbitrary Vertex Cover/Independent Set
witnesses but do not provide a scalable hard-instance distribution with known
certificates; and using only the paper's order-independence or false-twin
propositions makes the certificate mechanically recoverable. Thus a Track A
claim would rely only on worst-case NP-hardness, while the tested honest Track B
route is empirically too easy.
