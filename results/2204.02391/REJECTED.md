# Rejection: arXiv 2204.02391

## Decision

This paper does not ship a generator. The native construction passes **G** and
**V**, but fails **H on Track B**, specifically the polarity-flipped G9(b) gate.
The bare oracle pool failed on all three medium-preset instances, but an oracle
given the one-sentence structural hint returned an exactly verified witness.
The protocol permits one move up the named ladder; the same failure occurred
after moving from `easy` to `medium`, so no further escalation or redesign is
allowed.

Track A would be false independently. Proposition 1.1 gives necessary and
sufficient CRT/gcd conditions, and Remark 1.3(3) says the supplied Sage program
checks even 100,000-digit cycle lengths in seconds.

## Paper basis and the retained construction

[Morris, *Hamiltonicity after reversing the directed edges at a vertex of a
Cartesian product*](https://arxiv.org/abs/2204.02391) fixes the native digraph in
Definition 0.4. Lemma 2.2 replaces the pushed product by the same directed
toroidal grid with its `R_{2,2}` rectangle deleted. Lemmas 4.3--4.5 force the
unique cycle cover along cosets of `<(1,-1)>`, and equation (4.13) says that this
cover is a single Hamiltonian cycle exactly when its two knot coordinates are
coprime.

The retained module generates dimensions from
`A + B*sqrt(7) = (8 + 3*sqrt(7))^e`, with odd `e`. It writes the certificate
directly as `h = 14B - 5A` and `q = 2A - 5B`; it never searches for a cycle or
runs Euclid. The identity `A^2 - 7B^2 = 1` proves `Bh + 2 = Aq`, and the
coefficient matrix for the knot coordinates has determinant one. Verification
uses exact integer endpoint, parity, barrier, and gcd checks. As an independent
audit, all 88 programs accepted among 17,216 structure-aware candidates on
coprime grids of dimensions 3 through 40 expanded to one directed cycle.

## Step 0 cost comparison

The standard certificate-producing method is extended-Euclidean CRT recovery
followed by Proposition 1.1's exact tests. Its complexity is
`O(log(max(m,n)))` integer divisions. On 32 medium-preset instances it solved
32/32, averaging 0.00080 seconds, 1,998.25 Euclidean divisions, and 8,002
counted high-level operations (ranges: 1,212--2,887 divisions and
4,854--11,560 operations).

The compact Pell route is 12 high-level exact operations once the invariant is
recognized. Thus there is a real mechanical/compact gap; this is not a rejection
merely because an efficient algorithm exists. It is rejected because G9 directly
showed that the evaluated solver can recognize and execute the compact route
when given only the invariant. The medium answer stayed within the format cap:
at most 956 serialized characters, about 239 tokens, and 9 atomic elements.

## Oracle evidence

The structural hint was exactly one sentence and named no procedure or derived
quantity: “The two cycle lengths lie on a norm-one Pell conic over the
integers.” The placebo was matched in register and carried no mathematical
information.

| rung | bare | structural hint | placebo | result |
|---|---:|---:|---:|---|
| easy (`n=101`) | 0/3 solved | 1/3 solved | 0/3 solved | G9(b) failed; moved up once |
| medium (`n=301`) | 0/3 solved | 1/3 solved | 0/3 solved | final G9(b) failure |

At medium, `x-ai/grok-4.6` returned a parsed witness that `verify` accepted with
`(True, "ok")`; its recorded response time was 842.89 seconds. The other two
hinted attempts failed. Hence `hinted - placebo = 1/3`, and the success cannot be
attributed merely to appending another sentence.

The script-owned medium bare evidence is in
`llm_loop_transcript.jsonl`; the final medium diagnostic rows are in
`g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl`. The complete
implementation is preserved as `rejected_gen_2204_02391.py`, as required for a
future audit.

For each isolated final arm, the scratch copy exposed only the target
`{"n": 301, "jitter": 32}` parameters under the harness's sole non-demo rung,
so the transcript's `preset` field reads `easy`; these are exactly the retained
module's named `medium` parameters, as the recorded `params` field shows.

## Gate summary

| gate | outcome |
|---|---|
| G, inverse/theorem-backed generation | pass |
| V, exact witness verification | pass |
| Track A hardness | inapplicable/false by Proposition 1.1 and Remark 1.3(3) |
| Track B mechanical-versus-compact gap | present: 8,002 versus 12 operations |
| G9(b), hinted oracle must remain hardened | **fail at easy and medium** |
| G9(c), size and route caps | pass: 956 chars, 9 atoms, 12 operations |
