# Four prime squares with 46 fixed powers of two

> **Status: externally blocked, not yet shippable.** All local gates pass for the
> medium preset, but the bare hardening run exhausted the OpenRouter key after two
> valid medium attempts. The required third attempt and both G9 diagnostic arms
> therefore remain unmeasured. No API error is counted as a solver failure.

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | `number_theory` / `finite_discrete` |
| Core / certificate | `subset_sum` / four-integer `integer_tuple` |
| Objects | an even integer, four prime bases in an interval, 46 powers of two |
| Intuition | change of variables: center a hidden four-term arithmetic progression |
| Essentiality / reduction | `native` / none |

## Problem and construction

[Lilu Zhao, *Four squares of primes and powers of 2*](https://arxiv.org/abs/1308.5492)
studies equation (1.1),

`N = p0^2 + p1^2 + p2^2 + p3^2 + 2^nu1 + ... + 2^nuk`,

and Theorem 1.1 proves existence for `k=46` and every sufficiently large even
integer. The generator displays all 46 exponents, `N`, their exact subtotal, and
an inclusive prime interval. The solver returns four distinct increasing primes.
The checker uses deterministic exact primality testing and integer substitution;
it never reads the planted answer and accepts any valid quadruple.

Generation is inverse. It samples a four-prime progression
`p, p+d, p+2d, p+3d`, with `d` a positive multiple of 210, independently samples
the exponents and interval placement, and forms `N`. It therefore knows a witness
before the instance exists. Section 2's count instead uses ordered primes in a
very narrow box and `4 <= nu <= L`; Section 5 uses 44 such powers plus two low
powers to fix the residue modulo 8. This finite specialization is guaranteed by
inverse generation, not by the paper's ineffective “sufficiently large” theorem.

## Why Track B

Theorem 1.1 is existential: Section 5 proves positivity by comparing circle-method
major and minor arcs and gives neither a witness-recovery algorithm nor an explicit
threshold. It cannot support a Track-A claim for this distribution.

An admitted reference algorithm sieves the interval, hashes sums of two prime
squares, and looks up complementary pair sums. For interval width `W`, endpoint
`U`, and `m` interval primes, it costs `O(W log log U + m^2)` time and `O(m^2)`
memory. Across eight medium instances it solved 8/8, averaging 381,803 pair visits,
1,546,347 counted operations, and 0.154 seconds (maximum 2,173,481 operations and
0.256 seconds). This successful algorithm belongs under `reference_algorithm`, not
the failing attacks.

The intended compression is

`p^2 + (p+d)^2 + (p+2d)^2 + (p+3d)^2 = (2p+3d)^2 + 5d^2`.

At medium width there are at most 28 possible positive 210-multiple gaps. Updating
`5d^2` by first differences, checking the remaining square, and recovering `p`
uses at most 164 counted exact operations. The benchmark tests whether a no-tool
solver discovers that planted change of variables instead of attempting roughly
1.55 million mechanical operations.

## Worked demo (`seed=0`)

```text
Four prime squares and 46 powers of two

Find exactly four pairwise distinct primes p0 < p1 < p2 < p3 in [7, 657]
whose squares, together with the 46 displayed powers, sum to N.
E = [4, 8, 5, 4, 6, 4, 6, 6, 6, 8, 4, 5, 8, 4, 6, 6, 4, 7,
     4, 8, 4, 6, 6, 8, 8, 4, 4, 8, 4, 7, 5, 4, 4, 7, 5, 5,
     7, 5, 8, 6, 6, 5, 8, 6, 7, 4]
sum(2^e for e in E) = 4096
N = 654932
required prime-square subtotal = 650836

Give four comma-separated integers inside <answer></answer>.
```

`<answer>13, 223, 433, 643</answer>` verifies as `(True, "ok")`.
Dropping `643` gives `(False, "expected exactly 4 primes, got 3")`. A person can
solve this demo by hand: its only possible 210-step progression has
`650836 - 5*210^2 = 656^2`, hence `p=(656-3*210)/2=13`.

## Presets and gates

| Preset | Width | Prime floor | Gap slots | Power max | Result |
|---|---:|---:|---:|---:|---|
| demo | 650 | 10 | 1 | 8 | hand-solvable; hardener skips it |
| easy | 9,000 | 1,000,000 | 9–14 | 22 | oracle solved 1/3; rejected rung |
| medium | 18,000 | 5,000,000 | 13–24 | 32 | provisional shipping; oracle 0/2 before quota |
| hard | 32,000 | 10,000,000 | 25–48 | 40 | locally supported; not reached |

| Gate | Result | Shipping-level evidence |
|---|---|---|
| G1 | pass | planted answers and JSON round-trips: 16/16 |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged answer parsed from prose and a Markdown fence |
| G4 | pass | 0/250,000 structured guesses; language size 191,406,983 |
| G5 | pass | exactly 2/191,406,983 valid; reference cost above |
| G6 | pass | five attacks each 0/8; reference solver 8/8 as expected |
| G7 | pass | doubling width grows the space to 1,690,376,804; answer stays four atoms |
| G8 | pass | 20/20 reorderings, compositions, real transforms, and unrelated keys |
| G9(c) | pass | 33 chars, 9 estimated tokens, 4 atoms, 164 operations |

The five failed attacks are interval quartiles, equal-residual greedy, 80
consecutive-prime windows, 512 random restarts, and the first eight hand-scale
210-multiple gaps.

## Oracle and G9 evidence

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 1172132248 | GPT-5.6 Terra | failed | parsed tuple; first entry composite |
| easy | 1183434529 | Gemini 3.8 Flash | **solved** | exact witness verified |
| easy | 1229926589 | GPT-5.6 Terra | failed | parsed tuple; first entry composite |
| medium | 938307198 | Gemini 3.8 Flash | failed | parsed tuple; first entry composite |
| medium | 1023805787 | GPT-5.6 Terra | failed | parsed tuple; first entry composite |
| medium | four further seeds | both vendors | error | HTTP 403 total key limit; not attempts |

The bare medium arm is therefore 0/2 valid attempts, not the required 0/3. The
fresh isolated hinted and placebo runs each contain four HTTP-403 redraws and zero
valid attempts. `hinted - placebo` is consequently undefined; the report stores
`0.0` only as a zero-denominator serialization convention. No conclusion about
the hint's effect is justified. The hint names only the progression-gap invariant.

The root `.meta.json` still contains the last completed run's obsolete easy-preset
verdict because `harden.py` preserves the previous verdict when a later run aborts.
It is script-owned and was not edited by hand; the current transcript above is the
authoritative record of the incomplete rerun.

## Use

```python
from gen_1308_5492 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["medium"])
print(render(inst))
candidate = parse_answer("<answer>...</answer>")
print(verify(inst, candidate))
```

Once a funded key completes the third bare medium attempt and the two diagnostic
arms, regenerate the report and emit from the repository root:

```bash
bash scripts/emit.sh 1308.5492 20 medium
```

## Caveats

- This supplies the 46 exponents and adds distinctness and interval bounds; it is
  a native-object specialization, not the paper's full existential search problem.
- The arithmetic progression and factor 210 are generator features, not conclusions
  of Zhao's paper. Bare difficulty includes recognizing that planted ansatz.
- The exact G5 density is uniform over increasing interval-prime quadruples obeying
  a necessary prime-sum bound. It measures that declared prior, not every strategy
  a solver might use and not a complexity lower bound.
- The panel did not run LLL, optimized low-memory four-sum, specialized quadratic-
  form software, or the full 28-gap construction-aware scan; the last is intended
  to succeed after the insight.
- The family must not be emitted as hardened until the missing external attempts
  complete. It is parked for quota, not rejected on G, H, or V.
