# Verified directed-triangle factors for arXiv:2602.13737

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | modular subset sum (3SUM) |
| Certificate | exact symbolic affine `C3`-factor |
| Intended intuition | symmetry: odd centrally symmetric offset sets reveal their unpaired centers through first moments |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust status

[Molla and Treglown, *Cycle tilings and H-factors in directed graphs*](https://arxiv.org/abs/2602.13737) defines an `H`-factor as vertex-disjoint copies of `H` covering every vertex (Section 1.1) and proves spanning results for prescribed oriented cycles (Theorems 1.5 and 1.7). This generator gives the solver a native directed graph: three copies of `Z/qZ`, with edges between successive parts specified by exact modular offset sets. The answer is three offsets symbolically denoting all `q` translated directed triangles in a `C3`-factor.

Generation is inverse. It chooses the three closing offsets first, adds centrally paired decoys on three separated scales, and applies random translation/unit scaling. The separation proves that only the three centers close; no search solves the completed instance. Every individual planted or decoy residue has the same uniform marginal after the affine randomization. `verify` checks list membership and modular closure, then uses the exact fact that fixed translations of `Z/qZ` are bijections. It never reads `inst["answer"]`. Local enumeration confirms exactly one symbolic factor at the shipping preset, and all nine gates pass.

The modular offset form is a lossless implicit representation of the handed digraph, and the witness expands exactly to its `q` directed triangles; no graph, SAT, or finite-field surrogate replaces the paper's object. The computational core is nevertheless labelled `subset_sum`, because that is honestly what the solver searches inside this structured graph subfamily.

## Why this is Track B

This is not a complexity-theoretic hardness claim. The paper gives extremal existence theorems, not an average-case hardness theorem, and its dense regimes are poor benchmark distributions because they admit many factors. Section 4 itself combines probabilistic partitions, an oriented-Hamilton-cycle theorem, greedy extensions, and absorption. This generator stays sparse and outside those forcing thresholds.

The standard method for this generated distribution is hash-based modular 3SUM: test every `(s_AB,s_BC)` pair and look up `-s_AB-s_BC` in `S_CA`. It takes `O(d²)` exact time and `O(d)` memory. At shipping `d=401`, the full uniqueness-certifying scan checks **160,801 pairs**, costs **482,804 counted operations**, and averaged **0.0235 s** in the recorded final run. It solves 8/8, as expected.

The compact route notices that each odd set consists of reflection pairs plus one center. If `sigma` is its supplied first-moment checksum, the center is `sigma / d (mod q)`. The three centers close and give the factor. Because `q = 1 (mod d)`, the modular inverse is also short to obtain. This route is bounded by **24 exact operations** once the symmetry is recognized; the hard part in context is recognizing it among 1,203 shuffled offsets. The structural hint made this explicit and solved 3/3, while bare solved 0/3.

## Worked demo

`make_instance(n=5, spread=1, seed=3)` renders the following complete problem:

```text
DIRECTED TRIANGLE FACTOR IN A CYCLIC DIGRAPH

All arithmetic below is modulo q = 56; residues are the integers 0 through 55 inclusive.
The vertex set has three labelled parts
  A = {A_x : x in Z/qZ}, B = {B_x : x in Z/qZ}, C = {C_x : x in Z/qZ}.
There are no loops and the only directed edges are:
  A_x -> B_(x+s) for s in S_AB,
  B_y -> C_(y+s) for s in S_BC,
  C_z -> A_(z+s) for s in S_CA.
Every subscript and addition is reduced modulo q.  Each offset set has exactly d = 5 distinct residues; list order has no meaning.

A directed C3-factor is a set of vertex-disjoint directed 3-cycles covering every vertex exactly once.  Submit one in affine symbolic form by giving offsets s_AB, s_BC, s_CA from the corresponding sets whose sum is 0 modulo q.  Such a triple denotes, for every x in Z/qZ, the cycle
  A_x -> B_(x+s_AB) -> C_(x+s_AB+s_BC) -> A_x.
Translations are bijections, so these q cycles cover all 3q vertices exactly once.  Extra edges do not invalidate a cycle.

For exact auditing, checksum(S) is the sum of the displayed residues in S, reduced modulo q.
S_AB (checksum 13): [19, 25, 0, 31, 50]
S_BC (checksum 32): [22, 40, 2, 3, 21]
S_CA (checksum 11): [49, 45, 46, 48, 47]

Order in the submitted three-entry list is fixed as AB, BC, CA; offsets cannot be moved between layers.  Give integer residues, not negative representatives, and do not add fields.
Give your final answer inside <answer></answer> tags as exactly one JSON object of the form {"offsets":[s_AB,s_BC,s_CA]}.
Example syntax: <answer>{"offsets":[0,1,2]}</answer>
The example illustrates syntax only and is not an answer to this instance. Output nothing else inside the tags.
```

Since `5^(-1) = 45 (mod 56)`, the three checksums give `(25,40,47)`, whose sum is `112 = 0 (mod 56)`. Thus `<answer>{"offsets":[25,40,47]}</answer>` returns `(True, "ok")`. Dropping the final offset returns `(False, "offsets must be a list of exactly three entries")`. A person can solve this demo on paper with three short modular multiplications.

## Difficulty presets

The displayed modulus varies slightly with the seed; the table gives seed 0. The answer always remains three integers.

| Preset | Offsets/layer `d` | Spread | Seed-0 modulus `q` | Candidate triples | Ships? |
|---|---:|---:|---:|---:|---|
| demo | 5 | 1 | 56 | 125 | no; hand example |
| easy | 201 | 4 | 128,960,194 | 8,120,601 | no; one bare oracle solved it |
| **medium** | **401** | **6** | **3,435,796,873** | **64,481,201** | **yes** |
| hard | 801 | 8 | 65,331,021,025 | 513,922,401 | available |

`escalate` increases both offset crowding and numerical spread while the certificate remains three offsets.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted factors verify; 12/12 answers JSON-round-trip |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged, prose-surrounded, fenced JSON round-trips; garbage returns `None` |
| G4 | 0/200,000 structure-aware guesses; exact probability `1/64,481,201 = 1.55084e-8` |
| G5 | exactly 1 valid symbolic factor; reference scan 160,801 probes / 482,804 operations / 0.0235 s mean |
| G6 | four attacks all 0/8; disclosed reference and compact algorithms both 8/8 |
| G7 | doubled request gives `d=803`, candidate space 517,781,627, and the same three-offset answer shape |
| G8 | 80/80 affine/reorder/rotation invariance checks and carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | 49 characters, 13 estimated tokens, 3 atoms, 24 intended operations |

The failing G6 attacks are regular-degree/closest-zero outlier selection, a greedy fixed-first-offset scan, 256 random restarts, and the obvious numerical-median ansatz. The successful quadratic modular 3SUM scan is reported separately because Track B expects it to work.

## Oracle loop

| Preset | Model | Seed | Solved | Exact result |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 597667332 | no | parsed; offsets did not close |
| easy | Google Gemini 3.8 Flash | 1100632829 | yes | verified |
| easy | OpenAI GPT-5.6 Terra | 53869229 | no | parsed; CA offset not allowed |
| **medium** | Google Gemini 3.8 Flash | 147815291 | no | no final witness emitted within its response |
| **medium** | OpenAI GPT-5.6 Terra | 1600991294 | no | parsed; CA offset not allowed |
| **medium** | OpenAI GPT-5.6 Terra | 438166601 | no | parsed; CA offset not allowed |

The script-owned verdict is `hardened` at medium after one escalation, with no service errors. The one unparsed medium reply ends mid-analysis and contains no answer tag, so it is not an output-contract false negative.

## G9 diagnostics

| Arm | Solved/attempts | Service errors | Interpretation |
|---|---:|---:|---|
| bare shipping prompt | 0/3 | 0 | hardened |
| structural hint | 3/3 | 0 | symmetry recognition unlocks the route |
| placebo hint | 1/3 | 0 | prompt perturbation alone sometimes helps |

`hinted - placebo = 1 - 1/3 = 0.6667`. The controlled gap is strong evidence that the declared symmetry, rather than mere extra prompting, supplies useful information. Hinted ease is diagnostic and expected for this Track B family. The answer is 49 characters/3 atoms at worst over 32 shipping seeds, and the post-insight route is at most 24 exact operations.

## Use

```python
import json
import gen_2602_13737 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=17, **params)
question = g.render(inst)
wire = f"<answer>{json.dumps(inst['answer'])}</answer>"
answer = g.parse_answer(wire)
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2602.13737 20 medium
```

## Caveats

- This is a polynomial-time-solvable, deliberately structured Track B distribution. It is not evidence that general directed `C3`-factor search is hard, and it does not sample the dense threshold regime of Theorem 1.5 or 1.7.
- The cyclic/affine specialization and redundant checksums are artificial. A solver with a CAS, a short script, or the stated structural hint should solve it quickly; that is the intended boundary.
- The exact guess density is uniform over triples already chosen from the three allowed sets. It does not model a solver using the checksums, symmetry, or planting prior.
- The 24-operation count starts after recognizing which invariant matters. It counts modular inverse/center recovery, closure checks, and output, not visual reading of the 1,203 input residues.
- `canonical_key` is exact under offset-list order, common unit scaling, independent layer translations, cyclic layer rotation, and their tested compositions. It is a strong generated-family invariant, not a complete isomorphism algorithm for arbitrary digraphs.
- No SAT/ILP encoding or spectral attack was run. The graph is exactly regular, and the successful hash-based modular 3SUM reference algorithm is more direct for this representation.
