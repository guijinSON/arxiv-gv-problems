# Verified generator for arXiv:1508.07590

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity / inversion |
| Certificate | polynomial: one exact element of `GF(2^(2k+1))` represented in the binary polynomial basis |
| Intended intuition | symmetry — the nonlinear exponents straddle a Frobenius power |
| Domain essentiality | native; no reduction |

## Problem and trust status

[Li, Qu, and Chen, *New Classes of Permutation Binomials and Permutation Trinomials over Finite Fields*](https://arxiv.org/abs/1508.07590) prove in Theorem 4.10 that, for `q=2^(2k+1)`, a displayed three-term polynomial `F_a` permutes `GF(q)`. The generator hands the solver the binary extension field, its irreducible modulus, all three exact coefficient/exponent pairs, and a nonzero target `Y`. The solver must return the unique field element `X` satisfying `F_a(X)=Y`.

Generation is inverse: it samples nonzero `a` and `X` first and computes `Y=F_a(X)`. The answer is never found by solving the emitted instance. Verification ignores `inst["answer"]`, parses the submitted hexadecimal string as a polynomial over `GF(2)`, evaluates the three terms by exact modular polynomial arithmetic, and compares the result with `Y`. Any valid witness is accepted.

## Why Track B

This paper supplies a construction, not a search-hardness theorem, so Track A would be false. Section 2 fixes the permutation-polynomial definition and equivalences. Section 4.B gives the new trinomial classes; Theorem 4.10 is the family used here. Most importantly, Equation (21) in its proof turns `F_a(X)=Y` into

```text
(a^(2^(k+1)+2) + a Y^(2^(k+1)) + Y^2) X
    = a Y^(2^(k+1)+1).
```

Thus a solver who recognizes the Frobenius cancellation needs 68 counted exact field operations at shipping size. The honest reference algorithm builds primitive-element log/antilog tables and evaluates `F_a` on every nonzero field element. It is `O(2^(2k+1))` time and memory, solves 8/8 as expected, and in the final run cost up to 18,557,039 counted table/XOR/index operations and 1.08 seconds for one shipping instance. That is easy for software and unrealistic to execute unaided; the intended test is finding the 68-operation identity.

The paper's own easy route is precisely Equation (21), not an omitted hardness regime. The generator therefore does not claim that inversion is computationally hard, and it excludes `a=0` only so the nonzero formula and certificate language stay uniform.

## Worked demo

For `make_instance(n=2, seed=7)`, `n` is the paper's `k`. The full rendered task is:

```text
PREIMAGE OF A SPARSE PERMUTATION TRINOMIAL

Work in the binary field K = GF(2^5) represented as GF(2)[t]/(M(t)),
where M(t) = t^5 + t^2 + 1.
The hexadecimal modulus bit mask is 0x25; bit i is
the coefficient of t^i.  A field element is encoded the same way using
exactly 2 lowercase hexadecimal digits (leading zeros included).
Addition is bitwise XOR.  Multiplication is ordinary binary-polynomial
multiplication followed by reduction using M(t)=0.  Powers are field powers.
All arithmetic is exact; hexadecimal strings are not ordinary integers
for multiplication.

Define F(X) by these three terms (their displayed order is irrelevant):
  coefficient 0x05 times X^9
  coefficient 0x0b times X^7
  coefficient 0x01 times X^1

The target is Y = 0x09.
This displayed F is guaranteed to permute K, and F(0)=0 while Y is
nonzero.  Find the unique nonzero field element X with F(X)=Y.

Encode X as the unique binary polynomial of degree strictly below
5: if X=sum_i c_i t^i, bit i of polynomial_hex is c_i.
The value must be in 000...001 through 1f
and polynomial_hex must contain exactly 2 lowercase hex digits.

Give your final answer inside <answer></answer> tags, as a JSON object
with exactly the key polynomial_hex.
Example: <answer>{"polynomial_hex":"01"}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"polynomial_hex":"1f"}</answer>`. `verify(inst, inst["answer"])` returns `(True, "ok")`; dropping one hex digit returns `(False, "hex encoding must contain exactly 2 digits")`. A person can solve this 32-element demo by enumerating the 31 nonzero elements on paper, though Equation (21) is shorter.

## Difficulty presets

| Preset | `k=n` | Field | Witness space | Status |
|---|---:|---:|---:|---|
| demo | 2 | `GF(2^5)` | 31 | hand-scale illustration; skipped by hardening |
| easy | 10 | `GF(2^21)` | 2,097,151 | **shipping; bare oracle held 0/3** |
| medium | 14 | `GF(2^29)` | 536,870,911 | reserve escalation rung; G1 passed |
| hard | 19 | `GF(2^39)` | 549,755,813,887 | reserve escalation rung; G1 passed |

An earlier provisional easy rung at `k=5` also resisted 3/3 oracle calls, but it was removed because its exact random-witness probability `1/2047` fails G4. Difficulty now grows by enlarging the field while the answer remains one atomic polynomial encoding. `escalate()` continues increasing `k` and returns `cap_bound` only when that single hexadecimal encoding would exceed 2,000 characters.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 planted verifies | pass | 12/12 preset-seed instances; all answers JSON-native |
| G2 corruption | pass | drop, swap, duplicate, empty, and out-of-range rejected with 5 distinct reasons |
| G3 round trip | pass | realistic prose/fence/tag response parsed and verified |
| G4 guess resistance | pass | 0/200,000; exact probability `1/2,097,151 = 4.768e-7` |
| G5 density and baseline | pass | shipping density 0/200,000; demo exact count 1 of 31; baseline 18,557,039 operations / 1.08 s |
| G6 adversaries | pass | four no-tool attacks at 0/8 each; reference enumerator 8/8 |
| G7 scaling | pass | doubled `k=20` / degree 41 builds and verifies; answer stays one atom |
| G8 canonical key | pass | 80 invariance and 80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) caps | pass | 28 characters, 7 estimated tokens, 1 atom, 68 intended operations |

