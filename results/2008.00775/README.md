# arXiv:2008.00775 — rejected Track B candidate

**Disposition:** not shippable.  The generator is retained for audit because
G1--G8 pass and the bare oracle loop hardens, but structural hints solve 2/3
attempts at the final preset, so mandatory G9(b) fails.

| Profile field | Value |
|---|---|
| Track | B — an efficient mechanical scan exists |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | other (succinct list colouring) |
| Certificate | exact symbolic vertical parameters |
| Intuition | change of variables: recognize a hidden linear shear |
| Domain essentiality | native; no reduction |

## Problem and trust boundary

This candidate comes from Wanless and Wood, [*A general framework for
hypergraph colouring*](https://arxiv.org/abs/2008.00775), especially the proper
list-colouring definitions in Section 1 and the graph specialization in
Section 3.1.  A component is a complete graph `K_p`.  At slope `m`, its `p`
allowed colours are `(j,x,x*m+b_j(m))` over `GF(p)`.  The solver returns one
shared `x=t_j` per component; the checker accepts it exactly when the resulting
ordinates are pairwise distinct.  Verification is only modular arithmetic and
a collision table, and never reads the planted answer.

Generation samples `t_j` first and forms each public table as
`b_j(m)=Q_j(m)-t_j*m`, where `Q_j` is a generated composition of bijective
affine and coprime-power maps.  Thus the certificate is known by inverse
generation and the induced colours are distinct by construction.

## Hardness claim that was tested

This cannot be Track A.  Section 3.1 explicitly says the `Delta+1` graph case
has a greedy proof, and Section 4 notes that entropy compression often gives
explicit polynomial-expected-time algorithms.  The disclosed Track B
reference scans all vertical parameters in `O(blocks*p^2)`.  At the final
preset it used 208,243 collision checks (0.024 s) on seed 314159 and 1,670,827
checks across eight seeds.  The intended shear route uses 232 modular
operations.  The mechanical/compact gap is real, but G9 showed that models can
execute the compact route once its invariant is named.

## Worked demo

For `make_instance(n=11, blocks=1, layers=2, seed=0)`, the full instance is:

```text
GF(11), one K_11 component
circuit: [7,3,4] [9,7,6]
intercepts: 1:0 3:5 0:7 4:2 9:0 7:7 2:10 10:8 6:6 8:10 5:0
```

The answer `{"vertical_parameters":[6]}` gives `verify(...) == (True,"ok")`.
Changing it to zero gives `(False,"component 0 has an ordinate collision at
slopes 1 and 9")`.  A person can solve this demo on paper by testing eleven
parameters or by evaluating the two-layer circuit.

## Difficulty ladder

| Preset | Requested n / actual p | Components | Layers | Status |
|---|---:|---:|---:|---|
| demo | 11 / 11 | 1 | 2 | hand-scale |
| easy | 521 / 521 | 4 | 7 | bare solved 1/3 |
| medium | 1009 / 1009 | 5 | 7 | bare held; G9 hint rejected |
| hard | 2018 / 2027 | 5 | 7 | not used; no further G9 tuning allowed |

The earlier pre-shift `p=257` rung also held bare 0/3 and failed hinted 2/3;
those transcripts are retained separately.

## Gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and Markdown |
| G4 | pass | 0/200,000 structure-aware random candidates valid |
| G5 | pass | 1 / 1,045,817,322,864,049 exact density; 208,243-check baseline |
| G6 | pass | four attacks at 0/8; reference algorithm at 8/8 |
| G7 | pass | doubled field 1009 to 2027 with five answer atoms |
| G8 | pass | 40 invariant checks, 20 carried witnesses, 20/20 distinct seeds |
| G9 | **fail** | 45 chars, 5 atoms, 232 operations; hinted solved 2/3 |

## Oracle and G9 evidence

| Arm / rung | Solved | Outcome |
|---|---:|---|
| bare, p=521 | 1/3 | harness escalated |
| bare, p=1009 | 0/3 | hardened |
| structural hint, p=1009 | **2/3** | G9(b) failure |
| placebo hint, p=1009 | 0/3 | hardened |

The hinted-minus-placebo solve rate is `+2/3`; the structural sentence conveyed
real useful information.  One placebo failure was an empty length-limited
response and is identified as such in the script-owned transcript.

## Reproducing the retained candidate

```python
import importlib.util
s = importlib.util.spec_from_file_location("g", "rejected_gen_2008_00775.py")
g = importlib.util.module_from_spec(s); s.loader.exec_module(g)
inst = g.make_instance(seed=7, **g.DIFFICULTY["medium"])
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

Run `python3 rejected_gen_2008_00775.py` to regenerate the local gate report.
There is intentionally no `gen_*.py`, so `../../scripts/emit.sh 2008.00775`
refuses to emit this rejected family.

## Caveats

The random-guess result is relative to the declared language of independent
vertical parameters, not all proper list colourings; unrestricted colourings
are more numerous.  The adversary panel does not include a general-purpose SAT
or finite-field polynomial-decomposition package.  The exact vertical scan is
the relevant reference for the stated answer language and succeeds as
expected.  Most importantly, the benchmark difficulty is brittle to naming the
linear-shear invariant, which is why this otherwise valid generator is not
shipped.
