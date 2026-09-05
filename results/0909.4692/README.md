# Planar spanning-cycle subgraph isomorphism (arXiv:0909.4692)

> **Status: rejected after a construction-aware audit.** The exact-2-in-4
> closed-neighbourhood attack now retained in the module returns a verified
> cycle on 7/8 seeds at both `n=120` and `n=148`. See [REJECTED.md](REJECTED.md)
> for the Track A failure and the measured Track B comparison. The older oracle
> run was incomplete and is not the basis for the decision.

| Profile field | Value |
|---|---|
| Track | **A candidate — rejected on distributional hardness** |
| Native domain / essentiality | combinatorics / native |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple (an explicit injective vertex map) |
| Intended intuition | duality: in a cubic graph, a Hamiltonian cycle is the complement of a perfect matching |
| Reduction | none |

## The family

This generator turns Frederic Dorn's [*Planar Subgraph Isomorphism Revisited*](https://arxiv.org/abs/0909.4692)
into the spanning-cycle case. The pattern is `C_n`; the host is a cubic planar
graph. The solver returns a cyclic ordering of every host vertex, which is
exactly an injective map of the pattern into the host. Verification checks the
normalization, permutation property, and `n` host edges using integer set
membership only.

Generation is answer-first. Around a known cycle, it samples a noncrossing
perfect matching on the even positions and another on the odd positions, draws
them on opposite sides, and randomly relabels every vertex. The base cycle is
carried through the relabelling as the certificate; no answer-finding algorithm
runs in `make_instance`.

## Why this regime

Section 2 supplies the non-induced definition, so the matching edges may remain
in the host. The Introduction states that Subgraph Isomorphism remains
NP-complete on planar graphs and explicitly lists Hamiltonicity as a special
case. Theorem 1 also identifies the easy boundary that must be avoided: a fixed
`k`-vertex planar pattern can be found and constructed in `2^{O(k)} n` time.
Here `k=n` grows with the instance. That was intended as a Track A claim about
the generated distribution, not an inference from worst-case NP-completeness.
It failed: the later exact-2-in-4 closed-neighbourhood attack found a verified
cycle on 7/8 seeds at `n=120` and again on 7/8 at `n=148`.

## Worked demo

Seed 731 at `demo` asks for a spanning cycle in the graph

```text
V = {0,1,2,3,4,5,6,7}
E = {0-4, 4-5, 1-6, 6-7, 0-7, 3-4,
     2-3, 1-2, 0-5, 5-7, 1-3, 2-6}
```

The answer is `[0,5,4,3,2,1,6,7]`.
`verify(inst, answer)` returns `(True, "ok")`; deleting the final `7` returns
`(False, "wrong_length:7_expected_8")`. A person can solve this eight-vertex
demo on paper by tracing edges from 0. The larger presets deliberately remove
that hand-scale search option.

## Difficulty and gates

| Preset | n | Status |
|---|---:|---|
| demo | 8 | worked example; skipped by hardener |
| easy | 80 | rejected as shipping rung: Gemini and Grok solved it |
| medium | 120 | rejected: construction-aware attack solved 7/8 |
| hard | 148 | rejected: construction-aware attack solved 7/8 |

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted witnesses verify |
| G2 | 5/5 corruptions rejected with five distinct reason codes |
| G3 | prose/tag round-trip verifies; garbage returns `None` |
| G4 | 0/200,000 normalized random permutations valid; language size `(119!)/2` |
| G5 | **failed**: exact-2-in-4 DPLL solved 7/8; 352,059 total nodes, median 13,973 |
| G6 | **failed**: the new construction-aware entry has 7 successes in 8 attempts |
| G7 | `n=240` builds and its planted witness verifies |
| G8 | 60/60 relabelling invariance and witness-transport checks; 20/20 unrelated keys distinct |
| no-tool caps | **failed**: 490 characters and 120 atoms fit, but the shortest reproducible post-insight route has median 13,973 branch nodes |
| diagnostic arms | incomplete; no further paid calls were run after the local attack invalidated the family |

Timings above are the recorded second full local run and are machine-dependent.

## Historical oracle loop

| Preset | Model / seed | Result | Exact reason |
|---|---|---|---|
| easy | Claude Sonnet 5 / 351901605 | failed | response budget exhausted, no witness emitted |
| easy | Gemini 3.1 Pro / 1749103958 | solved | witness verified |
| easy | Grok 4.6 / 2134808312 | solved | witness verified |
| medium | Gemini 3.1 Pro / 1159637014 | failed | returned 122 entries; 120 required |
| medium | Claude Sonnet 5 / 1574699909 | failed | response budget exhausted, no witness emitted |
| medium | Grok 4.6 / 142998374 | error | 900-second timeout; correctly not counted |

| G9 arm at medium | Solved / completed attempts | Conclusion |
|---|---:|---|
| bare | 0 / 2 | incomplete; third valid attempt is still required |
| structural hint | 0 / 0 | not run |
| placebo hint | 0 / 0 | not run |

There is no hinted-minus-placebo conclusion. The missing
`g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl` are intentional:
creating them by hand would fabricate evidence, and further calls would not
repair the already failed adversary panel.

## Use

```python
from rejected_gen_0909_4692 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=42, **DIFFICULTY["medium"])
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

This snippet is for reproducing the retained attempt only. Do not emit it into
the corpus:

```bash
python3 results/0909.4692/rejected_gen_0909_4692.py
```

## Caveats

- The paper's NP-completeness statement is worst-case evidence, not a theorem
  about this random two-page distribution. The attack and oracle measurements
  are therefore load-bearing.
- The 0/200,000 guess result concerns uniform normalized permutations. It does
  not estimate a solver using planarity or learned graph priors.
- The paper's sphere-cut dynamic program was not reimplemented. The panel uses
  the natural cubic specialization—enumerate perfect matchings and test whether
  the complementary 2-factor is connected—as its exact domain attack.
- The decisive exact-2-in-4 attack is exponential in the worst case; its role is
  empirical and distribution-specific. Its 7/8 success rate is nevertheless
  enough to fail the required zero-success Track A panel.
- A full combinatorial planar-embedding attack was not needed after that
  failure and remains unimplemented.