## Bare oracle loop

The repository's current hardening script used its configured two-provider pool at medium reasoning effort.

| Preset | Seed | Model | Solved | Result |
|---|---:|---|---|---|
| easy | 1,232,533,276 | Gemini 3.8 Flash | no | parseable polynomial failed exact evaluation |
| easy | 884,843,477 | OpenAI GPT-5.6 Terra | no | parseable polynomial failed exact evaluation |
| easy | 989,244,871 | Gemini 3.8 Flash | no | exhausted the 32k-token budget without an answer |

The script-owned verdict is `hardened`, with shipping parameters `{"n":10}` and no escalation. The last outcome is explicitly length-limited; the other two are substantive wrong answers.

## G9 diagnostic

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. The hint did not measurably help this pool. Therefore the Frobenius symmetry is justified by the paper and by the compact exact solver, but this three-arm diagnostic provides no causal evidence that the hint exposes the models' missing insight. The only two `parsed=False` replies, one bare and one hinted, were explicit empty length-limited responses; no nonempty final answer was lost to the parser. The shipping answer is 28 characters (about 7 tokens), one atomic element, and the intended route uses 68 exact field operations.

## Use

```python
import gen_1508_07590 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=42)
statement = g.render(inst)
answer = g.parse_answer('<answer>{"polynomial_hex":"000001"}</answer>')
ok, reason = g.verify(inst, answer)  # the illustrative value need not be correct
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1508.07590
```

## Caveats

This is deliberately an easy algorithmic class and makes only a Track-B claim. A solver that recalls or re-derives Equation (21) makes the instance easy. The 0/200,000 estimate uses the strongest freely deducible prior—uniform over nonzero field elements—and the exact probability follows from the theorem's bijectivity; it says nothing about a solver using algebraic structure.

The reference baseline is exhaustive value-table inversion, not the fastest conceivable finite-field root algorithm. Berlekamp/Cantor–Zassenhaus factorization, a CAS implementation, and specialized symbolic elimination were not benchmarked. The attack panel covers displayed-value outliers, greedy bit fixing, 256 random restarts, and a low-complexity monomial/Frobenius ansatz; it does not establish hardness against tool-using algebra systems. The measured 1.08 seconds is machine-dependent, while the exact 18,557,039 operation count is reproducible.

The canonical key handles term reordering, all Frobenius field automorphisms, nonzero linear input/output scalings, and their compositions. It does not canonicalize a change to a different irreducible-polynomial presentation of the same abstract field. Finally, two of the nine oracle calls across all arms were length-limited; the other seven emitted exact-format but incorrect witnesses. The equal hinted/placebo rates mean the current `intuition_type` should be treated as mathematically motivated rather than empirically isolated by G9.
