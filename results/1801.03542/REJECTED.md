# Rejected: arXiv:1801.03542, *Oddities of quantum colorings*

## Decision

This paper does not yield an honest G/H/V family under the present output and
no-tool constraints.  **G and V are available, but H fails.**  The native
projector constructions fail H on both tracks; the only scalable reduction in
the paper produced a valid Track-B prototype, retained as
`rejected_gen_1801_03542.py`, but the no-tool oracle repeatedly solved it.

This decision is based on the full 17-page paper, including Definitions 1--2,
the two constructions in Section 3, Theorem 1 and its Gröbner-basis discussion
in Section 4.2, and the 3-SAT construction and Lemma 7 in Section 5.

## Step-0 certificate audit

The exact native witness is Definition 1's family of projectors.  Section 3
gives both positive certificate producers explicitly:

- For a flat complex orthogonal representation, the paper sets
  `U_v = sqrt(d) diag(phi(v)) F` and takes its columns.  With rank-one vectors as
  the least redundant exact output, the mechanical route writes
  `|V| d^2` scalar entries.  The compact route performs the same
  `|V| d^2` coordinatewise phase multiplications/copies.  Under the 256-atom
  cap, both costs are at most 256 entry operations.  There is no compression
  gap for Track B, and the disclosed formula rules out Track A.
- For a real four-dimensional representation, Lemma 1 uses the displayed
  quaternion matrix: every output entry is just a signed copy of one input
  coordinate.  A vector-form coloring has `16|V|` atomic entries, so the cap
  permits at most 16 vertices.  Mechanical cost: at most 256 signed copies.
  Compact-route cost: the same `16|V|` signed copies, plus unavoidable output
  transcription.  Again the two costs are comparable, so the construction
  tests no hidden compression insight.

Encoding only the common Fourier or quaternion kernel does not evade this:
that kernel is instance-independent and printed explicitly in Section 3, so
the answer becomes a fixed lookup rather than a hard witness.

The negative route does not repair this.  Theorem 1 proves that the single
13-vertex graph `G13` has no quantum 3-coloring.  Section 4.2 says GBNP could
detect the contradiction but could not produce an explicit ideal certificate
for `G13`; even `K4` produced an expression with more than 7,000 monomials.
That is beyond the 256-atom/2,000-character witness cap, while the paper's human
operator proof is tied to one fixed graph.  Relabellings, unitary conjugations,
and repeated copies do not create canonically distinct hard instances.

Section 5 is the only scalable theorem: it centrally maps a 3-SAT formula `f`
to a graph `G_f`, states `f` satisfiable iff `G_f` is 3-colorable, and proves in
Lemma 7 that a three-dimensional orthogonal representation of such a graph can
be converted to a 3-coloring.  This licenses a combinatorial reduction, but it
does not give a distribution-hard positive family; the quantum separation in
Fact 4 uses one specific magic-square instance.

## Retained Track-B prototype and measured failure

The retained module inverse-generates a satisfying assignment, composes exact
XOR identities into 3-CNF blocks, and uses the Section 5 reduction.  It passes
local generation and verification checks.  Its structure-aware language has
`2^24` candidates and the shipping sample observed 0 valid guesses in 200,000.
Five cheap attacks each succeeded on 0/8 seeds.

The efficient reference algorithm is XOR-block extraction followed by exact
Gaussian elimination over `GF(2)`, with complexity `O(m n^2)`.  At the initial
shipping preset (`n=144`, 24 hidden blocks, 24 audit rows), it averaged about
0.0042 seconds and 174,489 scalar bit operations over eight seeds.  The compact
identity-plus-rank-one block route takes at most 216 exact XORs.  Thus this
prototype did have a genuine mechanical/compact gap; it is not being rejected
merely because an algorithm exists.

It nevertheless fails Track-B H in context.  The script-owned bare oracle run
found verified answers at every completed level:

| level | parameters | verified oracle solves |
|---|---|---:|
| easy | `n=144, blocks=24, audits=24` | 2/3 |
| medium | `n=156, blocks=24, audits=48` | 2/3 |
| hard | `n=168, blocks=24, audits=72` | 2/3 |
| escalation 1 | `n=168, blocks=24, audits=108` | 1/3 |
| escalation 2 | `n=168, blocks=24, audits=162` | 1/3 |

The next level was not scored: OpenRouter returned account-total-limit HTTP 403
for every retry.  The preserved `llm_loop_transcript.jsonl` and `.meta.json` are
the unedited harness outputs and record that interruption.  No hardness verdict
is inferred from those API errors.

Further escalation could only add more same-distribution audit rows while
leaving the 168-bit witness and 240-XOR compact route unchanged.  The preceding
five levels show that the models can already recognize and execute that route;
making the prompt longer until transcription fails would test scanning burden,
not the paper's mathematical insight.  The prototype is therefore rejected on
H rather than tuned to the failed run.

## Track conclusion

- **Track A:** unavailable.  Section 3 explicitly constructs the positive
  witnesses; the retained Section 5 distribution is solved in polynomial time
  by XOR extraction and Gaussian elimination; the paper supplies no
  distribution-hard generative regime.
- **Track B:** unavailable for native projector witnesses because mechanical and
  compact costs are both bounded by the certificate length (at most 256 entry
  operations).  The paper-licensed SAT prototype has a real cost gap but was
  repeatedly solved by the no-tool oracle, so it fails the declared practical
  hardness test.
- **G/V:** both are otherwise satisfied by inverse generation and exact Boolean
  clause evaluation in the retained prototype.

Accordingly there is no shipping `gen_1801_03542.py`, and no hardness claim is
made from the interrupted oracle run.
