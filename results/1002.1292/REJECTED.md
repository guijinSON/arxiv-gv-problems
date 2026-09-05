# Rejected family audit for arXiv:1002.1292

## Decision

The attempted family fails **H on Track B**. It passes the construction and
verification requirements: the generator samples an affine Boolean factorization
first, and a skew-set fooling set gives an exact, executable lower-bound certificate
showing that its width is minimal. The answer is therefore known by inverse
generation, and `verify` checks the paper's asymmetric Boolean product and the
fooling-set cross entries without reading `inst["answer"]`.

It does not pass the no-tool hardness requirement. Both oracle vendors repeatedly
recovered the exact affine triples from the displayed first and centered-third
moments. Every named rung was defeated, as was the first custom escalation:

| round | parameters | exact solves / usable attempts |
|---:|---|---:|
| 0 | `p=41, blocks=2` | 2/3 |
| 1 | `p=71, blocks=2` | 3/3 |
| 2 | `p=101, blocks=2` | 2/3 |
| 3 | `p=101, blocks=3` | 3/3 |

Thus the family remained solvable after the three escalations required by STEP 4.
The next rung (`p=167, blocks=3`) also had one exact solve before the shared
OpenRouter key reached its total limit; those API errors are not counted as
model failures. The corrected transcript is retained in
`llm_loop_transcript.jsonl`.

## STEP 0 basis

Section 2, Definitions 1--3 define the asymmetric Boolean row product and ask for
minimum-width Boolean Mod and rescue matrices. Section 3, Theorem 1 proves its
equivalence to Bipartite Biclique Edge Cover, while Theorem 2 gives NP-completeness
and inapproximability for the unrestricted problem. Those worst-case results do not
establish hardness for this generated affine distribution.

Section 4 is the decisive easy-result for Track A: Lemma 1 gives an `O(N^3)`
kernelization to at most `2^k` vertices, and the final theorem in Section 4.3 gives
an exact FPT algorithm with running time
`O(2^(k*2^(k-1)+3k) + N^3)`. The retained generator therefore correctly declared
Track B rather than Track A.

## Mechanical cost versus compact route

The mechanical algorithm for the attempted bounded certificate language enumerates
the `p(p-1)(p-2)` legal affine triples per block and compares their predicted Boolean
products. Its worst-case cost is `O(blocks*p^5)`. At the proposed shipping setting
`p=41, blocks=2`, the self-test measured 154,417 exact membership tests and 0.558137
seconds for one instance; the eight-seed reference panel used 911,832 tests and
1.706585 seconds total.

The compact route takes at most 24 modular operations per block (48 at the proposed
shipping setting): a centered-third-moment ratio determines the column multiplier,
then two first-moment identities determine the row multiplier and translation. This
is a real compression gap, so the existence of an efficient method alone is **not**
the rejection reason. The rejection is that the statement itself names and displays
exactly those moment summaries, making the compact route discoverable and executable
by the evaluated models. Increasing `p` only padded the matrix around the same
calculation, and adding independent blocks merely repeated it and lengthened the
answer; neither supplied a remaining hardness axis.

## Artifact note

The attempted module is retained as `rejected_gen_1002_1292.py`, as required. An
earlier run incorrectly reported `cap_bound` because the old `escalate()` confused a
large rendered matrix with the **answer** cap, even though the largest tested answer
had only 9 atomic values and 102 characters. That bug was corrected before the final
rerun. The `.meta.json` file still contains the earlier script-owned verdict because
the corrected rerun exhausted the shared API key before the script could write a new
terminal verdict; it must not be interpreted as evidence that an output cap bound
this family.
