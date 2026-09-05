# arXiv:2302.04845 — rejected after Step 0 audit

No generator is shipped. The full decision, theorem references, measured
mechanical costs, and compact-route comparison are in
[REJECTED.md](REJECTED.md).

The raw aggregate measurements are in `rejection_measurements.json`.

The earlier prototype is retained as `rejected_gen_2302_04845.py` because it
had already been built. Its self-test report is not shipping evidence: the
prototype overstated its Track B mechanical cost by scanning 9,998 moduli even
though Euclid's algorithm recovers the planted modulus directly. The existing
oracle transcript contains only HTTP 403 account-limit errors and supplies no
hardness evidence.
