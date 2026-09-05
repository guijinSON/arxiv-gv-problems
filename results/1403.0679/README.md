# arXiv:1403.0679 — rejected after certificate-cost audit

This paper does not yield an acceptable hard generator under the stated tracks. The natural sparse-polynomial witness is generated and verified correctly, but Theorem 5.1 computes it directly in `O(log M + T)` operations, where `T` is the number of answer terms. At the attempted 16-term shipping preset, the direct route took 115--117 conservatively counted exact operations and a median 6.74 microseconds.

The earlier draft claimed Track B using a 2.3-million-step scan. That scan was artificial: it visited every integer exponent and rejected nonmultiples of a gcd that it had already computed. Stepping by the gcd gives exactly the paper's 16-iteration formula, so the mechanical route and compact route are the same length. Track A is also false because the formula applies to the entire generated distribution.

See [REJECTED.md](REJECTED.md) for the theorem-level audit, both cost figures, alternatives considered, and the status of the retained evidence. The attempted implementation remains in `rejected_gen_1403_0679.py`; its old self-test and quota-error transcripts are preserved for forensic review and must not be interpreted as a shipping hardness claim.
