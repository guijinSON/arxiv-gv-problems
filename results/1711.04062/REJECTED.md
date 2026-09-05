# Rejected: arXiv:1711.04062

The candidate is rejected for the current no-tool corpus. The construction and
checker clear G and V, but H is not supportable for the implemented Track A
distribution, and the paper's faithful path problem fails Track B/G9(c).

## Track A finding

The retained generator asks for a non-backtracking degree-2 isogeny walk ending
at an **exact coordinate-normalized Weierstrass model**. Section 9 of the paper
defines the relevant isogeny graph on j-invariants, and Section 11, Theorem 47
proves that this j-invariant graph is connected, 3-regular for degree 2, and
Ramanujan. That theorem does not transfer the claimed hardness to the module's
coordinate-model lift. The inconsistency is executable: `canonical_key`
quotients endpoints by j-invariant, while `verify` requires exact coefficient
equality. Consequently the actual generated distribution lacks the cited Track
A hardness basis.

The mismatch was reproduced on an 8-step instance by applying the paper's
coordinate change `x=u^2*x'`, `y=u^3*y'` to the target only. The target's
j-invariant and `canonical_key` stayed unchanged, while `verify` returned
`(False, "replayed path ends at a different curve model")` for the original
path. The corrected G8 gate therefore fails; this is not merely a documentation
disagreement.

Changing `verify` to accept the terminal j-invariant would repair fidelity, but
would expose the second blocker below.

## Track B and G9(c) finding

Section 12, Problem 3 states the isogeny-path problem and its birthday
meet-in-the-middle attack. Section 13 makes a CGL preimage exactly a path from
the fixed start j-invariant. Section 14.2 specializes the mechanical attack on
a hidden degree-`2^e` walk to `O(2^(e/2))` time and storage.

At the candidate's `e=58` setting:

- mechanical cost: a `2^29 = 536,870,912`-entry smaller frontier
  (the retained full-frontier estimate, including constants on both
  sides, is 1,342,177,280 leaves);
- compact route after recognizing the collision structure: the same balanced
  meet-in-the-middle search, still on the `2^29` scale;
- allowed intended route: at most 300 exact operations.

For the paper's actual graph, `p=2^61-1` gives
`floor(p/12)+1 = 192,153,584,101,141,163` vertices by Theorem 47, so the generic
birthday estimate is about 438,353,264 graph steps. This is comparable to the
known-length attack, not a short route hidden inside a large mechanical one.
Thus Track B fails H's compression test and G9(c) by over six orders of
magnitude. The old value 290 was only the cost of checking a supplied witness;
the prompt explicitly excludes checker replay from the intended-route count.

## Easy regimes checked

Section 12 says that a supplied kernel yields the isogeny through Vélu's
formulas in quasi-linear time in the kernel size, and that explicit isogenies of
known degree have `O(d^2)` or `O(d^3)` algorithms. Section 9 describes the rigid
ordinary isogeny-volcano regime. These fail Track A rather than providing a
short, nontrivial Track B alternative. The paper gives no compact route from a
generic supersingular endpoint to its planted CGL preimage.

The implementation is retained as `rejected_gen_1711_04062.py`, together with
its reports and script-owned transcripts. The transcripts contain only HTTP 403
key-limit errors and are not hardness evidence.
