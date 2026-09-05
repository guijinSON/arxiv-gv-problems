# Rejected: arXiv 1204.4298

## Decision

No family from this paper clears **H**.  The experimental family clears G and V,
but fails hardness on both tracks:

- **Track A fails at STEP 0.**  Theorem 1 is constructive.  Procedure 2 builds a
  connected dominating tree, and the subsequent cases explicitly colour its
  edges and the edges into its neighborhood.  More decisively for the retained
  experiment, Example 2 directly gives the optimal colouring of its clique-layer
  path: colour boundary `i` by `i` and every within-layer edge by colour 1.
- **Track B fails G6 and the bare oracle loop.**  The proposed affine relabelling
  does create a large mechanical/compact gap, but the compact route is exposed by
  the rendered instance and is reliably executable without tools.

The source is Dong and Li, *Rainbow connection number and independence number of
a graph*, [arXiv:1204.4298](https://arxiv.org/abs/1204.4298).  The exact graph and
colouring definitions are in the Introduction; the constructive upper bound is
Theorem 1 and its proof; the retained family is based on Example 2.

## What was built and what passed

`rejected_gen_1204_4298.py` inverse-generates an invertible affine frame over
`F_p`, uses it to relabel a chain of clique layers, and retains the frame as the
certificate.  Expanding a candidate frame reconstructs every layer and the
paper's colouring.  Verification is exact: modular inversion decodes all
vertices, all graph edges are recomputed, boundary colours are checked to be
distinct on every layer interval, and the `L-1` colours are compared with the
`L-1` diameter lower bound.  Thus:

- G passes by transformation of a known instance: the frame exists before the
  graph is assembled, so generation never solves its output.
- V passes without an oracle or search: it is exact finite-field arithmetic and
  graph comparison.
- The bounded answer is only six field elements (66 characters and 6 atoms on
  the shipping measurement).
- Structure-aware guessing found 0 valid frames in 200,000 trials from
  1,054,182,825,985,282,560 admissible affine frames.
- Exact enumeration at the demo preset found 2 valid frames among 98,784.

These facts do not rescue H: answer-space size is not difficulty.

## The disqualifying attack

At the shipping preset (`n=32`, later-layer widths 4--7), the two vertices of
the first width-two layer are the unique degree-3 vertices.  The rendered closed
neighborhood table makes the following route immediate:

1. Select the two degree-3 vertices; their coordinate difference is the slot
   step, up to its two orientations.
2. Intersect their open neighborhoods; the result is exactly the two vertices
   of the next layer.
3. Try the two next-layer vertices in the two slot positions.  Each trial gives
   the layer step by one vector subtraction.

This is at most eight candidate frames, using a handful of modular vector
subtractions after four table selections.  The implemented
`visible_degree3_twin_endpoint` attack solves **8/8** shipping seeds in 0.0196
seconds total.  It is precisely the fourth in-context attack required for Track
B, and its nonzero success count makes G6 fail.  Omitting it would leave five
nominally failing attacks while hiding the obvious construction-aware one.

## Mechanical cost versus compact route

The honest efficient reference algorithm groups equal closed neighborhoods,
orders their quotient path, and exhaustively aligns affine progressions.  Its
complexity is `O(N^2 + L^2 + w^3 + NLw^2)`.  Across eight shipping seeds it saw
159--174 vertices and 1,122--1,345 edges, solved 8/8, and used:

| measurement | value |
|---|---:|
| counted operations, minimum | 30,454 |
| counted operations, mean | 36,271 |
| counted operations, maximum | 39,752 |
| mean wall clock | 0.0027 s |

The intended affine-twin-path route was conservatively budgeted at 204 exact
operations, but the endpoint specialization above is much shorter: at most
eight frame trials and roughly a dozen small vector operations.  The numerical
gap is therefore real; this is **not** a rejection merely because a polynomial-
time algorithm exists.  It is a rejection because the shortcut is directly
visible and actually succeeds on every gate seed.

## Oracle evidence and stopping point

The script-owned bare hardening run independently confirms the attack.  No hint
was present.

| rung | parameters | solved |
|---|---|---:|
| easy | `n=10, p=101, widths=2..4` | 2/3 |
| medium | `n=20, p=257, widths=3..6` | 3/3 |
| hard | `n=32, p=1009, widths=4..7` | 3/3 |
| escalation 1 | `n=40, p=2003, widths=5..8` | 3/3 |
| escalation 2 | `n=48, p=4001, widths=6..9` | 3/3 |

The harness recorded `verdict: too_easy`.  The last rung already costs 284
intended exact operations.  The next meaningful increase in layers/crowding
would cost at least 324, above the task's 300-operation no-tool ceiling.
Increasing only `p` would make the same exposed subtraction use longer integers;
that would test arithmetic stamina rather than hide the structural route.

## Why the paper has no remaining admissible native family here

The paper proves an upper bound and supplies explicit extremal examples; its own
certificate-producing arguments are constructive.  Its Introduction cites the
external worst-case NP-completeness of deciding `rc(G)=2`, but that statement
does not provide a hard positive distribution, and worst-case hardness does not
make an inverse-planted distribution hard.  Using an unrelated SAT gadget
distribution would replace this paper's contribution with an external
reduction.  The paper's native constructive family has therefore been tested on
Track B and failed, while Track A is ruled out by the certificate-producing
procedure itself.

## Retained evidence

The failed generator is kept as `rejected_gen_1204_4298.py`, including the
successful endpoint attack.  `selftest_report.json` records the resulting G6
failure.  `llm_loop_transcript.jsonl` and `.meta.json` are the untouched files
written by `scripts/harden.py`; the latter records the final `too_easy` verdict.
