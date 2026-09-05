# Rejection: arXiv 2601.04295

Paper: Paulo Henrique Cunha Gomes, [“An explicit family of 30 blocks meeting
every 6-set of [60] in at least two points”](https://arxiv.org/abs/2601.04295).

## Decision

This paper provides generation and exact verification, but no acceptable hard
family. It fails **H on both tracks**. I read the complete LaTeX source,
including the definition in Section 2, Theorem 1 and its proof in Section 3,
the explicit list in Section 4, and the Johnson-space remark in Section 5.

The final Track B prototype passed every local gate, including four attacks at
0/8, but the script-owned hardening loop solved it **9/9** across both vendors
and all three non-demo presets. The preserved module is
`rejected_gen_2601_04295.py`; `llm_loop_transcript.jsonl` and `.meta.json`
contain the matching final run and its `too_easy` verdict.

## What the paper proves and what produces the witness

Section 2 partitions `[60]` into ten disjoint six-point base blocks, pairs the
base blocks, splits each into two triples, and adds the four cross-unions for
each pair. Equivalently, it makes five 12-point components, each partitioned
into four triples, and lists all six unions of two triples. Theorem 1 proves
that every selected 6-set has two points in one listed block.

The proof is already a witness algorithm. Classify the six selected points by
base block. A repeated base block gives a listed witness immediately; otherwise
six occupied base blocks among five pairs give a repeated pair, and the two
triple halves determine the recombined block. This costs at most 14 elementary
classifications plus writing six labels. The answer space for the native fixed
problem is only 30 blocks, so a uniform listed-block guess succeeds with
probability at least `1/30`, failing G4 by five orders of magnitude.

For the construction task itself, the mechanical and compact routes are also
comparable: both write the same 30 blocks, or 180 point occurrences. Using the
equivalent four-triple certificate reduces both routes to the same 60 point
occurrences plus constant bookkeeping. There is no hidden compression problem
in the fixed object.

## Track A failure

The paper contains no hardness result or hard parameter regime. Its only main
result, Theorem 1, is a correctness theorem for an explicit output-linear
construction, and its proof supplies the witnessing block. There is no
worst-case, distributional, average-case, or parameterized hardness statement
on which `hardness_basis` could rely. Declaring Track A would knowingly hide an
efficient algorithm.

## Track B attempt and measured failure

To give Track B its strongest fair chance, the prototype used only native
six-blocks and structure-preserving operations allowed by the generator rules:

1. compose many disjoint copies of the paper's exact 12-point/four-triple
   component;
2. inverse-plant two selected points in different triples of exactly one
   component and at most one point in every other occupied component;
3. carry the unique pair-and-block certificate through multiplication by a
   nonzero residue modulo a displayed prime; and
4. shuffle every listed block.

The standard mechanical algorithm builds a hash set of selected labels and
scans the six entries of each shuffled block. The compact route notices that
the directed modular differences in any block share a repeated step, recovers
the multiplier, undoes the relabeling, and applies Section 2's component
decomposition. Exact measurements over eight seeds were:

| preset | components | blocks | direct-scan membership tests (min / mean / max) | direct-scan mean wall time | compact operations (min / mean / max) | conservative compact bound |
|---|---:|---:|---:|---:|---:|---:|
| easy | 448 | 2,688 | 2,516 / 5,849.25 / 9,454 | 0.000156 s | 105 / 150.50 / 190 | 292 |
| medium | 600 | 3,600 | 317 / 5,768.25 / 17,471 | 0.000153 s | 144 / 172.75 / 208 | 295 |
| hard | 900 | 5,400 | 4,889 / 17,295.38 / 27,842 | 0.000454 s | 139 / 176.25 / 210 | 295 |

Thus an efficient reference algorithm exists and is disclosed: `O(6m)` exact
membership tests for `m` blocks. The compact route is genuinely shorter and
fits the 300-operation cap, so the idea warranted a Track B build rather than a
Step-0 dismissal. It nevertheless fails H because the evaluated no-tool models
reliably find and execute that route:

| preset | OpenAI solved | Google solved | total |
|---|---:|---:|---:|
| easy | 1/1 | 2/2 | **3/3** |
| medium | 1/1 | 2/2 | **3/3** |
| hard | 2/2 | 1/1 | **3/3** |

All nine returned exact pair-and-block witnesses accepted by `verify`. Adding
still more disjoint components cannot change the compact computation; it only
inflates the prompt after the insight has already been found. That would turn
the benchmark into a context-length or transcription test, so `escalate()`
correctly returns `None`. The harness consequently recorded `too_easy`, not a
format or budget bound.

## Other gates and attacks

G and V pass for the prototype: the certificate is inverse-generated and
carried through an exact bijection, while verification uses only integer type,
ordering, selected-membership, listed-block-membership, and containment checks.
Every tested instance has exactly one valid bounded-language answer. At the
provisional easy preset the structure-aware space has 2,427,264 candidates for
the fixed audit seed, exact density `1/2,427,264`, and 1/2,000,000 sampled hits.

The four local attacks all failed 0/8: selected-degree outlier, closest displayed
labels, 256 random restarts, and same displayed six-bucket. The successful
reference scan and compact solver are reported separately as Track B requires.
These local successes do not override the mandatory oracle result.

## Final gate outcome

| Gate | Outcome |
|---|---|
| G — construction with a carried certificate | passes |
| V — cheap exact witness checking | passes |
| H — Track A structural hardness | **fails**: Sections 2–3 give an explicit linear-time construction and witness algorithm, with no hard regime |
| H — Track B no-tool compression | **fails**: final hardening run solved 9/9 through the hard preset |

This is therefore a documented rejection, not a native release and not a
`cap_bound`/`budget_bound` park.
