# arXiv:2510.00228 — rejected after domain attack

This paper does **not** ship a generator. The full decision and measurements are
in [REJECTED.md](REJECTED.md). The closest candidate is retained as
`rejected_gen_2510_00228.py` for reproducibility.

The native task was to produce a radio-graceful labeling of a diameter-two
graph. By Theorem 2.4, that is a Hamiltonian path in its antipodal graph, and
verification is an exact permutation plus edge-membership check.

| Item | Result |
|---|---|
| Candidate track | A |
| G — construction | pass: Hamiltonian cycle planted before relabeling |
| V — verification | pass: exact, linear in the submitted ordering |
| H — structural hardness | **fail** |
| Decisive attack | cycle-cover MILP with iterative subtour cuts |
| Attack result | 7/8 at `n=240`, 59.862305 s total |

The paper’s own Singer/polarity labeling is not a Track B fallback.
Construction 3.34 uses 182 modular updates at the largest cap-compliant order
`q=13`, and the route after recognizing the construction still needs those same
182 updates to emit 183 labels. Compressing the answer to the two recurrence
constants makes 120 of 182 structure-aware candidates valid, so it fails guess
resistance instead.

To reproduce the retained candidate’s dependency-free local checks:

```bash
python3 rejected_gen_2510_00228.py > selftest_report.json
```

The recorded external solver measurements are also available in
`attack_audit.json`. The old oracle transcripts contain only OpenRouter HTTP 403
key-limit errors and are retained solely as provenance; they are not hardness
evidence.

Paper: [Radio gracefulness of Moore graphs and beyond](https://arxiv.org/abs/2510.00228).
