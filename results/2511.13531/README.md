# arXiv 2511.13531 — cyclic Pauli anticommutation dependencies

> **Current status:** implementation and local gates G1–G8 are complete, but this
> result is **not shippable yet**. The OpenRouter key reached its permanent $500
> limit during the bare oracle run, before the current ladder or either G9 arm
> could be evaluated. G9 is therefore recorded as failed/not-run rather than
> being fabricated from the API error.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | matrix certificate (a nonzero GF(2) kernel vector) |
| Intuition | decomposition: recognize a reciprocal polynomial mask repeated under cyclic translation |
| Domain essentiality | native |
| Reduction | none |

## The problem

The source is [Xu et al., *Simultaneous variances of Pauli strings, weighted
independence numbers, and a new kind of perfection of graphs*](https://arxiv.org/abs/2511.13531).
Section II defines the frustration pattern of Pauli strings by their pairwise
anticommutation. Section IX.2, Theorem 8, proved in Appendix A.3, shows that the
shortest Pauli realization has length `rank_GF(2)(A)/2`, where `A` is this exact
anticommutation matrix.

An instance gives a symmetric zero-diagonal circulant matrix over GF(2), using
its connection offsets rather than printing all `n²` entries. The solver must
return any nonzero `v` with `Av=0`. The checker performs the cyclic XOR product
exactly; it neither reads the planted answer nor solves a search problem.

Generation is compositional. It first chooses a reciprocal divisor `q` of
`x^n+1`, forms the witness `h=(x^n+1)/q`, and only afterward constructs the
public connection polynomial as an XOR of translated copies of `q`. Therefore
`A h=0` is known before the instance exists. Fourteen seed-dependent reciprocal
factors occur at the hard preset, rather than one answer shared by every seed.

## Why Track B

This is not a Track A claim. Theorem 8 itself exposes the mechanical algorithm:
GF(2) elimination gives the rank and a kernel, and the public cyclic structure
improves this to the Euclidean polynomial-gcd algorithm in `O(n²)` coefficient
operations. On eight hard instances that reference algorithm solved 8/8 in
0.001775 seconds total (0.000222 seconds mean), using 381,636 coefficient XORs
and 3,731 machine-word XOR steps.

The intended no-tool route notices that the offset mask decomposes into
translated copies of one 17-coefficient reciprocal factor, reads that factor,
and uses its quotient identity to write an annihilator. At the measured hard
instance this takes at most 265 exact operations. Small matrices, even row
weight (which makes the all-ones vector a kernel vector), and a single fixed
reciprocal factor are easy regimes deliberately avoided. A superseded `n=62`
easy rung was solved by 2/3 oracle vendors and was removed.

## Worked demo

For `make_instance(n=14, degree=3, blocks=0, seed=0)`, the complete mathematical
instance is:

```text
n = 14
D = [4, 5, 6, 7, 8, 9, 10]
A[i,j] = 1 iff (j-i) mod 14 is in D
Find nonzero v in GF(2)^14 with Av=0.
```

The planted answer is:

```json
{"encoding":"hex-lsb0","n":14,"vector":"0x0183"}
```

Here bits 0, 1, 7, and 8 are set. `verify(inst, answer)` returns `(True, "ok")`.
Changing the last bit to obtain `0x0182` returns `(False, "vector is not in the
GF(2) kernel of the stated matrix")`. This demo is hand-solvable by writing the
14 cyclic parity equations; the larger presets are not intended for manual
elimination.

## Difficulty presets

| Preset | n | reciprocal degree | translated block pairs | Status |
|---|---:|---:|---:|---|
| demo | 14 | 6 | 0 | hand example; never shipped |
| easy | 126 | 12 | 2 | locally verified; oracle not run |
| medium | 254 | 14 | 3 | locally verified; oracle not run |
| hard | 510 | 16 | 4 | intended shipping preset; oracle blocked |

`SHIPPING_DIFFICULTY` is provisionally `hard`. It must not be treated as shipped
until a fresh bare hardening run holds and G9(b) also holds.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16 preset/seed checks; 16 JSON-native checks |
| G2 | pass | 6 corruptions rejected with 6 distinct reasons |
| G3 | pass | tagged JSON recovered from prose and a Markdown fence |
| G4 | pass | 0 / 200,000 structure-valid random vectors |
| G5 | pass | hard nullity 20; 1,048,575 valid of `2^510-1` (`3.13e-148`); greedy baseline 9,180 evaluations |
| G6 | pass | five attacks, each 0/8; reference gcd 8/8 as expected |
| G7 | pass | doubled `n=1020` builds and verifies; search exponent +510 |
| G8 | pass | 80 invariance checks, 60 carried-witness checks, 20/20 unrelated keys distinct |
| G9 | **not run / fail** | answer 173 chars, 44 estimated tokens, 3 atoms; intended route 265 ops; oracle evidence missing |

## Oracle evidence

The only completed calls belong to the now-removed `n=62` pilot rung. They are
retained in `oracle_budget_exhausted_transcript.jsonl`; they do not establish
hardness for the current module.

| Superseded preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| old easy (`n=62`) | 1199940302 | OpenAI GPT-5.6 Terra | solved | verified kernel |
| old easy (`n=62`) | 1512647710 | Claude Sonnet 5 | failed | response exhausted its length budget |
| old easy (`n=62`) | 1460133520 | Grok 4.6 | solved | verified kernel |
| old medium | — | multiple redraws | error | OpenRouter key total limit exhausted |

The authoritative `llm_loop_transcript.jsonl` is an aborted harness output and
has no verdict. Once the key is replenished, rerun it from this directory; the
harness will overwrite that incomplete file with a fresh run.

## G9 arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0 / 0 | not run on current ladder |
| structural hint | 0 / 0 | not run; G9(b) cannot pass |
| placebo hint | 0 / 0 | not run |

The hinted-minus-placebo value is therefore undefined in substance (stored as
`0.0` only because both denominators are zero). No conclusion about the claimed
decomposition intuition is justified yet.

## Use

```python
from gen_2511_13531 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
prompt = render(inst)
answer = parse_answer('<answer>{"encoding":"hex-lsb0","n":510,"vector":"..."}</answer>')
ok, reason = verify(inst, answer)
```

After a successful hardening run, emit from the repository root with:

```bash
bash scripts/emit.sh 2511.13531
```

## Caveats

- Random-guess density is for the declared prior: every nonzero 510-bit vector
  uniformly. It says nothing about a solver exploiting cyclic algebra; the
  reference gcd does exactly that and is expected to win.
- The cheap affine canonical key covers cyclic translations, multiplication by
  units, reflection, and input-order changes. Composite-order circulant matrices
  can have non-affine isomorphisms; full isomorphism canonicalization was not
  attempted, so the key is the strongest inexpensive invariant used here.
- The attack panel tried equal-degree/all-ones, syndrome descent, 256 uniform
  restarts, short periods through 16, and 4,096 half-repeat samples. It did not
  test every coding-theory decoder or a learned cross-instance motif attack.
- The construction exposes only fourteen reciprocal-factor answers at the hard
  degree, although translated masks give many distinct instances. This is enough
  for the current diversity test but could create cross-example leakage in a
  very large emitted corpus.
- Most importantly, no current-ladder oracle or G9 result exists. A replenished
  OpenRouter key and three isolated harness runs are required before submission.
