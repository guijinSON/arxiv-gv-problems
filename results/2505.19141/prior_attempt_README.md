# arXiv 2505.19141 — bounded S-unit equations in a finite module

| Profile | Value |
|---|---|
| Track | **B** — no-tool compression; an efficient algorithm is disclosed below |
| Native domain / regime | algebra / finite field |
| Computational core | linear algebra |
| Certificate | integer exponent tuple (the paper's native witness) |
| Intended intuition | invariant: a wrapped-geometric circulant is inverted by one cyclic first difference |
| Domain essentiality | native; no reduction |

This generator instantiates Dong and Shafrir's [*S-unit equations in modules and linear-exponential Diophantine equations*](https://arxiv.org/abs/2505.19141). The solver receives the finite module `M = F_p^k direct-sum F_p^k`, the action `X(a,b) = (a+Ub,b)`, standard module vectors `s_i=(0,e_i)`, and a target. It must return the exponent residues in `sum_i X^(z_i)s_i = b`. The checker substitutes them and compares all coordinates exactly modulo `p`.

## Why this is Track B

Equation (1.2) in Section 1 fixes the native S-unit definition. Section 2 defines finitely presented Laurent modules and notes that finitely generated modules of this kind admit finite presentations; Section 3.3 explicitly treats the Laurent actions as commuting automorphisms and, after Proposition 3.16, as invertible matrices on a free module. Thus the matrix-action instance is native, not a reduction. Theorem 1.3 proves effective `p`-normality for prime-power torsion, Section 3.5 builds the finite automaton, and Sections 3.6–3.7 refine it into the `p`-normal description. Corollary 1.5 gives decidability with at most two torsion primes, while Theorem 1.4 ties three or more primes to the open general linear-exponential problem.

The paper's effective construction does not come with a polynomial complexity bound, so its mere existence would not disqualify Track A. This particular promised subfamily does: the identity `X^z=I+z(X-I)` turns recovery directly into `Uz=t`, and generic exact Gauss-Jordan elimination solves it in `O(k^3)`. Across eight hard instances it used a mean 30,219 field operations (maximum 97,822) and 0.001047 seconds mean in the recorded final self-test. The shorter route notices that the first column of `U` is a geometric sequence with one cyclic wrap and a ratio promised to lie in `{2,...,9}`. Three adjacent entries identify that small ratio without modular division. If the wrap is at `d`, then `z[r-d] = t[r+1] - a*t[r] (mod p)`. Detecting the ratio and applying that difference costs 280 field operations at shipping size. The benchmark asks a no-tool solver to find and execute that compression; it does not claim computational intractability.

## Worked demo

For `make_instance(n=3, modulus=11, seed=7)`, the rendered mathematical data are:

```text
M = F_11^3 direct-sum F_11^3
X(a | b) = (a + U b | b)
U =
  10  6  4
   4 10  6
   6  4 10
t = 10 3 10
s_i = (0 | e_i)
Find 0 <= z_i < 11 with sum_i X^(z_i)s_i = (t | 1).
```

The answer is `<answer>6, 10, 0</answer>`. `verify(inst, [6, 10, 0])` returns `(True, "ok")`; dropping the last entry returns `(False, "expected exactly 3 exponents, got 2")`. This demo is hand-solvable either by three modular equations or by spotting the cyclic ratio.

## Difficulty presets

| Preset | k | p | Matrix entries | Compact operations | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 11 | 9 | 36 | hand example; never ships |
| easy | 12 | 101 | 144 | 72 | local gates pass |
| medium | 32 | 10,007 | 1,024 | 152 | local gates pass |
| hard | 64 | 1,000,003 | 4,096 | 280 | configured shipping preset |

`hard` is configured to ship. The required oracle run could not certify it because the provided OpenRouter key returned HTTP 403 “Key limit exceeded (total limit)” on every call. Consequently this directory is locally verified but **not release-ready hardness evidence** until `harden.py` completes successfully.

## Gate results

| Gate | Result |
|---|---|
| G1 | 16/16 planted witnesses verify; 16/16 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic prose/fence/tag response round-trips; garbage returns `None` |
| G4 | 0 hits / 200,000 uniform shape-valid guesses; exact density (1/1000003^{64}) |
| G5 | shipping solution count is exactly 1 by invertibility; demo brute force finds 1/1,331; one shipping reference run used 26,736 field operations |
| G6 | five attacks, each 0/8; Gauss-Jordan succeeds 8/8 as Track B requires |
| G7 | doubled (k=128) instance builds and verifies; search-space bit length grows 1,276 to 2,552 |
| G8 | 120/120 key-invariance and 120/120 carried-witness checks, including global affine exponent relabellings; 20/20 unrelated keys distinct |
| G9(c) | 513-character exact worst-case bound (sampled maximum 447), about 129 tokens, 64 atoms, 280 intended operations — all within caps |

## Oracle loop

No call below is scored as a model failure; `harden.py` records API errors as errors and aborted without a verdict.

| Arm / preset | Seeds | Scored solved/attempts | Outcome |
|---|---|---:|---|
| bare / easy | 496426063, 59727428, 1903727092, 2048043185 | 0/0 | four HTTP 403 errors; pool unreachable |
| structural / hard | 1620087770, 266090387, 664653560, 755891851 | 0/0 | four HTTP 403 errors; pool unreachable |
| placebo / hard | 1910187282, 1246362567, 467786684, 1381799049 | 0/0 | four HTTP 403 errors; pool unreachable |

## G9 diagnostic

| Arm | Solved / scored attempts | Transcript |
|---|---:|---|
| bare | 0/0 | `llm_loop_transcript.jsonl` (API errors only) |
| hinted | 0/0 | `g9_hinted_transcript.jsonl` (API errors only) |
| placebo | 0/0 | `g9_placebo_transcript.jsonl` (API errors only) |

`hinted - placebo` is undefined: neither arm obtained an oracle response. Nothing can yet be concluded about whether the stated invariant helps models. This diagnostic is not used to pass G9; only the measured size and effort caps gate it.

## Use

```python
from gen_2505_19141 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
prompt = render(inst)
answer = parse_answer("<answer>" + ",".join(map(str, inst["answer"])) + "</answer>")
assert verify(inst, answer) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2505.19141 20
```

## Caveats

- The family is intentionally easy with tools: exact elimination takes milliseconds, and the successful compact solver is included in the self-test. This is not Track A evidence.
- The 0/200,000 guess result is relative to a uniform prior over all canonical residue tuples. It establishes density, not human or model difficulty.
- The hard renderer is about 30,551 characters because it displays the full native action matrix. Although the answer and intended arithmetic fit G9(c), prompt scanning itself may contribute difficulty.
- The panel did not test every structured-matrix recognizer. In particular, a circulant/geometric recognizer succeeds by design; that is the intended route, not a failing attack.
- After the modulus reaches 2,147,483,647, `escalate()` can raise `k` only to 69 (exactly 300 compact-route operations) and then returns `cap_bound`; larger instances remain mathematically valid but exceed the no-tool effort cap.
- `canonical_key` computes the exact reduced `[I|z]` form, forgets summand order, and canonically normalizes the global affine exponent action `z -> u*z+c`. It is invariant under arbitrary invertible changes of top-module basis, summand permutations, and those cyclic-group relabellings; transformations outside these stated equivalences are not collapsed.
- Most importantly, the four-vendor hardening and all three G9 response arms remain unmeasured because of the external OpenRouter quota. Re-run them before trusting the no-tool hardness claim.
