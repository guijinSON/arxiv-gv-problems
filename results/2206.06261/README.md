# Certified private-key recovery from a nodal-curve public key

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | `number_theory` |
| Object regime | `finite_discrete` |
| Computational core | `other` (balanced-semiprime factorization) |
| Certificate form | `integer_tuple` (the JSON object `{p,q,d}`) |
| Intended intuition | `decomposition`: the CRT decomposition exposes the two prime-field component orders |
| Domain essentiality | `licensed_reduction` |
| Reduction | `paper_licensed`, Theorem 4.1 |

## What the family asks

The source is Caglar, Nari, and Ozdemir, [*An Application of Nodal Curves*](https://arxiv.org/abs/2206.06261). The solver receives a balanced semiprime `N`, public exponent `e`, and the nodal curve

```text
C: y^2 = x(x^2-a)^2 over Z/NZ.
```

It must return the two ordered factors `p<q` and the canonical private exponent `d = e^(-1) mod (p^2-1)(q^2-1)`. Verification uses only exact multiplication, modular exponentiation, and one congruence. The generator first constructs and Pocklington-certifies `p` and `q`, then multiplies them; it never factors a completed instance.

This is deliberately a **paper-licensed cryptanalytic reduction**, not native curve-arithmetic search. Section 3, Algorithm 4 defines the factor-based key construction, and Theorem 4.1 makes knowledge of the factors sufficient to recover the private operation. Accordingly, the profile claims number-theoretic factorization coverage rather than algebraic-geometry coverage.

## Why Track A is justified

The paper's Section 4.1 bases the public-key proposal on integer factorization and explains that the factors determine the two component orders and hence `d`. The shipping distribution uses two independently constructed 512-bit primes, both `3 mod 4`, separated by more than `2^509`; `e=65537` does not divide either component order. Each prime's predecessor contains a recursively certified large prime factor. These choices remove the close-factor signature used by Fermat's method and the small-smooth-order signature used by Pollard `p-1`.

No polynomial-time classical factoring algorithm is known for this balanced-semiprime distribution. At the shipping preset, capped Pollard rho used 600,000 modular iterations over eight instances in 1.746050 seconds and recovered 0 factors. Four cheaper construction-aware attacks also recovered 0/8 each. The easy regimes are explicit: the demo modulus is hand-factorable; known factors make recovery immediate by Theorem 4.1; and Section 4.2 notes that degree-two or degree-three *group arithmetic* can use integer arithmetic alone. That last simplification does not reveal a balanced factor, so the hardness claim does not rely on expensive polynomial arithmetic.

## Worked demo

With `make_instance(n=5, seed=17, public_exponent=7)`, the complete mathematical data are:

```text
N = 713, e = 7
f(x) = x^2 - 260 over Z/713Z
C: y^2 = x f(x)^2
p and q are distinct 5-bit primes, p<q, both 3 mod 4.
K = (p^2-1)(q^2-1).
Return compact JSON {"p":p,"q":q,"d":d}, where 1<=d<K and 7d=1 mod K.
```

Factoring `713` by hand gives `23*31`. Thus `K=528*960=506880` and the answer is:

```text
<answer>{"p":23,"q":31,"d":144823}</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Changing `d` to `144824` returns `(False, "private exponent is not the inverse of e modulo K")`. This smallest preset is genuinely hand-solvable.

## Difficulty presets

| Preset | Factor bits `n` | Approx. modulus bits | Candidate-space bits | Ships? |
|---|---:|---:|---:|---|
| demo | 5 | 10 | 2 | no; illustration |
| easy | 512 | 1024 | 1017 | **yes** |
| medium | 640 | 1280 | 1273 | no; unnecessary escalation |
| hard | 768 | 1536 | 1529 | no; unnecessary escalation |

The bare oracle pool failed all three attempts at `easy`, so no preset was rejected or escalated.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted answers verified across all presets |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | Model-style tagged JSON round-tripped; garbage returned `None` |
| G4 | 0/200,000 structured guesses; declared space has 1017 bits |
| G5 | Shipping density sample 0/200,000; demo exact count 1/3; Pollard-rho baseline 600,000 iterations / 1.746050 s |
| G6 | Five attacks, 0/8 successes each |
| G7 | `n=1024` doubled instance built in 0.412025 s and verified |
| G8 | 60/60 fourth-power scaling invariances, 60/60 carried witnesses, 20/20 unrelated keys distinct |
| G9 | 948 chars, about 237 tokens, 3 atoms; 20 exact post-trapdoor operations |

The G6 attacks were coefficient/outlier gcds, 20,000-step Fermat search, 256 structured random restarts, Pollard `p-1` with `B=1000`, and capped Pollard rho. Full details and timings are in `selftest_report.json`.

## Bare oracle loop

| Preset | Seed | Model | Solved? | Recorded reason |
|---|---:|---|---|---|
| easy | 2128380508 | Gemini 3.8 Flash | no | returned an error-shaped JSON object, not `{p,q,d}` |
| easy | 173000154 | GPT-5.6 Terra | no | explicitly declined to factor; no answer parsed |
| easy | 443557953 | Gemini 3.8 Flash | no | fabricated factors with the wrong bit length |

The script-owned verdict is `hardened`, with zero escalations and `easy` as the shipping preset.

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. The decomposition hint bought no observed improvement. This is useful negative evidence about the declared intuition: the prompt already exposes the component-order formula, and the remaining difficulty is finding the hidden factors, not noticing CRT. The serialized answer measured 948 characters (237 approximate tokens, 3 atoms); after the factor trapdoor is known, assembling `K` and running Euclid takes at most 20 counted exact operations.

## Use

From the repository root:

```python
import importlib.util

path = "results/2206.06261/gen_2206_06261.py"
spec = importlib.util.spec_from_file_location("nodal_gen", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
answer = g.parse_answer(f"<answer>{g._format_answer(inst['answer'])}</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Emit dataset records with:

```bash
bash scripts/emit.sh 2206.06261 20 easy
```

## Caveats

- The paper does not prove that its root-extraction problem is equivalent to factoring; it states a security belief and proves only that factors are sufficient. This benchmark avoids claiming the converse by asking directly for the factor trapdoor and labels the reduction.
- The curve coefficient is mathematically tied to the key but is not needed once the task is recognized as factorization. This is not native curve-arithmetic coverage.
- The reported random prior samples all bit-length and congruence-correct integer factor guesses and computes `d` for free. It does **not** condition guesses on primality. A prime-conditioned prior would increase the hit probability by a polylogarithmic factor, but it remains astronomically below `1e-6`; the measured 0/200,000 alone is only an upper-resolution observation, not a security proof.
- General Number Field Sieve and ECM were not available under the standard-library-only dependency rule and were not run. Pollard rho is a bounded diagnostic, not a substitute for a measured GNFS security estimate. The 1024-bit modulus is a benchmark size, not a recommendation for deployed cryptography.
- The generator's Pocklington-certified primes are not a proof of uniform sampling from all 512-bit primes. Their public predecessors have hidden large prime divisors, which resists the tested `p-1` bound but may define a distinguishable research distribution.
- `canonical_key` proves invariance for the generated fourth-power coordinate scalings and distinguishes the sampled moduli; it is not a complete isomorphism classifier for arbitrary nodal curves.
- The G9 operation count begins **after** the factor trapdoor is known. The hard search itself is intentionally excluded, as required for the certificate-construction route; consequently this family primarily measures computational search resistance, not a short human insight.
- Escalation reaches `n=1088`, whose measured answer is 1,986 characters, before returning `cap_bound`; the next 64-bit rung would exceed the 2,000-character answer cap.
