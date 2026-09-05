# Rejection: arXiv:2401.02846

## Verdict

No family from this paper that I could justify clears **H**. The native cyclic-starter candidate clears G and V, but it clears neither Track A nor Track B hardness. The built candidate is retained as `rejected_gen_2401_02846.py`.

The source is Forbes and Rutherford, [*Design spectra for 6-regular graphs with 12 vertices*](https://arxiv.org/abs/2401.02846). Section 1 defines a `G`-design as an edgewise decomposition of `K_n` into copies of `G`. Section 4 defines ordered base blocks and develops them by modular multipliers and translations. Lemma 4.7 explicitly lists the graph-201 starters used by the retained candidate. Theorem 5.1 is an existence-spectrum theorem: for the sixteen listed graphs, a design exists exactly when `n = 1 mod 72`. It is not a hardness theorem.

## What passes

- **G passes.** Sample an invertible affine map `x -> ux+t (mod p)` first and carry a published Lemma 4.7 starter through it. Affine transport preserves every developed difference class, so no generated instance is solved during construction.
- **V passes.** The checker expands the multiplier orbit of each of the 36 graph edges and checks, with exact integer arithmetic, that the resulting undirected difference classes are exactly `1,...,(p-1)/2`. It does not read the planted answer.
- The retained implementation also passed its local correctness, corruption, round-trip, sampling, scaling, and canonicalization tests. Those facts do not repair H.

## Why Track A fails

The paper gives no average-case or distributional hardness theorem for recovering these starters. Section 6 says that the authors used backtracking combined with random processes and that direct construction is generally hopeless *unless there is an automorphism of large order*. The candidate distribution deliberately uses exactly the exceptional easy regime: Lemma 4.7's cyclic multiplier-and-translation developments, with a published reference starter exposed in the statement. Therefore neither Theorem 5.1 nor the Section 6 observation supports Track A for this distribution.

## Why Track B also fails

The first draft hid an affine image of the published starter in a pool and marked five planted residues together with marker decoys. Its baseline incorrectly scanned every pair in the 480-element pool. A construction-aware solver gets for free that the generator maps the first two reference coordinates into the marked set, so it only has to scan ordered pairs in the 14-element marked set.

Measured on the eight shipping seeds `800,...,807` at `p=1009`, pool size 480, and 14 markers:

| route | complexity | total exact operations | mean per instance | wall clock | solved |
|---|---|---:|---:|---:|---:|
| marked-pair affine-template scan | `O(m^2 * 12)` | 6,588 coordinate transforms | 823 | 0.001525 s | 8/8 |
| proposed difference-multiplicity shortcut | `O(m^2)` | 1,768 modular operations | 221 | below timer relevance | 8/8 |

The operation ratio is only about 3.7. More importantly, both routes do the same substantive work: enumerate directed marked differences and test the induced affine map. The proposed compact route is not a qualitatively shorter invariant-based solution; it is a constant-factor optimization of the mechanical route. The worst-case advertised compact count is itself 234 operations at the shipping preset. This is precisely the case the Track B rejection rule describes: the mechanical and compact routes are comparable.

The marked-pool wrapper is also not a construction or reduction in the paper. It compiles the search into a planted affine-pattern puzzle whose solution does not require the graph-design structure, even though final verification still expands the design. The retained module now declares `domain_essentiality="discretised_analogue"`, `reduction_kind="convenience"`, and `reduction_source="benchmark_convenience"`; it cannot count as native coverage.

## Disposition and preserved evidence

The implementation has been renamed to `rejected_gen_2401_02846.py` rather than deleted. `selftest_report.json` contains the corrected marked-pair cost. The existing oracle transcripts are retained, but every call in them is an HTTP 403 key-limit error and hence supplies no model-hardness evidence. I did not rerun the costly hardening loop after H failed locally.

A full decomposition would not rescue the family under the current answer contract: already at order 73 it contains 73 ordered 12-vertex blocks, or 876 atomic entries, above G9(c)'s 256-atom cap. The cyclic starter is the right compact certificate; what is missing is an honestly distinct, short recovery route with a large mechanical-cost gap.
