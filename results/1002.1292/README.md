# Mod/Resc parsimony generator audit

| profile field | attempted value |
|---|---|
| Track | B -- no-tool compression |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | compact affine specification of Boolean Mod/rescue matrices |
| Intended intuition | affine transformation of first and centered-third moments |
| Domain essentiality | native |
| Final status | **rejected: H fails on Track B** |

This directory records an attempted exact family based on [Nor et al., *Mod/Resc
Parsimony Inference*](https://arxiv.org/abs/1002.1292). The solver receives the
paper's Boolean compatibility matrix and must return affine triples defining Boolean
Mod and rescue factor matrices. Verification expands those triples, recomputes every
entry of the paper's asymmetric Boolean product, and checks a fooling set proving
the submitted width is minimal.

The construction and checker are sound, but the problem is not hard enough for this
corpus. Section 3, Theorem 1 equates the paper's factorization with bipartite biclique
edge cover; Theorem 2 gives only worst-case NP-hardness. Section 4 gives an
`O(N^3)` kernel and an exact FPT algorithm parameterized by the factor width, so this
could never be an honest Track A family. The attempted Track B route also fails:
the prompt displays exactly the first- and third-moment summaries needed to recover
the affine parameters, and both oracle vendors repeatedly did so.

## Evidence

| measurement | result |
|---|---:|
| Planted certificates | 16/16 verified across all presets |
| Corruptions | 5/5 rejected with distinct reasons |
| Structure-aware random guesses | 0/200,000 |
| Proposed shipping answer space | 4,090,881,600 |
| Exact valid answers at proposed shipping seed | 1 |
| Mechanical reference algorithm | 154,417 membership tests, 0.558137 s |
| Compact intended route | at most 48 modular operations |
| Adversary panel | four attacks at 0/8; reference enumeration at 8/8 |
| Canonical-key tests | 80/80 real relabellings invariant; 20/20 unrelated keys distinct |
| Proposed shipping answer size | 63 characters, 6 atoms |

The corrected hardening transcript defeated every named rung and the first custom
escalation:

| round | parameters | solved / usable attempts |
|---:|---|---:|
| 0 | `p=41, blocks=2` | 2/3 |
| 1 | `p=71, blocks=2` | 3/3 |
| 2 | `p=101, blocks=2` | 2/3 |
| 3 | `p=101, blocks=3` | 3/3 |

At `p=167, blocks=3`, one further exact solution was recorded before the shared
OpenRouter key reached its total limit. Errors are not model failures. See
[REJECTED.md](REJECTED.md) for the full decision, including the measured mechanical
cost and compact-route length.

## Retained module

The implementation is preserved as `rejected_gen_1002_1292.py`. It is deterministic
given `(n, seed)`, standard-library complete, and its `verify` function does not read
the planted answer. To inspect its demo:

```python
import rejected_gen_1002_1292 as g

inst = g.make_instance(seed=0, **g.DIFFICULTY["demo"])
print(g.render(inst))
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

Do not emit or submit this as an accepted generator. The old G9 transcripts contain
only API-limit errors and provide no diagnostic evidence. The current `.meta.json`
also retains an earlier, invalid `cap_bound` verdict because the corrected hardening
run exhausted the shared key before writing a terminal verdict.

## Caveats

The random-guess figure concerns only the declared uniform affine-triple prior; it
does not measure a solver using the displayed moments. That distinction is precisely
why the large answer space did not translate into hardness. A general SAT/SMT or
biclique-cover implementation was not needed to reject the family: the much cheaper
in-context moment route already solved it across vendors and sizes.
