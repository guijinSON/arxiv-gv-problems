# Transversal matching completion over an implicit graph collection

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | permutation |
| Certificate form | exact symbolic (eight vectors in `F_p^2`) |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This generator is based on Cheng and Staden, [*Transversals via regularity*](https://arxiv.org/abs/2306.03595). It gives a solver an implicitly represented bipartite graph collection, a matching whose left vertices are already embedded, and distinct colours already assigned to its edges. The solver supplies the eight missing right-vertex images. The answer completes the paper's two injective maps: the vertex embedding `tau` and edge-to-colour map `sigma`. Verification only performs exact arithmetic in `F_p`, graph-membership checks, and injectivity checks.

Generation is inverse, not search: it samples distinct left and right images first and evaluates their colours. Because every displayed affine swap layer is a bijection, every constraint has exactly one right image. The planted answer is therefore known by construction and is not consulted by `verify`.

## Why this is Track B

Section 1.7 gives the exact definition of a transversal embedding, Section 1.2 gives the equivalent 3-uniform-hypergraph representation, and Lemma 3.1 in Section 3 supplies the partial-embedding and candidate-set viewpoint used here. The paper's easy regime is a dense regular template: Lemma 2.2 supplies many typical choices, and the proof of Lemma 3.1 deletes bad candidates and chooses any survivor greedily. This generator is deliberately sparse and does **not** claim the hypotheses of the main blow-up theorem.

An efficient algorithm is known and included. Reverse the `L` displayed affine layers for every required colour, then add the fixed left image. It costs `O(mL)`, succeeds on 8/8 shipping instances, and uses exactly 288 counted field operations (about 19 microseconds in the final self-test). The mechanical paper-style alternative scans `F_p^2`: `O(mp^2L)`. At shipping size its exact eight-seed mean is 246,524,121 candidate tests and 8,874,868,343 counted operations. A real 100,000-test prefix was timed for every seed; extrapolation from those prefixes averaged 363 seconds. The full scans were not run, and the report labels that projection rather than presenting it as a measurement.

The compact route is to see each layer

```text
(u,v) -> (v, u + a*v + b)
```

as a change of coordinates with inverse `(u,v) -> (v-a*u-b, u)`, apply inverses in reverse order, and translate by the fixed left image. The required arithmetic count stays below the no-tool cap even as the ambient field grows.

## Worked demo

This is the full rendered data of `make_instance(seed=0, n=7, m=2, layers=1)` (the output-contract prose is included in compact form without omitting a convention):

```text
Complete a partial transversal embedding of a matching.

Arithmetic is in F_7; vectors are ordered pairs [u,v]. The host has disjoint
classes L and R indexed by F_7^2 and a graph G_c for every c in F_7^2.
Apply P's layers in order:
  0: (u,v) -> (v, (u + 4*v + 6) mod 7)
The edge L_x--R_y belongs to G_c exactly when P(y-x)=c, with coordinatewise
subtraction modulo 7.

H has vertices 0,1,2,3 and matching edges (0,1),(2,3).
  edge 0: left image L_[3, 0], required colour [4, 0]
  edge 1: left image L_[3, 3], required colour [3, 0]
Give, in edge order, two distinct right images in F_7^2. Order matters,
repetitions are forbidden, and coordinate bounds 0..6 are inclusive.

Give the JSON list inside <answer></answer> tags and nothing else in the tags.
Example syntax: <answer>[[0,0],[0,1]]</answer>
```

The valid answer is `<answer>[[2,4],[6,6]]</answer>`, and `verify` returns `(True, "ok")`. Changing the first image to `[0,0]` returns `(False, "edge 0 is not present in its assigned colour graph")`. A person can solve the demo by hand: undo the single layer and add each left vector modulo 7.

## Difficulty presets

| preset | `p=n` | matching edges `m` | layers `L` | ambient candidates per edge | hardening result |
|---|---:|---:|---:|---:|---|
| demo | 7 | 2 | 1 | 49 | hand-solvable; skipped by harness |
| easy | 2,027 | 8 | 7 | 4,108,729 | lower-rung version solved 3/3 |
| medium | 4,057 | 8 | 8 | 16,459,249 | lower-rung version solved 3/3 |
| **hard (ships)** | **8,117** | **8** | **8** | **65,885,689** | **held 0/3 solved** |

Earlier rungs `p=101,251,499,1009` were also solved 3/3. Difficulty escalation grows the field while the witness remains eight vectors; the answer length does not drive the hardness.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 planted verifies | pass | 16/16 across every preset and four seeds |
| G2 corruption | pass | drop, swap, duplicate, empty, and out-of-range all rejected with five distinct reasons |
| G3 round trip | pass | fenced JSON with surrounding prose parsed exactly; answer is JSON-native |
| G4 guess resistance | pass | 0/200,000 uniform ordered injective maps; exact language size at shipping is `355081912948037932694464502535465924272247153852351554453957760` |
| G5 density + baseline | pass | exact valid count 1 by bijectivity; demo brute force also counts 1; reference 288 ops; scan mean 246,524,121 tests / 8.875B ops |
| G6 adversaries | pass | all four attacks 0/8; exact inverse reference solves 8/8 |
| G7 scaling | pass | modulus 8,117 -> 16,249; search space grows and witness stays eight vectors |
| G8 canonical key | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 suitability | pass | 97 characters, about 25 tokens, 16 atomic coordinates, 288 intended operations |

The G6 attacks were: lexicographically smallest-vector outlier, a 64-candidate local greedy window, 256 uniform restarts, and the in-context ansatz that reverses only the final layer. Each recorded zero successes in eight shipping instances.

## Bare oracle loop

The final transcript was produced by `scripts/harden.py` with two vendors and fresh seeds. `ok` means a parsed witness verified; failure reasons are exact verifier diagnostics.

| round / parameters | seed | model | result |
|---|---:|---|---|
| 0: `p=101,L=3,m=6` | 663062486 | Gemini 3.8 Flash | solved (`ok`) |
| 0 | 1711346487 | GPT-5.6 Terra | solved (`ok`) |
| 0 | 283408379 | Gemini 3.8 Flash | solved (`ok`) |
| 1: `p=251,L=4,m=8` | 286513993 | Gemini 3.8 Flash | solved (`ok`) |
| 1 | 572956264 | GPT-5.6 Terra | solved (`ok`) |
| 1 | 1365712292 | Gemini 3.8 Flash | solved (`ok`) |
| 2: `p=499,L=5,m=8` | 1102985696 | GPT-5.6 Terra | solved (`ok`) |
| 2 | 1983721903 | Gemini 3.8 Flash | solved (`ok`) |
| 2 | 1330875117 | Gemini 3.8 Flash | solved (`ok`) |
| 3: `p=1009,L=6,m=8` | 384453063 | GPT-5.6 Terra | solved (`ok`) |
| 3 | 1843047290 | Gemini 3.8 Flash | solved (`ok`) |
| 3 | 539095115 | GPT-5.6 Terra | solved (`ok`) |
| 4: `p=2027,L=7,m=8` | 499119867 | GPT-5.6 Terra | solved (`ok`) |
| 4 | 1471803888 | Gemini 3.8 Flash | solved (`ok`) |
| 4 | 712896821 | Gemini 3.8 Flash | solved (`ok`) |
| 5: `p=4057,L=8,m=8` | 114578600 | GPT-5.6 Terra | solved (`ok`) |
| 5 | 1229787075 | Gemini 3.8 Flash | solved (`ok`) |
| 5 | 1029656148 | GPT-5.6 Terra | solved (`ok`) |
| **6: `p=8117,L=8,m=8`** | **1606232** | **Gemini 3.8 Flash** | failed: edge 3 wrong |
| **6** | **488458758** | **GPT-5.6 Terra** | failed: edge 2 wrong |
| **6** | **1095100952** | **GPT-5.6 Terra** | failed: edge 0 wrong |

## G9 three-arm diagnostic

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0/3 | shipping level held |
| structural hint | 0/3 | naming bijectivity did not unlock exact execution |
| placebo hint | 1/3 | one independent instance was solved |

`hinted - placebo = -1/3`. On this small sample the structural hint bought nothing and may have distracted. This weakens the claim that failures isolate discovery of the stated change of variables: the lower rungs show that models do discover the inverse, while the shipping failures appear to involve executing 288 modular operations reliably. The family still meets the formal G9(c) cap, but this interpretation is a real caveat, not evidence for the hint.

## Use

From this directory:

```python
import gen_2306_03595 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit examples with:

```bash
bash scripts/emit.sh 2306.03595 20
```

## Caveats

- This is native coverage of the paper's graph-collection and transversal-map objects, but it covers the Section 3 partial-embedding machinery, not the main theorem's spanning dense-template regime. The host colour graphs are perfect matchings and are far outside the paper's superregular density hypotheses.
- Track A would be false. The reverse-layer algorithm is explicit, exact, and fast; the benchmark claim is only no-tool compression.
- `P(random guess)` uses the strongest natural statement-only prior implemented here—uniform ordered injective right maps. It says nothing about a solver that recognizes and inverts the layers.
- The full lexicographic scan was not timed. Its node and arithmetic counts are exact after decoding the unique targets, but its wall time is an extrapolation from measured 100,000-node prefixes.
- The adversary panel does not include SAT/SMT, spectral, or generic graph-isomorphism software. Those are not the standard attack for this explicit finite-field permutation equation; exact inverse evaluation is, and it is included as the successful Track B reference.
- `canonical_key` proves invariance under constraint order, independent translations, and common `GL(2,p)` changes of coordinates. It does not attempt arbitrary nonlinear isomorphism of the enormous implicitly represented graph collection.
- The G9 result suggests arithmetic reliability is more load-bearing than the claimed structural hint at shipping size. Consumers seeking a pure “find the invariant” test should filter or down-weight this family accordingly.
