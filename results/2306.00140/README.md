# Verified generator for arXiv:2306.00140

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | exact symbolic automorphism |
| Intuition | invariant: normalize a layer's first-coordinate sum by `h_b` |
| Domain essentiality | native; no reduction |

## Problem and trust model

[Polhill–Davis–Smith–Swartz, *Genuinely nonabelian partial difference sets*](https://arxiv.org/abs/2306.00140) defines a PDS by an exact group-ring identity in Definition 3.1 and identifies it with a strongly regular Cayley graph in Lemma 3.2. Theorem 4.8 constructs the triangular-graph PDS in the nonabelian group `C_p semidirect C_((p-1)/2)` for primes `p = 3 mod 4`; Remark 4.9 writes the PDS as five group-ring pieces.

An instance gives that group, the paper's PDS `D`, and exact first and second coordinate moments from many automorphic images `phi_(u,w)(D)`. Exactly two rows come from one image; every decoy row comes from an independent image sampled from the same distribution. The solver returns the symbolic automorphism, including its action on the two generators. `verify` checks the finite-field identities and moment equations exactly, without floats and without reading `inst["answer"]`.

Generation is a structure-preserving transformation, not a solve: `(u,w)` is sampled first, two rows are evaluated from it, and decoys are evaluated from independently sampled automorphisms. The executable base certificate checks the regular affine action used in Theorem 4.8; exhaustive group-ring multiplication is also cross-checked at `p=7` and `p=11`.

## Why Track B

Track A would be false. Remark 4.9 is already an explicit construction, and this decoding task has an exact polynomial-time algorithm: recover every row independently by centered-second-moment elimination and modular square-root extraction, then count repeated automorphisms. Its complexity is `O(d log p)`; at the shipping preset (`p=1,000,003`, `d=152`) it solved in 0.0017 seconds and 11,856 counted field operations.

The shorter route notices that `sum/h_b = 4w - 2u(m-1)` is independent of the layer. It fingerprints all rows, performs centered recovery only on the repeated fingerprint, and costs 230 exact operations. That is within the no-tool cap but is not a mechanically comfortable calculation in context. The paper's easy/construction regime is deliberately acknowledged: `p = 3 mod 4` makes the quadratic residues and their negatives partition the nonzero field elements, while the paper notes this construction fails for `p = 1 mod 4` and reports GAP nonexistence checks for several other triangular graphs.

## Worked demo

The demo is hand-solvable: there are only `3 * 7 = 21` admissible `(u,w)` pairs, or one can use the normalized-sum invariant and a single centered moment.

```text
GENUINELY NONABELIAN PARTIAL DIFFERENCE SET: MOMENT WITNESS

All arithmetic in first coordinates is modulo the prime p=7.  Second
coordinates are modulo t=3.  Let m=2, which has multiplicative order t
modulo p.  The nonabelian group G consists of pairs (a,b), with

  (a,b)*(c,d) = (a + m^b*c mod p, b+d mod t).

The identity is (0,0).  Let D be the following subset of G.  In layer b=0 it
contains (1,0) and (-1 mod p,0).  In every layer 1 <= b < t, put q_b=m^b mod p;
the four first coordinates in D are

  0,  -q_b mod p,  1,  1-q_b mod p.

This D is a (21,10,
5,4) partial difference
set: the identity is excluded, D is inverse-closed, and each nonidentity g has
exactly lambda ordered representations x*y^(-1) when g is in D and exactly mu
otherwise.

For 1 <= u < p and 0 <= w < p define h_0=0 and
h_b=1+m+...+m^(b-1) mod p, and define

  phi_(u,w)(a,b) = (u*a + w*h_b mod p, b).

This is a group automorphism whenever u is nonzero.  To make its description
unique, this problem permits only u that are quadratic residues modulo p
(equivalently u^t=1 mod p).  The decoded PDS is phi_(u,w)(D).

For a nonzero layer b, its four decoded first coordinates are denoted x_1,...,x_4.
An observation row lists q=m^b, h=h_b, and the exact residues

  sum = x_1+x_2+x_3+x_4 mod p,
  sum_sq = x_1^2+x_2^2+x_3^2+x_4^2 mod p.

For exact arithmetic it also lists h_inv=h^(-1),
center_den_inv=[4*(q^2+1)]^(-1), and four_h_inv=(4*h)^(-1), all
modulo p.  These are redundant data: a valid row must satisfy the displayed
inverse identities.

Here are 2 observation rows; their order is irrelevant:
  1: b=2, q=4, h=3, h_inv=5, center_den_inv=3, four_h_inv=3, sum=0, sum_sq=6
  2: b=1, q=2, h=1, h_inv=1, center_den_inv=6, four_h_inv=2, sum=0, sum_sq=3

Exactly one permitted pair (u,w) matches at least 2
rows.  The other rows are decoys made by the identical construction from
independent permitted automorphisms.  Find the unique matching pair.

Your certificate must be one JSON object with exactly these fields:
  "type": "automorphism"
  "scale": u
  "shear": w
  "generator_images": {"sigma":[u,0], "tau":[w,1]}
Coordinates and residues are least nonnegative integers.  Array order matters;
no entries may be omitted or repeated.

Give your final answer inside <answer></answer> tags as exact JSON.
Example: <answer>{"type":"automorphism","scale":1,"shear":0,"generator_images":{"sigma":[1,0],"tau":[0,1]}}</answer>
Output nothing else inside the tags.
```

For seed 5, the answer is:

```json
{"type":"automorphism","scale":4,"shear":2,"generator_images":{"sigma":[4,0],"tau":[2,1]}}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the tau image by `[4,0]` returns `(False, "tau generator image must equal [shear, 1]")`.

## Difficulty presets

| Preset | Prime `p` | Rows | Candidate space | Compact operations | Status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 2 | 21 | 34 | hand example |
| easy | 100,003 | 22 | 5,000,250,003 | 92 | one bare oracle solved during the first ladder run |
| medium | 300,007 | 77 | 45,001,950,021 | 156 | bare held, but the structural hint solved 2/3; rejected by G9(b) |
| hard | 1,000,003 | 152 | 500,002,500,003 | 230 | **shipping**; bare and hinted both held |

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted instances verified; direct group-ring checks passed at 7 and 11 |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged JSON round-trip passed; garbage returned `None` |
| G4 | 0 hits / 200,000 structure-aware guesses; exact construction probability 1.99999e-12 |
| G5 | one witness by construction, sample 0/200,000; reference solve 11,856 operations, 0.0017 s |
| G6 | raw outlier, zero-shear greedy, 256 restarts, and scale-one ansatz: each 0/8 |
| G7 | primes increase across all presets; doubled instance at 2,000,039 verified with unchanged answer size |
| G8 | 80 invariance checks and 60 carried-witness checks passed; 20/20 unrelated keys distinct |
| G9 | bare 0/3, hinted 0/3; answer 110 chars / 28 estimated tokens / 7 atoms; route 230 operations |

## Shipping oracle loop

| Preset | Model | Seed | Solved | Recorded reason |
|---|---|---:|---|---|
| hard | OpenAI GPT-5.6 Terra | 2012920370 | no | candidate matched 0 rows |
| hard | Gemini 3.1 Pro Preview | 415609237 | no | candidate matched 0 rows |
| hard | Claude Sonnet 5 | 1219725049 | no | empty length-limited response after 32,000 completion tokens |

## G9 arms

| Arm | Solved / completed | Conclusion |
|---|---:|---|
| bare | 0 / 3 | shipping level held |
| structural hint | 0 / 3 | polarity-flipped gate passed |
| placebo | 0 / 0 | OpenRouter rejected every redraw with HTTP 403 total-key-limit; no result was inferred |

The hinted-minus-placebo estimate is therefore undefined, not zero. At medium the hint genuinely helped (2/3 solved), which is why the ladder was moved up once and both bare and hinted were rerun at hard. At hard, the hint did not yield a verified answer in three completed calls. The failed placebo run is preserved verbatim in `g9_placebo_transcript.jsonl`; it is a non-gated diagnostic gap.

## Usage

```python
from gen_2306_00140 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
print(render(inst))
candidate = parse_answer('<answer>{"type":"automorphism","scale":1,"shear":0,"generator_images":{"sigma":[1,0],"tau":[0,1]}}</answer>')
print(verify(inst, candidate))
```

From the repository root, emit deterministic JSONL instances with:

```bash
bash scripts/emit.sh 2306.00140 20
```

## Caveats

This is not a computational-hardness claim: the reference algorithm solves every instance quickly. The 0/200,000 guess result concerns the uniform, statement-aware language of quadratic-residue scales and arbitrary shears; it does not model a solver's algebraic prior. Once the normalized-sum invariant is seen, the remaining obstacle at hard is 152 exact modular products plus one modular recovery, so some failures may measure exact-arithmetic endurance as well as invariant discovery.

The panel did not run GAP, a CAS, Gröbner-basis software, or exhaustive subgroup-isomorphism tooling; such tools are unnecessary because the included reference algorithm already wins. The generator covers the prime case of Theorem 4.8, not general prime powers or the paper's distinct Hermitian-generalized-quadrangle family. `canonical_key` handles input reordering and the full coordinate automorphism family used here, including the PDS stabilizer, but it is not advertised as a general-purpose group-isomorphism canonicalizer. Finally, the placebo diagnostic is incomplete because the provided OpenRouter key exhausted its total limit after the gated runs.
