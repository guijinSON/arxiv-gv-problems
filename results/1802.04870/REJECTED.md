# Rejected family for arXiv:1802.04870

## Verdict

The attempted **RAAG direct-product secret-sharing family fails H on Track B**.
It passes generation and exact verification, but the script-owned no-tool oracle
loop defeated every named preset and every supported escalation.  The final
verdict in `.meta.json` is `too_easy`; therefore the family must not ship.

This is not a rejection merely because an efficient algorithm exists.  STEP 0
identified that algorithm and correctly selected Track B first.  The rejection
comes from the required empirical hardening loop: the compact route was repeatedly
found and executed by the evaluated models.

## Paper facts used at STEP 0

Flores, Kahrobaei, and Koberda, [*Algorithmic problems in right-angled Artin
groups: complexity and applications*](https://arxiv.org/abs/1802.04870), defines
`A(Gamma)` in Definition 2.1.  Theorem 4.1 identifies graph join factors with
direct-product factors of the RAAG.  Proposition 4.2 computes the maximal join
decomposition in polynomial time by taking the complement graph and finding its
connected components.  Section 6.3.1 uses those factor counts as the values
`m_i=f(i)` of a monic polynomial and takes `f(0)` as the shared secret.

The paper also explicitly records the easy regimes that rule out a Track A
claim: the RAAG word and conjugacy problems are linear-time, shortlex/geodesic
normal forms are polynomial-time (Section 2.2), graph/RAAG automorphism has a
quasi-polynomial consequence (Corollary 3.7), and join decomposition is
polynomial-time (Proposition 4.2).

## G and V

Generation is inverse and theorem-backed.  It samples each desired factor count
`m_i` first, sets `N=2^n` and a cyclic step `s=m_i*a` with odd `a`, and then
relabels the resulting disjoint cycles by an exact Feistel permutation.  Thus
the noncommutation graph has exactly `gcd(N,s)=m_i` components by construction.
The planted rational `[f(0),1]` is obtained from the exact consecutive-node
interpolation identity, not by solving the emitted presentations.

Verification is executable and exact: validate the succinct presentations,
recompute every `gcd(N,s)`, evaluate the integer interpolation identity, reduce
the submitted rational, and compare.  The preserved local self-test passes G1
through G9(c), including 0/200,000 random hits and four attacks at 0/8 each.

## Why H fails

Track A is false because Proposition 4.2 supplies a polynomial-time certificate
producer.  Track B initially looked plausible because the mechanical and compact
costs differ sharply:

| Final attempted level | Mechanical reference route | Compact route |
|---|---:|---:|
| `n=24`, degree 28, 14 Feistel rounds | 469,762,048 complement-edge iterations and **13,623,099,392** counted edge/Feistel operations | **173–175** exact operations |

The mechanical route is Proposition 4.2 union-find after evaluating both Feistel
endpoints of every complement edge.  The compact route observes that Feistel only
renames vertices, reads `gcd(2^n,s)` as the lowest set bit of `s`, and applies

`f(0)=(-1)^d d! + sum_i (-1)^(i-1) C(d,i)m_i`.

That is a genuine compression gap, so the paper was built rather than rejected at
triage.  It nevertheless fails this benchmark's H gate because the models can see
and carry out the shortcut.  The bare hardening transcript contains 18 scored
calls and no API errors:

| Level | Parameters `(n, degree, rounds)` | Solved / attempts |
|---|---|---:|
| easy | `(14,20,4)` | 3/3 |
| medium | `(16,24,6)` | 2/3 |
| hard | `(18,28,8)` | 2/3 |
| escalation 1 | `(20,28,10)` | 1/3 |
| escalation 2 | `(22,28,12)` | 1/3 |
| escalation 3 | `(24,28,14)` | 3/3 |

Overall, 12/18 calls produced parsed answers that `verify()` accepted.  At the
largest supported level all three calls solved, so increasing the Feistel
haystack did not help once the invariant was recognized.  This is not a G9(b)
rejection; the bare STEP 4 run itself returned `too_easy`.

## Preserved evidence

- `rejected_gen_1802_04870.py` — the complete locally verified generator.
- `selftest_report.json` — local gate measurements for its provisional `easy`
  shipping preset.
- `llm_loop_transcript.jsonl` and `.meta.json` — script-owned decisive bare run.
- `g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl` — earlier
  quota-error diagnostics; they play no role in this rejection.

No alternative family is claimed.  Section 7's clique, coloring, independent-set,
and induced-subgraph translations give worst-case hardness only; this paper does
not provide a theorem-backed hard generatable distribution for them, and replacing
the native RAAG objects with an ad hoc planted graph would not repair this failed
Track B family.
