# arXiv 2505.19141 — S-unit equations on commuting unipotent modules

| Profile | Value |
|---|---|
| Track | **B** — no-tool compression; an efficient algorithm is disclosed below |
| Native domain / object regime | algebra / finite field |
| Computational core | linear algebra |
| Certificate | integer exponent tuple (the paper's native witness) |
| Intended intuition | invariant: all dense coupling is one rank-one scalar pairing |
| Domain essentiality | native; no reduction |

This generator instantiates Dong and Shafrir's [*S-unit equations in modules and linear-exponential Diophantine equations*](https://arxiv.org/abs/2505.19141). The solver receives a free module `V = GF(p)^(n+1)`, commuting invertible actions for Laurent generators `X_j`, a source module element, and a target. It must return the least-residue exponent vector of a Laurent monomial that sends the source to the target. The checker composes the actions by exact modular arithmetic and compares the resulting module vector. No graph, finite-field analogue of a real object, or convenience reduction replaces the paper's mathematics.

## Why this is Track B

Equation (1.2) in Section 1 fixes the native S-unit definition. Section 3.3 treats the Laurent generators as pairwise commuting automorphisms and writes the equation using invertible matrices on a free module; Equation (3.25) is the exact matrix-action form used here. Theorem 1.3 proves that for prime-power torsion the complete solution set is effectively `p`-normal, with the automaton constructed in Section 3.5 and refined in Sections 3.6–3.7. The introduction also identifies the easy/known regimes: one prime has classical decision procedures, two primes are decidable by Corollary 1.5, and three or more primes are tied by Theorem 1.4 to the open general linear-exponential problem.

Those results forbid a Track A claim for this distribution. In this promised subfamily, generator `X_j` acts by `(c,w) -> (c,w+c*a_j)`. Its square-zero shear parts have pairwise-zero products, so the displayed S-unit equation is exactly `A z = b (mod p)`. Exact Gaussian elimination solves it in `O(n^3)`: the recorded eight-seed shipping run averaged 23,376 field operations, 636 Euclidean divisions, and 0.004374 seconds. The compact route notices `A = I + u v^T` and applies the single Sherman–Morrison scalar correction in at most 226 field operations. The benchmark tests whether a no-tool solver discovers that invariant; it does not claim computational intractability.

Generation is inverse, not a disguised solve: `z` is sampled first, independent nonzero `u,v` are sampled until `1+v^T u != 0`, and the target is computed as `b=(I+uv^T)z`. Thus `A` is nonsingular by the matrix-determinant lemma and the bounded witness is unique.

## Worked demo

For `make_instance(n=2, field="toy", seed=3)`, the complete rendered mathematical data are:

```text
Find a Laurent monomial sending one element of a finite-field module to another.

Let F be the field of residues modulo the prime p=11.  The module is
V=F^(3); write its vectors as (c,w_1,...,w_2).  There are 2
commuting Laurent generators X_1,...,X_2.  Column j of the matrix A below is
the vector a_j in F^2, and the action of X_j is

    X_j * (c,w) = (c, w + c*a_j)  (all coordinates modulo p).

This action is invertible: X_j^(-1)*(c,w)=(c,w-c*a_j), so every integer
exponent is defined.  The actions commute.  For an exponent vector
z=(z_1,...,z_2), the Laurent monomial X_1^z_1 ... X_2^z_2 means compose
those actions.  We require the unique least-residue representative with every
0 <= z_j < p.  Rows and columns are 1-indexed, their order is significant, and
no entry may be omitted.

Matrix A (2 rows, 2 entries per row; entries are least residues modulo p):
  1: 6 3
  2: 9 2

Source module element:
  1 0 0

Target module element:
  1 1 1

Find z such that the ordered product over j=1,...,2 of X_j^(z_j), acting
on source, equals target.

The displayed A is nonsingular over F, so the required least-residue exponent
vector is unique.  The answer must be a JSON list of exactly 2 decimal
integers in X_1,...,X_2 order, with every entry in the inclusive range
0,...,p-1.  Repetitions are allowed.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example: <answer>[0,1]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[3,9]</answer>` because both rows of `A*[3,9]` are `1 mod 11`. `verify(inst, [3,9])` returns `(True, "ok")`; `verify(inst, [3])` returns `(False, "expected 2 entries, got 1")`. A person can solve this demo on paper by two modular equations.

## Difficulty presets

| Preset | n | Field modulus p | Search-space bits | Compact-operation cap | Status |
|---|---:|---:|---:|---:|---|
| demo | 2 | 11 | 7 | 16 | hand example; never ships |
| easy | 32 | 2,147,483,647 | 992 | 226 | configured shipping candidate |
| medium | 36 | 2,147,483,647 | 1,116 | 254 | local gates pass |
| hard | 40 | 2,147,483,647 | 1,240 | 282 | local gates pass |

`easy` is currently configured by `SHIPPING_DIFFICULTY`. It is not release-ready hardness evidence: the required oracle run obtained only HTTP 403 quota errors, so the harness produced no scored attempt and no `hardened` verdict.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses and 12/12 module-law checks pass; all five field primality checks pass |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic prose/fence/tag response round-trips |
| G4 | 0 hits / 200,000 structure-aware uniform guesses; candidate language has 992 bits |
| G5 | exact density `1 / 2147483647^32`; demo brute force finds exactly one solution; strongest failing attack ran 256 restarts |
| G6 | five attacks each score 0/8; Gaussian reference and compact solver each score 8/8 |
| G7 | doubled `n=64` instance builds and verifies; space grows from 992 to 1,984 bits |
| G8 | 300/300 invariance checks and 300/300 carried-witness checks pass; 20/20 unrelated keys differ |
| G9(c) | actual answer 334 characters / 84 approximate tokens / 32 atoms; worst-case 353 / 89; intended route 226 operations |

## Oracle loop

No row below is scored as a model failure. `harden.py` correctly records API failures as errors and aborted without a verdict.

| Arm / preset | Seeds | Scored solved/attempts | Outcome |
|---|---|---:|---|
| bare / easy | 860780874, 1979233316, 512378836, 625199521 | 0/0 | four HTTP 403 “Key limit exceeded” errors |
| structural / easy | 1674830937, 1300053966, 1595428563, 1758045363 | 0/0 | four HTTP 403 errors |
| placebo / easy | 627886522, 1719052225, 1278007648, 740985748 | 0/0 | four HTTP 403 errors |

## G9 diagnostic

| Arm | Solved / scored attempts | Transcript |
|---|---:|---|
| bare | 0/0 | `llm_loop_transcript.jsonl` (errors only) |
| hinted | 0/0 | `g9_hinted_transcript.jsonl` (errors only) |
| placebo | 0/0 | `g9_placebo_transcript.jsonl` (errors only) |

`hinted - placebo` is undefined because neither arm received a response. Nothing can yet be inferred about whether the structural hint helps. This does not affect the local G9(c) size/effort gate, but it leaves STEP 4 and the G9 diagnostic incomplete.

## Use

```python
from gen_2505_19141 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["easy"])
prompt = render(inst)
wire_answer = "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
answer = parse_answer(wire_answer)
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after a successful hardening run, emit instances with:

```bash
bash scripts/emit.sh 2505.19141 20
```

The implementation is standard-library-only; this finite-field action needs no `gvlib` helper.

## Caveats

- The family is intentionally easy with tools: exact elimination takes milliseconds. That is the Track B reference algorithm, not a failed Track A claim.
- The 0/200,000 result is relative to the exact uniform prior over all length-32 residue vectors. It establishes witness density, not model difficulty.
- A rank-one detector followed by Sherman–Morrison succeeds by design and is therefore reported as the reference/intended route, not hidden among failing attacks. The panel did not test every alternative structured-matrix recognizer.
- The rendered easy instance is about 12,855 characters because it displays the native action columns exactly. Prompt scanning may contribute some difficulty even though the answer is short.
- `canonical_key` performs exact elimination, normalizes every residue up to sign, and sorts them. This is invariant under arbitrary invertible changes of the displayed tail-module basis, Laurent-generator permutations, and replacing any generator by its inverse; it intentionally does not identify unrelated coefficient-field presentations.
- Escalation first increases `n` only to the 300-operation boundary, then increases the Mersenne-prime modulus at fixed answer length. After `m127`, the next certified Mersenne-prime field would exceed the answer-character cap, so `escalate()` returns `"cap_bound"` rather than falsely condemning the paper.
- Most importantly, the configured OpenRouter key is quota-blocked. Restore its allowance and rerun the bare, structural, and placebo harnesses before trusting any no-tool hardness claim or emitting this family.
